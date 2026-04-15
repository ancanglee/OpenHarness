"""Tests for Bedrock Guardrails integration."""

from __future__ import annotations

import os
from unittest import mock

import pytest


class TestGuardrailConfig:
    """Test guardrail configuration in BedrockClient constructor."""

    def test_guardrail_from_constructor(self):
        """Guardrail ID/version from constructor args."""
        with mock.patch.dict(os.environ, {"AWS_REGION": "us-east-1"}):
            from openharness.api.bedrock_client import BedrockClient
            client = BedrockClient(
                region="us-east-1",
                guardrail_id="gr-test123",
                guardrail_version="1",
            )
            assert client._guardrail_id == "gr-test123"
            assert client._guardrail_version == "1"

    def test_guardrail_from_env(self):
        """Guardrail ID/version from environment variables."""
        with mock.patch.dict(os.environ, {
            "AWS_REGION": "us-east-1",
            "BEDROCK_GUARDRAIL_ID": "gr-env456",
            "BEDROCK_GUARDRAIL_VERSION": "2",
        }):
            from openharness.api.bedrock_client import BedrockClient
            client = BedrockClient(region="us-east-1")
            assert client._guardrail_id == "gr-env456"
            assert client._guardrail_version == "2"

    def test_constructor_overrides_env(self):
        """Constructor args take priority over env vars."""
        with mock.patch.dict(os.environ, {
            "AWS_REGION": "us-east-1",
            "BEDROCK_GUARDRAIL_ID": "gr-env",
            "BEDROCK_GUARDRAIL_VERSION": "1",
        }):
            from openharness.api.bedrock_client import BedrockClient
            client = BedrockClient(
                region="us-east-1",
                guardrail_id="gr-constructor",
                guardrail_version="3",
            )
            assert client._guardrail_id == "gr-constructor"
            assert client._guardrail_version == "3"

    def test_no_guardrail_configured(self):
        """No guardrail when neither constructor nor env is set."""
        with mock.patch.dict(os.environ, {"AWS_REGION": "us-east-1"}, clear=False):
            # Remove guardrail env vars if present
            env = {k: v for k, v in os.environ.items() if not k.startswith("BEDROCK_GUARDRAIL")}
            with mock.patch.dict(os.environ, env, clear=True):
                from openharness.api.bedrock_client import BedrockClient
                client = BedrockClient(region="us-east-1")
                assert client._guardrail_id is None

    def test_default_version_is_draft(self):
        """Default guardrail version is DRAFT when only ID is set."""
        with mock.patch.dict(os.environ, {
            "AWS_REGION": "us-east-1",
            "BEDROCK_GUARDRAIL_ID": "gr-test",
        }):
            # Remove VERSION if present
            os.environ.pop("BEDROCK_GUARDRAIL_VERSION", None)
            from openharness.api.bedrock_client import BedrockClient
            client = BedrockClient(region="us-east-1")
            assert client._guardrail_version == "DRAFT"


class TestGuardrailEnvForwarding:
    """Test guardrail env vars are forwarded to subagents."""

    def test_guardrail_id_in_teammate_vars(self):
        from openharness.swarm.spawn_utils import _TEAMMATE_ENV_VARS
        assert "BEDROCK_GUARDRAIL_ID" in _TEAMMATE_ENV_VARS

    def test_guardrail_version_in_teammate_vars(self):
        from openharness.swarm.spawn_utils import _TEAMMATE_ENV_VARS
        assert "BEDROCK_GUARDRAIL_VERSION" in _TEAMMATE_ENV_VARS
