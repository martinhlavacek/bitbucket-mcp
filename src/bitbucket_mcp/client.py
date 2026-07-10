"""Bitbucket API client."""

from typing import Any, cast

import httpx

from bitbucket_mcp.config import BitbucketConfig


class BitbucketClient:
    """HTTP client for Bitbucket Cloud API."""

    def __init__(self, config: BitbucketConfig) -> None:
        """Initialize the Bitbucket client."""
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                auth=self.config.auth,
                timeout=30.0,
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        """Make a GET request."""
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request."""
        client = await self._get_client()
        response = await client.post(path, json=json)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def put(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a PUT request."""
        client = await self._get_client()
        response = await client.put(path, json=json)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def delete(self, path: str) -> None:
        """Make a DELETE request."""
        client = await self._get_client()
        response = await client.delete(path)
        response.raise_for_status()

    # Repository methods

    async def get_repository(self, workspace: str, repo_slug: str) -> dict[str, Any]:
        """Get repository information."""
        return await self.get(f"/repositories/{workspace}/{repo_slug}")

    # Branch methods

    async def list_branches(
        self,
        workspace: str,
        repo_slug: str,
        page: int = 1,
        pagelen: int = 25,
    ) -> dict[str, Any]:
        """List repository branches."""
        return await self.get(
            f"/repositories/{workspace}/{repo_slug}/refs/branches",
            page=page,
            pagelen=pagelen,
        )

    # Pull Request methods

    async def list_pull_requests(
        self,
        workspace: str,
        repo_slug: str,
        state: str = "OPEN",
        page: int = 1,
        pagelen: int = 25,
    ) -> dict[str, Any]:
        """List pull requests."""
        return await self.get(
            f"/repositories/{workspace}/{repo_slug}/pullrequests",
            state=state,
            page=page,
            pagelen=pagelen,
        )

    async def get_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> dict[str, Any]:
        """Get a specific pull request."""
        return await self.get(f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}")

    async def create_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        title: str,
        source_branch: str,
        destination_branch: str,
        description: str | None = None,
        close_source_branch: bool = False,
        reviewers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new pull request."""
        data: dict[str, Any] = {
            "title": title,
            "source": {"branch": {"name": source_branch}},
            "destination": {"branch": {"name": destination_branch}},
            "close_source_branch": close_source_branch,
        }
        if description:
            data["description"] = description
        if reviewers:
            data["reviewers"] = [{"uuid": r} for r in reviewers]

        return await self.post(f"/repositories/{workspace}/{repo_slug}/pullrequests", json=data)

    async def merge_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
        message: str | None = None,
        close_source_branch: bool = True,
        merge_strategy: str = "merge_commit",
    ) -> dict[str, Any]:
        """Merge a pull request."""
        data: dict[str, Any] = {
            "close_source_branch": close_source_branch,
            "merge_strategy": merge_strategy,
        }
        if message:
            data["message"] = message

        return await self.post(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/merge",
            json=data,
        )

    async def approve_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> dict[str, Any]:
        """Approve a pull request."""
        return await self.post(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/approve"
        )

    async def unapprove_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> None:
        """Remove approval from a pull request."""
        await self.delete(f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/approve")

    async def decline_pull_request(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> dict[str, Any]:
        """Decline a pull request."""
        return await self.post(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/decline"
        )

    async def get_pull_request_diff(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> str:
        """Get the diff of a pull request."""
        client = await self._get_client()
        response = await client.get(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/diff",
            headers={"Accept": "text/plain"},
        )
        response.raise_for_status()
        return response.text

    async def add_pull_request_comment(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
        content: str,
        inline: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a pull request."""
        data: dict[str, Any] = {"content": {"raw": content}}
        if inline:
            data["inline"] = inline

        return await self.post(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/comments",
            json=data,
        )

    async def list_pull_request_comments(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
    ) -> dict[str, Any]:
        """List comments on a pull request."""
        return await self.get(
            f"/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/comments"
        )

    # Pipeline methods

    async def list_pipelines(
        self,
        workspace: str,
        repo_slug: str,
        query: str | None = None,
        sort: str = "-created_on",
        page: int = 1,
        pagelen: int = 25,
    ) -> dict[str, Any]:
        """List pipelines, newest first, optionally filtered by a Bitbucket query expression.

        The ``query`` is a Bitbucket query-language expression on the pipeline fields,
        e.g. ``target.commit.hash="abc123"`` or ``target.ref_name="my-branch"``.
        """
        params: dict[str, Any] = {"sort": sort, "page": page, "pagelen": pagelen}
        if query:
            params["q"] = query
        return await self.get(f"/repositories/{workspace}/{repo_slug}/pipelines/", **params)

    async def get_pipeline(
        self,
        workspace: str,
        repo_slug: str,
        pipeline_uuid: str,
    ) -> dict[str, Any]:
        """Get a specific pipeline by UUID."""
        return await self.get(f"/repositories/{workspace}/{repo_slug}/pipelines/{pipeline_uuid}")

    async def list_pipeline_steps(
        self,
        workspace: str,
        repo_slug: str,
        pipeline_uuid: str,
        pagelen: int = 100,
    ) -> dict[str, Any]:
        """List the steps of a pipeline.

        Uses the maximum page size (100) so the full step list is returned in one
        call; otherwise the default page size (~10) would truncate the steps and a
        failing step beyond the first page would be missed.
        """
        return await self.get(
            f"/repositories/{workspace}/{repo_slug}/pipelines/{pipeline_uuid}/steps/",
            pagelen=pagelen,
        )

    async def get_pipeline_step_log(
        self,
        workspace: str,
        repo_slug: str,
        pipeline_uuid: str,
        step_uuid: str,
    ) -> str:
        """Get the log output of a pipeline step as plain text.

        The Bitbucket log endpoint serves ``application/octet-stream`` and rejects a
        ``text/plain`` Accept header with 406, so we accept any content type here.
        """
        client = await self._get_client()
        response = await client.get(
            f"/repositories/{workspace}/{repo_slug}/pipelines/{pipeline_uuid}/steps/{step_uuid}/log",
            headers={"Accept": "*/*"},
        )
        response.raise_for_status()
        return response.text
