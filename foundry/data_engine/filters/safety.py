# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Safety Filters — Toxicity detection and PII removal."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Common PII patterns
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),  # SSN
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD_REDACTED]"),
]

# Toxicity keyword blocklist (minimal — real system would use a classifier)
TOXIC_KEYWORDS = {
    "hack into", "steal password", "make a bomb", "synthesize drugs",
    "exploit vulnerability", "bypass security",
}


class SafetyFilter:
    """Filter and sanitize training samples for safety."""

    def __init__(
        self,
        remove_pii: bool = True,
        check_toxicity: bool = True,
        custom_blocklist: list[str] | None = None,
    ) -> None:
        self.remove_pii = remove_pii
        self.check_toxicity = check_toxicity
        self._blocklist = TOXIC_KEYWORDS.copy()
        if custom_blocklist:
            self._blocklist.update(custom_blocklist)

    def _redact_pii(self, text: str) -> str:
        for pattern, replacement in PII_PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text

    def _is_toxic(self, text: str) -> bool:
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self._blocklist)

    def filter(self, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter and sanitize samples."""
        passed = []
        for sample in samples:
            messages = sample.get("messages", [])
            full_text = " ".join(m.get("content", "") for m in messages)

            # Toxicity check
            if self.check_toxicity and self._is_toxic(full_text):
                logger.debug("Sample filtered for toxicity")
                continue

            # PII redaction
            if self.remove_pii:
                for msg in messages:
                    if "content" in msg:
                        msg["content"] = self._redact_pii(msg["content"])

            passed.append(sample)

        logger.info("Safety filter: %d/%d passed", len(passed), len(samples))
        return passed
