"""Configuration for Bitbucket MCP server."""

import os
from dataclasses import dataclass


@dataclass
class BitbucketConfig:
    """Configuration for Bitbucket API access."""

    username: str
    app_password: str
    workspace: str | None = None
    base_url: str = "https://api.bitbucket.org/2.0"

    @classmethod
    def from_env(cls) -> "BitbucketConfig":
        """Create configuration from environment variables."""
        username = os.environ.get("BITBUCKET_USERNAME")
        app_password = os.environ.get("BITBUCKET_APP_PASSWORD")

        if not username or not app_password:
            raise ValueError(
                "BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD environment variables are required"
            )

        return cls(
            username=username,
            app_password=app_password,
            workspace=os.environ.get("BITBUCKET_WORKSPACE"),
        )

    @property
    def auth(self) -> tuple[str, str]:
        """Return HTTP basic auth tuple."""
        return (self.username, self.app_password)
