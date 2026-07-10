"""Tests for Bitbucket API client."""

import pytest
import respx
from httpx import Response

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig


@pytest.fixture
def config() -> BitbucketConfig:
    """Create test configuration."""
    return BitbucketConfig(
        email="test@example.com",
        api_token="testtoken",
        workspace="testworkspace",
    )


@pytest.fixture
def client(config: BitbucketConfig) -> BitbucketClient:
    """Create test client."""
    return BitbucketClient(config)


class TestBitbucketClient:
    """Tests for BitbucketClient."""

    @respx.mock
    async def test_get_repository(self, client: BitbucketClient) -> None:
        """Test getting repository information."""
        mock_response = {
            "slug": "test-repo",
            "name": "Test Repo",
            "full_name": "testworkspace/test-repo",
        }
        respx.get("https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo").mock(
            return_value=Response(200, json=mock_response)
        )

        result = await client.get_repository("testworkspace", "test-repo")

        assert result["slug"] == "test-repo"
        assert result["name"] == "Test Repo"

    @respx.mock
    async def test_list_branches(self, client: BitbucketClient) -> None:
        """Test listing branches."""
        mock_response = {
            "values": [
                {"name": "main"},
                {"name": "develop"},
            ],
            "page": 1,
            "size": 2,
        }
        respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/refs/branches"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.list_branches("testworkspace", "test-repo")

        assert len(result["values"]) == 2
        assert result["values"][0]["name"] == "main"

    @respx.mock
    async def test_list_pull_requests(self, client: BitbucketClient) -> None:
        """Test listing pull requests."""
        mock_response = {
            "values": [
                {"id": 1, "title": "Test PR", "state": "OPEN"},
            ],
            "page": 1,
            "size": 1,
        }
        respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.list_pull_requests("testworkspace", "test-repo")

        assert len(result["values"]) == 1
        assert result["values"][0]["id"] == 1

    @respx.mock
    async def test_get_pull_request(self, client: BitbucketClient) -> None:
        """Test getting a specific pull request."""
        mock_response = {
            "id": 1,
            "title": "Test PR",
            "state": "OPEN",
            "description": "Test description",
        }
        respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests/1"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.get_pull_request("testworkspace", "test-repo", 1)

        assert result["id"] == 1
        assert result["title"] == "Test PR"

    @respx.mock
    async def test_create_pull_request(self, client: BitbucketClient) -> None:
        """Test creating a pull request."""
        mock_response = {
            "id": 2,
            "title": "New PR",
            "state": "OPEN",
        }
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests"
        ).mock(return_value=Response(201, json=mock_response))

        result = await client.create_pull_request(
            "testworkspace",
            "test-repo",
            title="New PR",
            source_branch="feature",
            destination_branch="main",
        )

        assert result["id"] == 2
        assert result["title"] == "New PR"

    @respx.mock
    async def test_merge_pull_request(self, client: BitbucketClient) -> None:
        """Test merging a pull request."""
        mock_response = {
            "id": 1,
            "state": "MERGED",
        }
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests/1/merge"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.merge_pull_request("testworkspace", "test-repo", 1)

        assert result["state"] == "MERGED"

    @respx.mock
    async def test_approve_pull_request(self, client: BitbucketClient) -> None:
        """Test approving a pull request."""
        mock_response = {"approved": True}
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests/1/approve"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.approve_pull_request("testworkspace", "test-repo", 1)

        assert result["approved"] is True

    @respx.mock
    async def test_get_pull_request_diff(self, client: BitbucketClient) -> None:
        """Test getting pull request diff."""
        mock_diff = "diff --git a/file.txt b/file.txt\n+new line"
        respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests/1/diff"
        ).mock(return_value=Response(200, text=mock_diff))

        result = await client.get_pull_request_diff("testworkspace", "test-repo", 1)

        assert "+new line" in result

    @respx.mock
    async def test_add_pull_request_comment(self, client: BitbucketClient) -> None:
        """Test adding a comment to a pull request."""
        mock_response = {
            "id": 1,
            "content": {"raw": "Test comment"},
        }
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pullrequests/1/comments"
        ).mock(return_value=Response(201, json=mock_response))

        result = await client.add_pull_request_comment(
            "testworkspace", "test-repo", 1, "Test comment"
        )

        assert result["content"]["raw"] == "Test comment"

    @respx.mock
    async def test_list_pipelines(self, client: BitbucketClient) -> None:
        """Test listing pipelines with a query filter."""
        mock_response = {
            "values": [
                {"uuid": "{p1}", "build_number": 42, "state": {"name": "COMPLETED"}},
            ],
            "page": 1,
            "size": 1,
        }
        route = respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pipelines/"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.list_pipelines(
            "testworkspace", "test-repo", query='target.ref_name="main"'
        )

        assert result["values"][0]["build_number"] == 42
        request = route.calls.last.request
        assert request.url.params["q"] == 'target.ref_name="main"'
        assert request.url.params["sort"] == "-created_on"

    @respx.mock
    async def test_get_pipeline(self, client: BitbucketClient) -> None:
        """Test getting a specific pipeline by UUID."""
        mock_response = {"uuid": "{p1}", "build_number": 7, "state": {"name": "COMPLETED"}}
        respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pipelines/%7Bp1%7D"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.get_pipeline("testworkspace", "test-repo", "{p1}")

        assert result["build_number"] == 7

    @respx.mock
    async def test_list_pipeline_steps(self, client: BitbucketClient) -> None:
        """Test listing pipeline steps."""
        mock_response = {
            "values": [
                {"uuid": "{s1}", "name": "build", "state": {"name": "COMPLETED"}},
                {"uuid": "{s2}", "name": "test", "state": {"name": "COMPLETED"}},
            ],
            "size": 2,
        }
        route = respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pipelines/%7Bp1%7D/steps/"
        ).mock(return_value=Response(200, json=mock_response))

        result = await client.list_pipeline_steps("testworkspace", "test-repo", "{p1}")

        assert len(result["values"]) == 2
        assert result["values"][1]["name"] == "test"
        # Max page size so steps are not truncated to the first page (~10).
        assert route.calls.last.request.url.params["pagelen"] == "100"

    @respx.mock
    async def test_get_pipeline_step_log(self, client: BitbucketClient) -> None:
        """Test getting a pipeline step log as plain text."""
        mock_log = "Running tests...\nFAILED test_foo\nexit code 1"
        route = respx.get(
            "https://api.bitbucket.org/2.0/repositories/testworkspace/test-repo/pipelines/%7Bp1%7D/steps/%7Bs2%7D/log"
        ).mock(return_value=Response(200, text=mock_log))

        result = await client.get_pipeline_step_log("testworkspace", "test-repo", "{p1}", "{s2}")

        assert "FAILED test_foo" in result
        # The log endpoint rejects an ``Accept: text/plain`` header with 406.
        assert route.calls.last.request.headers["accept"] == "*/*"
