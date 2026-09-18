"""Configuration for Bitbucket MCP server."""

import os
from dataclasses import dataclass, field

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable, falling back to ``default`` when unset."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in TRUE_VALUES


def _parse_pipeline_allowlist(raw: str | None) -> frozenset[tuple[str, str]]:
    """Parse ``repo:pipeline`` entries into a set of (repo_slug, pipeline) pairs.

    A malformed entry raises instead of being skipped: silently dropping it would
    leave the operator believing a pipeline is allowed when it is not.
    """
    entries: set[tuple[str, str]] = set()
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        repo, sep, pipeline = item.partition(":")
        if not sep or not repo.strip() or not pipeline.strip():
            raise ValueError(
                f"Invalid BITBUCKET_PIPELINE_ALLOWLIST entry {item!r} - "
                "expected 'repo-slug:pipeline-name'"
            )
        entries.add((repo.strip(), pipeline.strip()))
    return frozenset(entries)


@dataclass
class BitbucketConfig:
    """Configuration for Bitbucket API access."""

    email: str
    api_token: str
    workspace: str | None = None
    base_url: str = "https://api.bitbucket.org/2.0"
    allow_pipeline_trigger: bool = False
    allow_pipeline_stop: bool = True
    pipeline_allowlist: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> "BitbucketConfig":
        """Create configuration from environment variables.

        Supports both new API token format and legacy app password format:
        - New: BITBUCKET_EMAIL + BITBUCKET_API_TOKEN
        - Legacy: BITBUCKET_USERNAME + BITBUCKET_APP_PASSWORD
        """
        # Try new format first, fall back to legacy
        email = os.environ.get("BITBUCKET_EMAIL") or os.environ.get("BITBUCKET_USERNAME")
        api_token = os.environ.get("BITBUCKET_API_TOKEN") or os.environ.get(
            "BITBUCKET_APP_PASSWORD"
        )

        if not email or not api_token:
            raise ValueError(
                "BITBUCKET_EMAIL and BITBUCKET_API_TOKEN environment variables are required. "
                "Legacy BITBUCKET_USERNAME/BITBUCKET_APP_PASSWORD also supported."
            )

        return cls(
            email=email,
            api_token=api_token,
            workspace=os.environ.get("BITBUCKET_WORKSPACE"),
            allow_pipeline_trigger=_env_bool("BITBUCKET_ALLOW_PIPELINE_TRIGGER", False),
            allow_pipeline_stop=_env_bool("BITBUCKET_ALLOW_PIPELINE_STOP", True),
            pipeline_allowlist=_parse_pipeline_allowlist(
                os.environ.get("BITBUCKET_PIPELINE_ALLOWLIST")
            ),
        )

    @property
    def auth(self) -> tuple[str, str]:
        """Return HTTP basic auth tuple (email, api_token)."""
        return (self.email, self.api_token)

    def is_pipeline_allowed(self, repo_slug: str, pipeline: str) -> bool:
        """Whether ``pipeline`` may be triggered for ``repo_slug``.

        Scoped per repository on purpose: one server instance serves every repo, so a
        bare pipeline name would let a ``deploy`` allowed for a staging repo also run
        the production ``deploy`` of another one.
        """
        return (repo_slug, pipeline) in self.pipeline_allowlist

    def allowed_pipelines_for(self, repo_slug: str) -> list[str]:
        """Pipelines allowed for ``repo_slug``, sorted - used in error messages."""
        return sorted(pipeline for repo, pipeline in self.pipeline_allowlist if repo == repo_slug)
