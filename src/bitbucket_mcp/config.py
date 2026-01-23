"""Configuration for Bitbucket MCP server."""

import os
from dataclasses import dataclass


@dataclass
class BitbucketConfig:
    """Configuration for Bitbucket API access."""

    email: str
    api_token: str
    workspace: str | None = None
    base_url: str = "https://api.bitbucket.org/2.0"

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
        )

    @property
    def auth(self) -> tuple[str, str]:
        """Return HTTP basic auth tuple (email, api_token)."""
        return (self.email, self.api_token)
