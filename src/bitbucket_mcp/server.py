"""Bitbucket MCP Server - FastMCP server for Bitbucket Cloud API."""

import time
from datetime import datetime, timezone
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


# Prometheus metrics endpoint
@mcp.custom_route("/metrics", methods=["GET"])
async def metrics_endpoint(_request: Request) -> PlainTextResponse:
    """Prometheus-compatible metrics endpoint."""
    uptime = time.time() - _server_start_time
    metrics = f"""# HELP bitbucket_mcp_up Whether the service is up (1 = up, 0 = down)
# TYPE bitbucket_mcp_up gauge
bitbucket_mcp_up 1

# HELP bitbucket_mcp_uptime_seconds Time since server started
# TYPE bitbucket_mcp_uptime_seconds counter
bitbucket_mcp_uptime_seconds {uptime:.2f}

# HELP bitbucket_mcp_info Service information
# TYPE bitbucket_mcp_info gauge
bitbucket_mcp_info{{service="bitbucket-mcp",version="0.3.0"}} 1
"""
    return PlainTextResponse(metrics, media_type="text/plain; version=0.0.4")


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


# =============================================================================
# Pipeline Tools
# =============================================================================


def _tail_log(log: str, tail: int) -> dict[str, Any]:
    """Split ``log`` once and return its last ``tail`` lines plus line counts.

    ``tail <= 0`` returns the whole log. Splitting a single time avoids re-scanning
    a potentially multi-MB log to compute totals and truncation separately.
    """
    lines = log.splitlines()
    total = len(lines)
    returned = lines if tail <= 0 or total <= tail else lines[-tail:]
    return {
        "total_lines": total,
        "returned_lines": len(returned),
        "truncated": tail > 0 and total > tail,
        "log": "\n".join(returned),
    }


def _summarize_pipeline(pipeline: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a single-call summary of a pipeline and its steps.

    Distinguishes three states — running / done-OK / failed — and surfaces the
    per-step breakdown, the currently running step, the remaining steps and the
    failing step's uuid, so no extra round-trip is needed to act on the result.
    """
    state = pipeline.get("state") or {}
    state_name = state.get("name")  # PENDING / IN_PROGRESS / COMPLETED
    result_name = (state.get("result") or {}).get("name")  # SUCCESSFUL / FAILED / STOPPED

    step_breakdown: list[dict[str, Any]] = []
    current_step: dict[str, Any] | None = None
    failed_step: dict[str, Any] | None = None
    remaining: list[str] = []

    total = len(steps)
    for idx, step in enumerate(steps):
        s_state = step.get("state") or {}
        s_state_name = s_state.get("name")
        s_result = (s_state.get("result") or {}).get("name")
        name = step.get("name") or "(unnamed)"
        uuid = step.get("uuid")
        step_breakdown.append(
            {"uuid": uuid, "name": name, "state": s_state_name, "result": s_result}
        )
        if s_state_name == "IN_PROGRESS":
            if current_step is None:
                current_step = {"uuid": uuid, "name": name, "position": f"{idx + 1}/{total}"}
        elif s_state_name != "COMPLETED":
            remaining.append(name)
        # A step can fail with several terminal results (FAILED, ERROR, EXPIRED);
        # surface the first non-successful one so its log can always be fetched.
        if s_result in ("FAILED", "ERROR", "EXPIRED") and failed_step is None:
            failed_step = {"uuid": uuid, "name": name}

    build_number = pipeline.get("build_number")

    if state_name == "COMPLETED":
        if result_name == "SUCCESSFUL":
            status = "success"
            summary = f"Pipeline #{build_number} SUCCESSFUL — all {total} step(s) passed."
        elif result_name == "FAILED":
            status = "failed"
            failed_name = failed_step["name"] if failed_step else "unknown"
            summary = f"Pipeline #{build_number} FAILED — step '{failed_name}' failed."
        elif result_name == "STOPPED":
            status = "stopped"
            summary = f"Pipeline #{build_number} was STOPPED."
        else:
            status = (result_name or "completed").lower()
            summary = f"Pipeline #{build_number} completed with result {result_name}."
    elif state_name in ("IN_PROGRESS", "BUILDING"):
        status = "running"
        if current_step:
            remaining_txt = ", ".join(remaining) if remaining else "none"
            summary = (
                f"Pipeline #{build_number} running — in step "
                f"'{current_step['name']}' ({current_step['position']}), remaining: {remaining_txt}."
            )
        else:
            summary = f"Pipeline #{build_number} running."
    elif state_name == "PENDING":
        status = "pending"
        summary = f"Pipeline #{build_number} is pending (not started yet)."
    else:
        status = (state_name or "unknown").lower()
        summary = f"Pipeline #{build_number} state: {state_name}."

    target = pipeline.get("target") or {}
    # Branch-triggered pipelines expose the branch as ``ref_name``; PR-triggered
    # ones (``pipeline_pullrequest_target``) expose the source branch as ``source``.
    ref_name = target.get("ref_name") or target.get("source")
    return {
        "pipeline_uuid": pipeline.get("uuid"),
        "build_number": build_number,
        "state": state_name,
        "result": result_name,
        "status": status,
        "summary": summary,
        "ref_name": ref_name,
        "target_type": target.get("type"),
        "commit": (target.get("commit") or {}).get("hash"),
        "steps": step_breakdown,
        "current_step": current_step,
        "remaining_steps": remaining,
        "failed_step": failed_step,
    }


async def _resolve_latest_pipeline(
    client: BitbucketClient,
    workspace: str,
    repo_slug: str,
    pr: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the newest pipeline for a PR: by source commit hash, fallback to branch.

    Returns ``(pipeline, resolved_by)`` where ``resolved_by`` is "commit", "branch"
    or ``None`` when no pipeline was found for either.
    """
    source = pr.get("source") or {}
    commit_hash = (source.get("commit") or {}).get("hash")
    branch_name = (source.get("branch") or {}).get("name")

    if commit_hash:
        res = await client.list_pipelines(
            workspace, repo_slug, query=f'target.commit.hash="{commit_hash}"'
        )
        values = res.get("values") or []
        if values:
            return values[0], "commit"

    if branch_name:
        res = await client.list_pipelines(
            workspace, repo_slug, query=f'target.ref_name="{branch_name}"'
        )
        values = res.get("values") or []
        if values:
            return values[0], "branch"

    return None, None


@mcp.tool(
    tags={"pipeline"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_pr_pipeline(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pr_id: Annotated[int, Field(ge=1, description="Pull request ID")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """Get the latest CI pipeline status for a pull request.

    Answers "how did the pipeline for this PR go?" in a single call: reports whether
    it is running (with the current step and what's left), succeeded, or failed (with
    the failing step and its uuid, so the log can be fetched). Resolves the pipeline
    by the PR's source commit hash, falling back to its source branch name.
    """
    client = get_client()
    ws = get_workspace(workspace)

    pr = await client.get_pull_request(ws, repo_slug, pr_id)
    source = pr.get("source") or {}
    source_branch = (source.get("branch") or {}).get("name")
    source_commit = (source.get("commit") or {}).get("hash")

    pipeline, resolved_by = await _resolve_latest_pipeline(client, ws, repo_slug, pr)
    if pipeline is None or not pipeline.get("uuid"):
        return {
            "pr_id": pr_id,
            "found": False,
            "summary": (
                f"No pipeline found for PR #{pr_id} "
                f"(source branch '{source_branch}', commit '{source_commit}')."
            ),
            "source_branch": source_branch,
            "source_commit": source_commit,
        }

    steps_res = await client.list_pipeline_steps(ws, repo_slug, pipeline["uuid"])
    steps = steps_res.get("values") or []
    summary = _summarize_pipeline(pipeline, steps)
    summary.update({"pr_id": pr_id, "found": True, "resolved_by": resolved_by})
    return summary


@mcp.tool(
    tags={"pipeline"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_pipeline_step_log(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pipeline_uuid: Annotated[str, Field(description="Pipeline UUID (e.g. '{abc-123}')")],
    step_uuid: Annotated[str, Field(description="Step UUID (e.g. '{def-456}')")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    tail: Annotated[
        int, Field(ge=0, description="Return only the last N lines (0 = whole log)")
    ] = 200,
) -> dict[str, Any]:
    """Get the log of a pipeline step, by default only the last ``tail`` lines.

    Logs can be several MB; the tail default keeps the output small while still
    capturing the error, which is usually at the end. Set ``tail=0`` for the full log.
    """
    client = get_client()
    ws = get_workspace(workspace)

    log = await client.get_pipeline_step_log(ws, repo_slug, pipeline_uuid, step_uuid)
    result = _tail_log(log, tail)
    result.update({"pipeline_uuid": pipeline_uuid, "step_uuid": step_uuid})
    return result


@mcp.tool(
    tags={"pipeline"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_list_pipelines(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
    branch: Annotated[str | None, Field(description="Filter by branch (target ref name)")] = None,
    page: Annotated[int, Field(ge=1, description="Page number")] = 1,
    pagelen: Annotated[int, Field(ge=1, le=100, description="Results per page")] = 25,
) -> dict[str, Any]:
    """List recent pipelines, newest first, optionally filtered by branch."""
    client = get_client()
    ws = get_workspace(workspace)
    query = f'target.ref_name="{branch}"' if branch else None
    return await client.list_pipelines(ws, repo_slug, query=query, page=page, pagelen=pagelen)


@mcp.tool(
    tags={"pipeline"},
    annotations={"readOnlyHint": True},
)
async def bitbucket_get_pipeline(
    repo_slug: Annotated[str, Field(description="Repository slug")],
    pipeline_uuid: Annotated[str, Field(description="Pipeline UUID (e.g. '{abc-123}')")],
    workspace: Annotated[str | None, Field(description="Workspace slug")] = None,
) -> dict[str, Any]:
    """Get a specific pipeline with its per-step breakdown and status summary."""
    client = get_client()
    ws = get_workspace(workspace)
    pipeline = await client.get_pipeline(ws, repo_slug, pipeline_uuid)
    steps_res = await client.list_pipeline_steps(ws, repo_slug, pipeline_uuid)
    steps = steps_res.get("values") or []
    return _summarize_pipeline(pipeline, steps)
