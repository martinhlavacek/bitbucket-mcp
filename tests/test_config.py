"""Tests for Bitbucket configuration."""

import os
from unittest.mock import patch

import pytest

from bitbucket_mcp.config import BitbucketConfig


class TestBitbucketConfig:
    """Tests for BitbucketConfig."""

    def test_from_env_success(self) -> None:
        """Test creating config from environment variables."""
        env = {
            "BITBUCKET_USERNAME": "testuser",
            "BITBUCKET_APP_PASSWORD": "testpassword",
            "BITBUCKET_WORKSPACE": "testworkspace",
        }
        with patch.dict(os.environ, env, clear=False):
            config = BitbucketConfig.from_env()

        assert config.username == "testuser"
        assert config.app_password == "testpassword"
        assert config.workspace == "testworkspace"

    def test_from_env_missing_username(self) -> None:
        """Test error when username is missing."""
        env = {"BITBUCKET_APP_PASSWORD": "testpassword"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="BITBUCKET_USERNAME"),
        ):
            BitbucketConfig.from_env()

    def test_from_env_missing_password(self) -> None:
        """Test error when password is missing."""
        env = {"BITBUCKET_USERNAME": "testuser"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="BITBUCKET_APP_PASSWORD"),
        ):
            BitbucketConfig.from_env()

    def test_auth_property(self) -> None:
        """Test the auth property returns correct tuple."""
        config = BitbucketConfig(username="user", app_password="pass")
        assert config.auth == ("user", "pass")

    def test_default_base_url(self) -> None:
        """Test default base URL is set correctly."""
        config = BitbucketConfig(username="user", app_password="pass")
        assert config.base_url == "https://api.bitbucket.org/2.0"
