"""Tests for AWS credential forwarding in spawn_utils."""

from __future__ import annotations

import os
from unittest import mock

from openharness.swarm.spawn_utils import build_inherited_env_vars, _TEAMMATE_ENV_VARS


class TestAWSEnvVarsInTeammateList:
    """Verify AWS credential env vars are in the forwarding list."""

    def test_aws_access_key_id_in_list(self):
        assert "AWS_ACCESS_KEY_ID" in _TEAMMATE_ENV_VARS

    def test_aws_secret_access_key_in_list(self):
        assert "AWS_SECRET_ACCESS_KEY" in _TEAMMATE_ENV_VARS

    def test_aws_session_token_in_list(self):
        assert "AWS_SESSION_TOKEN" in _TEAMMATE_ENV_VARS

    def test_aws_region_in_list(self):
        assert "AWS_REGION" in _TEAMMATE_ENV_VARS

    def test_aws_default_region_in_list(self):
        assert "AWS_DEFAULT_REGION" in _TEAMMATE_ENV_VARS

    def test_aws_profile_in_list(self):
        assert "AWS_PROFILE" in _TEAMMATE_ENV_VARS


class TestBuildInheritedEnvVarsAWS:
    """Verify build_inherited_env_vars forwards AWS vars when set."""

    @mock.patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "AKIATEST", "AWS_REGION": "us-east-1"})
    def test_forwards_aws_credentials(self):
        env = build_inherited_env_vars()
        assert env["AWS_ACCESS_KEY_ID"] == "AKIATEST"
        assert env["AWS_REGION"] == "us-east-1"

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_no_aws_vars_when_unset(self):
        env = build_inherited_env_vars()
        assert "AWS_ACCESS_KEY_ID" not in env
        assert "AWS_REGION" not in env

    @mock.patch.dict(os.environ, {"AWS_PROFILE": "bedrock-dev", "AWS_DEFAULT_REGION": "eu-west-1"})
    def test_forwards_profile_and_default_region(self):
        env = build_inherited_env_vars()
        assert env["AWS_PROFILE"] == "bedrock-dev"
        assert env["AWS_DEFAULT_REGION"] == "eu-west-1"
