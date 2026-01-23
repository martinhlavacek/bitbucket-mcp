"""Entry point for running Bitbucket MCP server."""

from bitbucket_mcp.server import mcp


def main() -> None:
    """Run the Bitbucket MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
