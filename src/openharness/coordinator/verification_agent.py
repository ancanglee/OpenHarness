"""Verification subagent for validating other agents' work.

Implements Anthropic's verification subagent pattern:
- Black-box verification: doesn't need implementation context
- Clear success criteria
- Prevents "early victory" by requiring comprehensive checks
- Returns structured pass/fail with specific issues
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openharness.api.client import (
    ApiMessageRequest,
    ApiTextDeltaEvent,
    ApiMessageCompleteEvent,
    SupportsStreamingMessages,
)
from openharness.engine.messages import ConversationMessage

log = logging.getLogger(__name__)

VERIFICATION_SYSTEM_PROMPT = """You are a verification specialist. Your job is to verify whether work output meets the specified requirements.

CRITICAL RULES:
- You MUST check ALL criteria before marking as passed
- Do NOT mark as passed after checking only some criteria
- For each criterion, explicitly state whether it is met or not
- If ANY criterion is not met, the verification FAILS
- Be thorough and precise in your assessment

Respond with JSON only:
{
  "passed": true/false,
  "criteria_results": [
    {"criterion": "description", "met": true/false, "detail": "explanation"}
  ],
  "issues": ["list of specific issues found"],
  "summary": "brief overall assessment"
}"""


@dataclass
class VerificationResult:
    """Result of a verification check."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    criteria_results: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class VerificationAgent:
    """Dedicated agent for verifying other agents' work output.

    Operates as a black-box verifier: it receives the task description
    and output but NOT the implementation context, following Anthropic's
    recommendation that verification requires minimal context transfer.
    """

    def __init__(
        self,
        *,
        api_client: SupportsStreamingMessages,
        model: str,
        system_prompt: str | None = None,
    ) -> None:
        self._api_client = api_client
        self._model = model
        self._system_prompt = system_prompt or VERIFICATION_SYSTEM_PROMPT

    async def verify(
        self,
        task_description: str,
        output: str,
        criteria: list[str] | None = None,
    ) -> VerificationResult:
        """Verify whether output meets the task requirements.

        Args:
            task_description: What the task was supposed to accomplish.
            output: The actual output produced by the subagent.
            criteria: Optional explicit success criteria. If not provided,
                     the verifier infers criteria from the task description.
        """
        prompt_parts = [
            f"## Task Description\n{task_description}",
            f"## Output to Verify\n{output}",
        ]
        if criteria:
            criteria_text = "\n".join(f"- {c}" for c in criteria)
            prompt_parts.append(f"## Success Criteria\n{criteria_text}")
        else:
            prompt_parts.append(
                "## Success Criteria\nInfer appropriate criteria from the task description. "
                "Check completeness, correctness, and quality."
            )

        prompt_parts.append(
            "\nVerify the output against ALL criteria. "
            "You MUST check every criterion before deciding pass/fail."
        )

        request = ApiMessageRequest(
            model=self._model,
            messages=[ConversationMessage.from_user_text("\n\n".join(prompt_parts))],
            system_prompt=self._system_prompt,
            max_tokens=2048,
        )

        collected = ""
        try:
            async for event in self._api_client.stream_message(request):
                if isinstance(event, ApiTextDeltaEvent):
                    collected += event.text
                elif isinstance(event, ApiMessageCompleteEvent):
                    if event.message.text:
                        collected = event.message.text
        except Exception as exc:
            log.warning("Verification agent failed: %s", exc)
            return VerificationResult(
                passed=False,
                issues=[f"Verification agent error: {exc}"],
                summary="Verification could not be completed",
            )

        return self._parse_response(collected)

    def _parse_response(self, response: str) -> VerificationResult:
        """Parse the verification agent's JSON response."""
        try:
            text = response.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            # If we can't parse, treat as failed with the raw response
            return VerificationResult(
                passed=False,
                issues=["Could not parse verification response"],
                summary=response[:200],
            )

        return VerificationResult(
            passed=bool(data.get("passed", False)),
            issues=data.get("issues", []),
            criteria_results=data.get("criteria_results", []),
            summary=data.get("summary", ""),
        )
