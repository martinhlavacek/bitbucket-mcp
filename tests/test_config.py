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


class TestPipelineGuardrailConfig:
    """Tests for the pipeline write guardrail settings."""

    BASE_ENV = {
        "BITBUCKET_EMAIL": "test@example.com",
        "BITBUCKET_API_TOKEN": "testtoken",
    }

    def _config(self, **extra: str) -> BitbucketConfig:
        """Build a config from BASE_ENV plus ``extra``, isolated from the real environment."""
        with patch.dict(os.environ, {**self.BASE_ENV, **extra}, clear=True):
            return BitbucketConfig.from_env()

    def test_trigger_disabled_by_default(self) -> None:
        """Triggering is off unless explicitly enabled - the whole point of the opt-in."""
        assert self._config().allow_pipeline_trigger is False

    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
    def test_trigger_enabled_by_truthy_values(self, value: str) -> None:
        """Test the accepted spellings of an enabled flag."""
        assert self._config(BITBUCKET_ALLOW_PIPELINE_TRIGGER=value).allow_pipeline_trigger is True

    @pytest.mark.parametrize("value", ["false", "0", "no", ""])
    def test_trigger_stays_disabled_for_other_values(self, value: str) -> None:
        """Anything that is not a truthy spelling leaves the flag at its default."""
        assert self._config(BITBUCKET_ALLOW_PIPELINE_TRIGGER=value).allow_pipeline_trigger is False

    def test_stop_enabled_by_default(self) -> None:
        """Stopping a run is less consequential than starting one, so it defaults to on."""
        assert self._config().allow_pipeline_stop is True

    def test_stop_can_be_disabled(self) -> None:
        """Test the stop flag can be turned off independently of the trigger flag."""
        assert self._config(BITBUCKET_ALLOW_PIPELINE_STOP="false").allow_pipeline_stop is False

    def test_allowlist_empty_by_default(self) -> None:
        """An unset allowlist means no custom pipeline is allowed, not all of them."""
        assert self._config().pipeline_allowlist == frozenset()

    def test_allowlist_parses_scoped_entries_and_trims_whitespace(self) -> None:
        """Test parsing of a realistic multi-repo allowlist."""
        config = self._config(BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci, my-api:preview , web:ci")
        assert config.pipeline_allowlist == frozenset(
            {("my-api", "ci"), ("my-api", "preview"), ("web", "ci")}
        )

    @pytest.mark.parametrize("entry", ["my-api", ":ci", "my-api:", " : "])
    def test_allowlist_rejects_malformed_entry(self, entry: str) -> None:
        """A malformed entry raises: skipping it would look like the pipeline is allowed."""
        with pytest.raises(ValueError, match="BITBUCKET_PIPELINE_ALLOWLIST"):
            self._config(BITBUCKET_PIPELINE_ALLOWLIST=entry)

    def test_is_pipeline_allowed_is_scoped_per_repo(self) -> None:
        """'ci' allowed for my-api must not unlock 'ci' for another repository."""
        config = self._config(BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci")

        assert config.is_pipeline_allowed("my-api", "ci") is True
        assert config.is_pipeline_allowed("web", "ci") is False
        assert config.is_pipeline_allowed("my-api", "prod-deploy") is False

    def test_allowed_pipelines_for_lists_only_that_repo(self) -> None:
        """Test the helper that feeds the error message listing what is permitted."""
        config = self._config(BITBUCKET_PIPELINE_ALLOWLIST="my-api:preview,my-api:ci,web:ci")

        assert config.allowed_pipelines_for("my-api") == ["ci", "preview"]
        assert config.allowed_pipelines_for("web") == ["ci"]
        assert config.allowed_pipelines_for("unknown") == []
