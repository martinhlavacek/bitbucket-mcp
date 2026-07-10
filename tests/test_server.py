"""Tests for pipeline helpers in the MCP server."""

import pytest
import respx
from httpx import Request, Response

from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig
from bitbucket_mcp.server import (
    _resolve_latest_pipeline,
    _summarize_pipeline,
    _tail_lines,
)


def _step(name: str, state: str, result: str | None = None) -> dict:
    """Build a pipeline step dict."""
    step_state: dict = {"name": state}
    if result is not None:
        step_state["result"] = {"name": result}
    return {"uuid": f"{{{name}}}", "name": name, "state": step_state}


def _pipeline(state: str, result: str | None = None, build_number: int = 1) -> dict:
    """Build a pipeline dict."""
    pl_state: dict = {"name": state}
    if result is not None:
        pl_state["result"] = {"name": result}
    return {
        "uuid": "{pipe-1}",
        "build_number": build_number,
        "state": pl_state,
        "target": {"ref_name": "feature", "commit": {"hash": "abc123"}},
    }


@pytest.fixture
def config() -> BitbucketConfig:
    return BitbucketConfig(email="test@example.com", api_token="tok", workspace="ws")


@pytest.fixture
def client(config: BitbucketConfig) -> BitbucketClient:
    return BitbucketClient(config)


class TestSummarizePipeline:
    """Tests for the three-state pipeline summary."""

    def test_successful(self) -> None:
        pipeline = _pipeline("COMPLETED", "SUCCESSFUL", build_number=10)
        steps = [
            _step("build", "COMPLETED", "SUCCESSFUL"),
            _step("test", "COMPLETED", "SUCCESSFUL"),
        ]

        summary = _summarize_pipeline(pipeline, steps)

        assert summary["status"] == "success"
        assert summary["failed_step"] is None
        assert summary["remaining_steps"] == []
        assert "SUCCESSFUL" in summary["summary"]
        assert len(summary["steps"]) == 2

    def test_failed_surfaces_failing_step(self) -> None:
        pipeline = _pipeline("COMPLETED", "FAILED", build_number=11)
        steps = [
            _step("build", "COMPLETED", "SUCCESSFUL"),
            _step("test", "COMPLETED", "FAILED"),
            _step("deploy", "PENDING"),
        ]

        summary = _summarize_pipeline(pipeline, steps)

        assert summary["status"] == "failed"
        assert summary["failed_step"] == {"uuid": "{test}", "name": "test"}
        assert "test" in summary["summary"]

    def test_pr_triggered_ref_name_falls_back_to_source(self) -> None:
        pipeline = {
            "uuid": "{pipe-2}",
            "build_number": 15,
            "state": {"name": "COMPLETED", "result": {"name": "SUCCESSFUL"}},
            "target": {
                "type": "pipeline_pullrequest_target",
                "source": "feat/POCAIMO-6-changelog",
                "destination": "develop",
                "commit": {"hash": "f7c700bc"},
            },
        }

        summary = _summarize_pipeline(pipeline, [_step("build", "COMPLETED", "SUCCESSFUL")])

        assert summary["ref_name"] == "feat/POCAIMO-6-changelog"
        assert summary["target_type"] == "pipeline_pullrequest_target"

    def test_in_progress_reports_current_and_remaining(self) -> None:
        pipeline = _pipeline("IN_PROGRESS", build_number=12)
        steps = [
            _step("build", "COMPLETED", "SUCCESSFUL"),
            _step("test", "IN_PROGRESS"),
            _step("deploy", "PENDING"),
            _step("notify", "PENDING"),
        ]

        summary = _summarize_pipeline(pipeline, steps)

        assert summary["status"] == "running"
        assert summary["current_step"]["name"] == "test"
        assert summary["current_step"]["position"] == "2/4"
        assert summary["remaining_steps"] == ["deploy", "notify"]
        assert summary["failed_step"] is None

    def test_pending(self) -> None:
        summary = _summarize_pipeline(_pipeline("PENDING"), [])
        assert summary["status"] == "pending"


class TestTailLines:
    """Tests for log tail truncation."""

    def test_truncates_to_last_n(self) -> None:
        text = "\n".join(str(i) for i in range(1000))
        result = _tail_lines(text, 200)
        lines = result.splitlines()
        assert len(lines) == 200
        assert lines[-1] == "999"
        assert lines[0] == "800"

    def test_short_log_not_truncated(self) -> None:
        text = "line1\nline2\nline3"
        assert _tail_lines(text, 200) == text

    def test_zero_returns_whole_log(self) -> None:
        text = "\n".join(str(i) for i in range(500))
        assert _tail_lines(text, 0) == text


class TestResolveLatestPipeline:
    """Tests for PR -> pipeline resolution (commit hash, fallback branch)."""

    @respx.mock
    async def test_resolve_by_commit(self, client: BitbucketClient) -> None:
        pr = {"source": {"commit": {"hash": "abc123"}, "branch": {"name": "feature"}}}
        respx.get("https://api.bitbucket.org/2.0/repositories/ws/repo/pipelines/").mock(
            return_value=Response(200, json={"values": [_pipeline("COMPLETED", "SUCCESSFUL")]})
        )

        pipeline, resolved_by = await _resolve_latest_pipeline(client, "ws", "repo", pr)

        assert resolved_by == "commit"
        assert pipeline is not None

    @respx.mock
    async def test_fallback_to_branch(self, client: BitbucketClient) -> None:
        pr = {"source": {"commit": {"hash": "abc123"}, "branch": {"name": "feature"}}}

        def responder(request: Request) -> Response:
            q = request.url.params.get("q", "")
            if "commit.hash" in q:
                return Response(200, json={"values": []})
            return Response(200, json={"values": [_pipeline("IN_PROGRESS")]})

        respx.get("https://api.bitbucket.org/2.0/repositories/ws/repo/pipelines/").mock(
            side_effect=responder
        )

        pipeline, resolved_by = await _resolve_latest_pipeline(client, "ws", "repo", pr)

        assert resolved_by == "branch"
        assert pipeline is not None

    @respx.mock
    async def test_no_pipeline_found(self, client: BitbucketClient) -> None:
        pr = {"source": {"commit": {"hash": "abc123"}, "branch": {"name": "feature"}}}
        respx.get("https://api.bitbucket.org/2.0/repositories/ws/repo/pipelines/").mock(
            return_value=Response(200, json={"values": []})
        )

        pipeline, resolved_by = await _resolve_latest_pipeline(client, "ws", "repo", pr)

        assert pipeline is None
        assert resolved_by is None
