# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Verifiable Trajectory Pipeline — Real tool execution, not mock success.

This is the core differentiator: the Teacher generates tool calls,
the Sandbox EXECUTES them, real outputs feed back to the Teacher,
and the Teacher generates the next step based on actual execution state.

Failed trajectories where errors are handled gracefully are KEPT.
Trajectories where the Teacher hallucinates success despite failure are REJECTED.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from foundry.data_engine.constitution import Constitution
from foundry.data_engine.teachers.base import Message, Teacher
from foundry.sandbox.tool_executor import ToolExecutor, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryStep:
    """A single step in an agentic trajectory."""

    step_number: int
    thought: str = ""
    tool_call: dict[str, Any] | None = None
    tool_result: ToolResult | None = None
    assistant_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step": self.step_number,
            "thought": self.thought,
        }
        if self.tool_call:
            d["tool_call"] = self.tool_call
        if self.tool_result:
            d["tool_result"] = self.tool_result.to_dict()
        if self.assistant_response:
            d["response"] = self.assistant_response
        return d


@dataclass
class Trajectory:
    """A complete agentic trajectory with verified tool execution."""

    task_prompt: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_answer: str = ""
    verified: bool = False
    rejection_reason: str = ""
    critique: str = ""
    constitution_score: float = 0.0

    @property
    def success(self) -> bool:
        return self.verified and not self.rejection_reason

    @property
    def has_error_recovery(self) -> bool:
        """True if any tool call failed and the trajectory still completed."""
        has_failure = any(
            s.tool_result and not s.tool_result.success for s in self.steps
        )
        return has_failure and self.verified

    def to_chat_format(self) -> dict[str, Any]:
        """Convert to chat format for SFT training."""
        messages: list[dict[str, str]] = [
            {"role": "user", "content": self.task_prompt},
        ]

        # Build assistant response from trajectory steps
        response_parts = []
        for step in self.steps:
            if step.thought:
                response_parts.append(f"<thinking>{step.thought}</thinking>")
            if step.tool_call:
                tc = step.tool_call
                response_parts.append(
                    f'<tool_call>{{"name": "{tc["name"]}", "arguments": {tc.get("arguments", {})}}}</tool_call>'
                )
            if step.tool_result:
                response_parts.append(
                    f"<tool_result>{step.tool_result.to_feedback()}</tool_result>"
                )
            if step.assistant_response:
                response_parts.append(step.assistant_response)

        if self.final_answer:
            response_parts.append(self.final_answer)

        messages.append({
            "role": "assistant",
            "content": "\n\n".join(response_parts),
        })

        return {
            "messages": messages,
            "metadata": {
                "pipeline": "trajectory",
                "num_steps": len(self.steps),
                "verified": self.verified,
                "has_error_recovery": self.has_error_recovery,
                "constitution_score": self.constitution_score,
            },
        }


class TrajectoryPipeline:
    """Verifiable Trajectory synthesis pipeline.

    Flow:
    1. Teacher receives task prompt + available tool schemas
    2. Teacher generates a plan + first tool call
    3. Sandbox EXECUTES the tool call -> returns real stdout/stderr
    4. Real execution output fed back to Teacher
    5. Teacher generates next step based on actual execution state
    6. Loop until task complete or max steps reached
    7. Constitutional critique of the full trajectory
    8. Save verified trajectory as training data

    Rejection criteria:
    - Teacher hallucinates success when tool execution failed
    - Trajectory exceeds max steps without completion
    - Constitutional critique score below threshold
    """

    def __init__(
        self,
        teacher: Teacher,
        tool_executor: ToolExecutor,
        constitution: Constitution | None = None,
        max_steps: int = 10,
        min_constitution_score: float = 0.5,
    ) -> None:
        self.teacher = teacher
        self.tool_executor = tool_executor
        self.constitution = constitution
        self.max_steps = max_steps
        self.min_constitution_score = min_constitution_score

    async def generate_trajectory(self, task_prompt: str) -> Trajectory:
        """Generate a single verified trajectory."""
        trajectory = Trajectory(task_prompt=task_prompt)

        # Build initial messages with tool schemas
        tools = self.tool_executor.available_tools
        system_msg = (
            "You are an AI assistant with access to tools. "
            "Use tools to complete tasks step-by-step. "
            "After each tool result, decide whether to use another tool or provide a final answer. "
            "When done, respond with your final answer without any tool calls."
        )
        if self.constitution and self.constitution.system_prompt:
            system_msg = self.constitution.system_prompt

        conversation: list[Message] = [
            Message(role="system", content=system_msg),
            Message(role="user", content=task_prompt),
        ]

        for step_num in range(1, self.max_steps + 1):
            # Get teacher's next action
            response = await self.teacher.generate(
                conversation, tools=tools, temperature=0.5
            )

            step = TrajectoryStep(step_number=step_num)

            if response.has_tool_calls:
                # Teacher wants to use a tool
                tc = response.tool_calls[0]  # Process one tool call at a time
                step.thought = response.content
                step.tool_call = {
                    "name": tc["name"],
                    "arguments": tc.get("arguments", {}),
                }

                # EXECUTE the tool call in the sandbox
                tool_result = await self.tool_executor.execute(
                    tc["name"], tc.get("arguments", {})
                )
                step.tool_result = tool_result

                # Feed real result back to teacher
                conversation.append(Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                ))
                conversation.append(Message(
                    role="tool",
                    content=tool_result.to_feedback(),
                    tool_call_id=tc.get("id", f"call_{step_num}"),
                    name=tc["name"],
                ))

            else:
                # Teacher is done — this is the final answer
                step.assistant_response = response.content
                trajectory.final_answer = response.content
                trajectory.steps.append(step)
                break

            trajectory.steps.append(step)
        else:
            # Max steps exceeded
            trajectory.rejection_reason = f"Exceeded max steps ({self.max_steps})"

        # Verification: check for hallucinated success
        if not trajectory.rejection_reason:
            hallucination = self._check_hallucination(trajectory)
            if hallucination:
                trajectory.rejection_reason = hallucination

        # Constitutional critique
        if self.constitution and not trajectory.rejection_reason:
            score, critique = await self._constitutional_critique(trajectory)
            trajectory.constitution_score = score
            trajectory.critique = critique
            if score < self.min_constitution_score:
                trajectory.rejection_reason = (
                    f"Constitution score {score:.2f} below threshold {self.min_constitution_score}"
                )

        trajectory.verified = not trajectory.rejection_reason
        return trajectory

    def _check_hallucination(self, trajectory: Trajectory) -> str:
        """Check if the teacher hallucinated success despite tool failures.

        Returns rejection reason if hallucination detected, empty string otherwise.
        """
        for step in trajectory.steps:
            if step.tool_result and not step.tool_result.success:
                # Check if the next step or final answer claims success
                # without acknowledging the error
                idx = trajectory.steps.index(step)
                if idx + 1 < len(trajectory.steps):
                    next_step = trajectory.steps[idx + 1]
                    text = (next_step.thought + " " + next_step.assistant_response).lower()
                    # If error is not acknowledged in subsequent response
                    error_keywords = ["error", "fail", "issue", "problem", "retry", "alternative"]
                    if not any(kw in text for kw in error_keywords):
                        return (
                            f"Step {step.step_number}: Tool '{step.tool_call['name']}' failed "
                            f"but subsequent step does not acknowledge the error"
                        )

                # Check final answer
                if trajectory.final_answer:
                    final_lower = trajectory.final_answer.lower()
                    success_claims = ["successfully", "completed", "done", "finished"]
                    error_acks = ["error", "fail", "couldn't", "unable", "issue"]
                    if any(s in final_lower for s in success_claims) and not any(
                        e in final_lower for e in error_acks
                    ):
                        return (
                            f"Final answer claims success but step {step.step_number} "
                            f"tool '{step.tool_call['name']}' failed"
                        )
        return ""

    async def _constitutional_critique(
        self, trajectory: Trajectory,
    ) -> tuple[float, str]:
        """Run constitutional critique on the full trajectory."""
        assert self.constitution is not None

        # Format trajectory for critique
        traj_text = f"Task: {trajectory.task_prompt}\n\n"
        for step in trajectory.steps:
            traj_text += f"Step {step.step_number}:\n"
            if step.thought:
                traj_text += f"  Thought: {step.thought}\n"
            if step.tool_call:
                traj_text += f"  Tool: {step.tool_call['name']}({step.tool_call.get('arguments', {})})\n"
            if step.tool_result:
                traj_text += f"  Result: {step.tool_result.to_feedback()}\n"
            if step.assistant_response:
                traj_text += f"  Response: {step.assistant_response}\n"
            traj_text += "\n"
        if trajectory.final_answer:
            traj_text += f"Final Answer: {trajectory.final_answer}\n"

        # Critique against each principle and average scores
        scores = []
        critiques = []
        for principle in self.constitution.weighted_principles():
            critique_prompt = (
                f'Rate this trajectory against the principle "{principle.description}" '
                f"on a scale of 0.0 to 1.0. Respond with ONLY a number first, "
                f"then a brief justification.\n\n{traj_text}"
            )
            response = await self.teacher.generate(
                [Message(role="user", content=critique_prompt)],
                temperature=0.1,
                max_tokens=256,
            )

            # Parse score
            try:
                score_text = response.content.strip().split()[0]
                score = float(score_text)
                score = max(0.0, min(1.0, score))
            except (ValueError, IndexError):
                score = 0.5

            scores.append(score * principle.weight)
            critiques.append(f"{principle.name}: {score:.2f} — {response.content[:200]}")

        total_weight = sum(p.weight for p in self.constitution.weighted_principles())
        avg_score = sum(scores) / total_weight if total_weight > 0 else 0.0

        return avg_score, "\n".join(critiques)

    async def process_batch(
        self, task_prompts: list[str], on_progress: Any = None,
    ) -> list[Trajectory]:
        """Generate verified trajectories for a batch of task prompts."""
        results = []
        accepted = 0
        rejected = 0

        for i, prompt in enumerate(task_prompts):
            try:
                traj = await self.generate_trajectory(prompt)
                if traj.success or traj.has_error_recovery:
                    results.append(traj)
                    accepted += 1
                else:
                    rejected += 1
                    logger.info(
                        "Trajectory %d rejected: %s", i, traj.rejection_reason
                    )
                if on_progress:
                    await on_progress(i + 1, len(task_prompts), accepted, rejected)
            except Exception as e:
                logger.error("Failed trajectory %d: %s", i, e)
                rejected += 1

        logger.info(
            "Trajectory batch complete: %d accepted, %d rejected",
            accepted, rejected,
        )
        return results
