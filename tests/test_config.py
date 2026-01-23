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
            "BITBUCKET_EMAIL": "test@example.com",
            "BITBUCKET_API_TOKEN": "testtoken",
            "BITBUCKET_WORKSPACE": "testworkspace",
        }
        with patch.dict(os.environ, env, clear=False):
            config = BitbucketConfig.from_env()

        assert config.email == "test@example.com"
        assert config.api_token == "testtoken"
        assert config.workspace == "testworkspace"

    def test_from_env_legacy_variables(self) -> None:
        """Test backward compatibility with legacy environment variables."""
        env = {
            "BITBUCKET_USERNAME": "legacyuser",
            "BITBUCKET_APP_PASSWORD": "legacypassword",
        }
        with patch.dict(os.environ, env, clear=True):
            config = BitbucketConfig.from_env()

        assert config.email == "legacyuser"
        assert config.api_token == "legacypassword"

    def test_from_env_missing_email(self) -> None:
        """Test error when email is missing."""
        env = {"BITBUCKET_API_TOKEN": "testtoken"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="BITBUCKET_EMAIL"),
        ):
            BitbucketConfig.from_env()

    def test_from_env_missing_token(self) -> None:
        """Test error when token is missing."""
        env = {"BITBUCKET_EMAIL": "test@example.com"}
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="BITBUCKET_API_TOKEN"),
        ):
            BitbucketConfig.from_env()

    def test_auth_property(self) -> None:
        """Test the auth property returns correct tuple."""
        config = BitbucketConfig(email="test@example.com", api_token="token123")
        assert config.auth == ("test@example.com", "token123")

    def test_default_base_url(self) -> None:
        """Test default base URL is set correctly."""
        config = BitbucketConfig(email="test@example.com", api_token="token")
        assert config.base_url == "https://api.bitbucket.org/2.0"
