#!/usr/bin/env python3
"""
Generate sample training data without requiring API keys.
Uses the local teacher model for self-contained data synthesis.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from foundry.data_engine.constitution import Constitution
from foundry.data_engine.pipelines.sl_cai import SLCAIPipeline
from foundry.data_engine.pipelines.rl_cai import RLCAIPipeline
from foundry.data_engine.teachers.local_teacher import LocalTeacher


SAMPLE_PROMPTS = [
    "Explain the concept of recursion in programming.",
    "Write a Python function to check if a string is a palindrome.",
    "Describe how a hash table works.",
    "What is the difference between a process and a thread?",
    "Explain Big O notation and why it matters.",
    "How does garbage collection work in Python?",
    "What are the SOLID principles in software design?",
    "Explain REST API design principles.",
    "What is the difference between SQL and NoSQL databases?",
    "How does HTTPS encryption work?",
]


async def generate_sl_cai_samples():
    """Generate SL-CAI samples using a local teacher model."""
    print("Loading local teacher model...")
    # Use a small model for testing
    teacher = LocalTeacher(model_name="unsloth/Qwen2.5-0.5B-Instruct")
    
    # Load the coding constitution
    constitution = Constitution.from_yaml(Path("constitutions/coding.yaml"))
    
    print(f"Running SL-CAI pipeline with {len(SAMPLE_PROMPTS)} prompts...")
    pipeline = SLCAIPipeline(teacher, constitution, max_revisions=2)
    
    results = await pipeline.process_batch(SAMPLE_PROMPTS[:5])
    
    # Save results
    output_dir = Path("datasets/generated")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "sample_sl_cai.jsonl"
    with open(output_file, "w") as f:
        for sample in results:
            import json
            f.write(json.dumps(sample.to_chat_format(), ensure_ascii=False) + "\n")
    
    print(f"Saved {len(results)} samples to {output_file}")
    return results


async def generate_rl_cai_pairs():
    """Generate RL-CAI preference pairs."""
    print("Loading local teacher model...")
    teacher = LocalTeacher(model_name="unsloth/Qwen2.5-0.5B-Instruct")
    
    constitution = Constitution.from_yaml(Path("constitutions/general.yaml"))
    
    print(f"Running RL-CAI pipeline with {len(SAMPLE_PROMPTS)} prompts...")
    pipeline = RLCAIPipeline(teacher, constitution)
    
    results = await pipeline.process_batch(SAMPLE_PROMPTS[:5])
    
    output_dir = Path("datasets/generated")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "sample_rl_cai.jsonl"
    with open(output_file, "w") as f:
        for pair in results:
            import json
            f.write(json.dumps(pair.to_dpo_format(), ensure_ascii=False) + "\n")
    
    print(f"Saved {len(results)} preference pairs to {output_file}")
    return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample training data")
    parser.add_argument(
        "pipeline",
        choices=["sl_cai", "rl_cai", "all"],
        default="all",
        nargs="?",
        help="Which pipeline to run"
    )
    
    args = parser.parse_args()
    
    if args.pipeline in ("sl_cai", "all"):
        print("=" * 50)
        print("Generating SL-CAI samples...")
        print("=" * 50)
        try:
            asyncio.run(generate_sl_cai_samples())
        except Exception as e:
            print(f"SL-CAI generation failed: {e}")
            print("Note: This requires the model to be downloaded. First run may take time.")
    
    if args.pipeline in ("rl_cai", "all"):
        print("=" * 50)
        print("Generating RL-CAI pairs...")
        print("=" * 50)
        try:
            asyncio.run(generate_rl_cai_pairs())
        except Exception as e:
            print(f"RL-CAI generation failed: {e}")
            print("Note: This requires the model to be downloaded. First run may take time.")


if __name__ == "__main__":
    main()
