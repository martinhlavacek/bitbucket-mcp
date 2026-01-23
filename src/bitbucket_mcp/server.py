"""Bitbucket MCP Server - FastMCP server for Bitbucket Cloud API."""

import time
from datetime import datetime
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig

# Track server start time for health checks
_server_start_time = time.time()

# Initialize FastMCP server
mcp = FastMCP(
    name="Bitbucket MCP",
    instructions="""Bitbucket MCP server provides tools for interacting with Bitbucket Cloud API.

Available operations:
- Pull Requests: create, list, get, merge, approve, decline, comment
- Branches: list repository branches
- Repositories: get repository information
- Diffs: view pull request changes

Required environment variables:
- BITBUCKET_EMAIL: Your Bitbucket email
- BITBUCKET_API_TOKEN: Bitbucket API Token with repository and PR permissions
- BITBUCKET_WORKSPACE: (optional) Default workspace
""",
)


# Health check endpoint for Docker/monitoring
@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(_request: Request) -> JSONResponse:
    """HTTP health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "bitbucket-mcp",
            "uptime_seconds": time.time() - _server_start_time,
            "timestamp": datetime.now().isoformat(),
        }
    )


# Global client instance
_client: BitbucketClient | None = None


def get_client() -> BitbucketClient:
    """Get or create the Bitbucket client."""
    global _client
    if _client is None:
        config = BitbucketConfig.from_env()
        _client = BitbucketClient(config)
    return _client


def get_workspace(workspace: str | None) -> str:
    """Get workspace from parameter or environment."""
    if workspace:
        return workspace
    config = BitbucketConfig.from_env()
    if config.workspace:
        return config.workspace
    raise ToolError("workspace is required - provide it as parameter or set BITBUCKET_WORKSPACE")


# =============================================================================
# Repository Tools
# =============================================================================


@mcp.tool(
    tags={"repository"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_repo(
    repo_slug: Annotated[str, Field(description="Repository slug (e.g., 'my-repo')")],
    workspace: Annotated[
        str | None, Field(description="Workspace slug. Uses BITBUCKET_WORKSPACE if not provided")
    ] = None,
) -> dict[str, Any]:
    """Get repository information including name, description, and settings."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.get_repository(ws, repo_slug)


# =============================================================================
# Branch Tools
# =============================================================================


@mcp.tool(
    tags={"branch"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_list_branches(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    page: Annotated[int, Field(ge=1, description="Page number")] = 1,
    pagelen: Annotated[int, Field(ge=1, le=100, description="Results per page")] = 25,
) -> dict[str, Any]:
    """List branches in a repository with pagination support."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.list_branches(ws, repo_slug, page=page, pagelen=pagelen)


# =============================================================================
# Pull Request Tools
# =============================================================================


@mcp.tool(
    tags={"pull-request"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_list_prs(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    state: Annotated[
        str, Field(description="PR state: OPEN, MERGED, DECLINED, or SUPERSEDED")
    ] = "OPEN",
    page: Annotated[int, Field(ge=1, description="Page number")] = 1,
    pagelen: Annotated[int, Field(ge=1, le=50, description="Results per page")] = 25,
) -> dict[str, Any]:
    """List pull requests in a repository filtered by state."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.list_pull_requests(ws, repo_slug, state=state, page=page, pagelen=pagelen)


@mcp.tool(
    tags={"pull-request"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """Get detailed information about a specific pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.get_pull_request(ws, repo_slug, pr_id)


@mcp.tool(
    tags={"pull-request"},
    annotations={"destructiveHint": False},
)
async def bitbucket_create_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    title: Annotated[str, Field(description="Pull request title")],
    source_branch: Annotated[str, Field(description="Source branch name")],
    destination_branch: Annotated[str, Field(description="Destination branch name")] = "main",
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    description: Annotated[str | None, Field(description="Pull request description")] = None,
    close_source_branch: Annotated[
        bool, Field(description="Close source branch after merge")
    ] = False,
    reviewers: Annotated[list[str] | None, Field(description="List of reviewer UUIDs")] = None,
) -> dict[str, Any]:
    """Create a new pull request in the repository."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.create_pull_request(
        ws,
        repo_slug,
        title=title,
        source_branch=source_branch,
        destination_branch=destination_branch,
        description=description,
        close_source_branch=close_source_branch,
        reviewers=reviewers,
    )


@mcp.tool(
    tags={"pull-request"},
    annotations={"destructiveHint": True},
)
async def bitbucket_merge_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    message: Annotated[str | None, Field(description="Merge commit message")] = None,
    close_source_branch: Annotated[
        bool, Field(description="Close source branch after merge")
    ] = True,
    merge_strategy: Annotated[
        str, Field(description="Merge strategy: merge_commit, squash, or fast_forward")
    ] = "merge_commit",
) -> dict[str, Any]:
    """Merge an approved pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.merge_pull_request(
        ws,
        repo_slug,
        pr_id,
        message=message,
        close_source_branch=close_source_branch,
        merge_strategy=merge_strategy,
    )


@mcp.tool(
    tags={"pull-request"},
)
async def bitbucket_approve_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """Approve a pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.approve_pull_request(ws, repo_slug, pr_id)


@mcp.tool(
    tags={"pull-request"},
)
async def bitbucket_unapprove_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, str]:
    """Remove approval from a pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    await client.unapprove_pull_request(ws, repo_slug, pr_id)
    return {"status": "unapproved", "pr_id": str(pr_id)}


@mcp.tool(
    tags={"pull-request"},
    annotations={"destructiveHint": True},
)
async def bitbucket_decline_pr(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """Decline a pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.decline_pull_request(ws, repo_slug, pr_id)


# =============================================================================
# Diff & Comment Tools
# =============================================================================


@mcp.tool(
    tags={"pull-request", "diff"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_diff(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> str:
    """Get the diff of a pull request showing all file changes."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.get_pull_request_diff(ws, repo_slug, pr_id)


@mcp.tool(
    tags={"pull-request", "comment"},
)
async def bitbucket_add_comment(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    content: Annotated[str, Field(description="Comment content (Markdown supported)")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    file_path: Annotated[str | None, Field(description="File path for inline comment")] = None,
    line: Annotated[int | None, Field(ge=1, description="Line number for inline comment")] = None,
) -> dict[str, Any]:
    """Add a comment to a pull request. Can be general or inline on a specific line."""
    client = get_client()
    ws = get_workspace(workspace)

    inline = None
    if file_path and line:
        inline = {"path": file_path, "to": line}

    return await client.add_pull_request_comment(ws, repo_slug, pr_id, content, inline=inline)


@mcp.tool(
    tags={"pull-request", "comment"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_list_comments(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """List all comments on a pull request."""
    client = get_client()
    ws = get_workspace(workspace)
    return await client.list_pull_request_comments(ws, repo_slug, pr_id)
