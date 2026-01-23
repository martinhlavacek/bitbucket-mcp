"""Entry point for running Bitbucket MCP server."""

import argparse

from bitbucket_mcp.server import mcp


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bitbucket MCP Server - MCP server for Bitbucket Cloud API"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the Bitbucket MCP server."""
    args = parse_args()

    if args.transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,  # No session management needed for Bitbucket API
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
