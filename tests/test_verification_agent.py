"""Tests for the verification agent."""

from __future__ import annotations

import pytest

from openharness.coordinator.verification_agent import VerificationAgent, VerificationResult


class TestVerificationResultParsing:
    """Test the JSON parsing logic of VerificationAgent."""

    def _make_verifier(self):
        return VerificationAgent(api_client=None, model="test")  # type: ignore[arg-type]

    def test_valid_pass(self):
        verifier = self._make_verifier()
        response = '{"passed": true, "issues": [], "summary": "All good"}'
        result = verifier._parse_response(response)
        assert result.passed is True
        assert result.issues == []
        assert result.summary == "All good"

    def test_valid_fail(self):
        verifier = self._make_verifier()
        response = '{"passed": false, "issues": ["missing error handling"], "summary": "Needs work"}'
        result = verifier._parse_response(response)
        assert result.passed is False
        assert "missing error handling" in result.issues

    def test_with_criteria_results(self):
        verifier = self._make_verifier()
        response = '''{
            "passed": true,
            "criteria_results": [
                {"criterion": "completeness", "met": true, "detail": "all done"}
            ],
            "issues": [],
            "summary": "OK"
        }'''
        result = verifier._parse_response(response)
        assert result.passed is True
        assert len(result.criteria_results) == 1

    def test_json_in_code_block(self):
        verifier = self._make_verifier()
        response = '```json\n{"passed": false, "issues": ["bug"], "summary": "fail"}\n```'
        result = verifier._parse_response(response)
        assert result.passed is False
        assert "bug" in result.issues

    def test_invalid_json_returns_failed(self):
        verifier = self._make_verifier()
        result = verifier._parse_response("this is not json at all")
        assert result.passed is False
        assert "Could not parse" in result.issues[0]

    def test_empty_response(self):
        verifier = self._make_verifier()
        result = verifier._parse_response("")
        assert result.passed is False
