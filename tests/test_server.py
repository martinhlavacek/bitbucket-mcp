"""Tests for pipeline helpers in the MCP server."""

import json
import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from fastmcp.exceptions import ToolError
from httpx import Request, Response

from bitbucket_mcp import server
from bitbucket_mcp.client import BitbucketClient
from bitbucket_mcp.config import BitbucketConfig
from bitbucket_mcp.server import (
    _pipeline_scope_error,
    _require_stop_allowed,
    _require_trigger_allowed,
    _resolve_latest_pipeline,
    _summarize_pipeline,
    _tail_log,
    bitbucket_stop_pipeline,
    bitbucket_trigger_pipeline,
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

    def test_error_result_surfaces_failed_step(self) -> None:
        pipeline = _pipeline("COMPLETED", "FAILED", build_number=20)
        steps = [
            _step("build", "COMPLETED", "SUCCESSFUL"),
            _step("test", "COMPLETED", "ERROR"),
        ]

        summary = _summarize_pipeline(pipeline, steps)

        assert summary["failed_step"] == {"uuid": "{test}", "name": "test"}

    def test_parallel_running_step_not_listed_as_remaining(self) -> None:
        pipeline = _pipeline("IN_PROGRESS", build_number=21)
        steps = [
            _step("build", "IN_PROGRESS"),
            _step("test", "IN_PROGRESS"),
            _step("deploy", "PENDING"),
        ]

        summary = _summarize_pipeline(pipeline, steps)

        assert summary["current_step"]["name"] == "build"
        # A second concurrently-running step must not be reported as remaining.
        assert summary["remaining_steps"] == ["deploy"]


class TestTailLog:
    """Tests for log tail truncation."""

    def test_truncates_to_last_n(self) -> None:
        text = "\n".join(str(i) for i in range(1000))
        result = _tail_log(text, 200)
        lines = result["log"].splitlines()
        assert result["total_lines"] == 1000
        assert result["returned_lines"] == 200
        assert result["truncated"] is True
        assert lines[-1] == "999"
        assert lines[0] == "800"

    def test_short_log_not_truncated(self) -> None:
        text = "line1\nline2\nline3"
        result = _tail_log(text, 200)
        assert result["log"] == text
        assert result["truncated"] is False
        assert result["total_lines"] == 3

    def test_zero_returns_whole_log(self) -> None:
        text = "\n".join(str(i) for i in range(500))
        result = _tail_log(text, 0)
        assert result["log"] == text
        assert result["truncated"] is False
        assert result["returned_lines"] == 500


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


CREDS = {
    "BITBUCKET_EMAIL": "test@example.com",
    "BITBUCKET_API_TOKEN": "tok",
    "BITBUCKET_WORKSPACE": "ws",
}


def _tool_fn(tool: Any) -> Any:
    """Return the undecorated coroutine behind an MCP tool.

    FastMCP 2.x wraps it in a FunctionTool exposing ``.fn``, while 4.x registers the
    tool and hands the plain function back. The project allows both (fastmcp>=2.0.0),
    so the tests must not depend on which one is installed.
    """
    return getattr(tool, "fn", tool)


def _env(**extra: str) -> dict[str, str]:
    """Build an environment with credentials plus ``extra``.

    Always used with ``clear=True`` so a developer's own BITBUCKET_* settings cannot
    leak in and make a guardrail test pass for the wrong reason.
    """
    return {**CREDS, **extra}


class TestTriggerGuardrails:
    """Tests for the two gates in front of triggering a pipeline."""

    def test_rejected_when_opt_in_missing(self) -> None:
        """Without the global opt-in nothing can be triggered, not even the default."""
        with (
            patch.dict(os.environ, _env(), clear=True),
            pytest.raises(ToolError, match="BITBUCKET_ALLOW_PIPELINE_TRIGGER"),
        ):
            _require_trigger_allowed("my-api", None)

    def test_default_pipeline_needs_no_allowlist_entry(self) -> None:
        """The default pipeline runs what a push would run, so the opt-in alone suffices."""
        with patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True):
            _require_trigger_allowed("my-api", None)

    def test_custom_pipeline_rejected_with_empty_allowlist(self) -> None:
        """An empty allowlist means no custom pipeline, not every custom pipeline."""
        with (
            patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True),
            pytest.raises(ToolError, match="not allowed"),
        ):
            _require_trigger_allowed("my-api", "ci")

    def test_custom_pipeline_allowed_when_listed(self) -> None:
        """A listed repo/pipeline pair passes."""
        env = _env(
            BITBUCKET_ALLOW_PIPELINE_TRIGGER="true",
            BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci",
        )
        with patch.dict(os.environ, env, clear=True):
            _require_trigger_allowed("my-api", "ci")

    def test_same_pipeline_name_in_another_repo_is_rejected(self) -> None:
        """The allowlist is scoped - 'ci' for my-api must not unlock 'ci' for web.

        This is the reason the allowlist is not a flat list of names: one server
        instance serves every repository.
        """
        env = _env(
            BITBUCKET_ALLOW_PIPELINE_TRIGGER="true",
            BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci",
        )
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ToolError, match="not allowed"),
        ):
            _require_trigger_allowed("web", "ci")

    def test_rejection_message_lists_what_is_allowed(self) -> None:
        """The error says what may be run instead of only what may not."""
        env = _env(
            BITBUCKET_ALLOW_PIPELINE_TRIGGER="true",
            BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci,my-api:preview",
        )
        with patch.dict(os.environ, env, clear=True), pytest.raises(ToolError) as excinfo:
            _require_trigger_allowed("my-api", "prod-deploy")

        assert "ci, preview" in str(excinfo.value)


class TestStopGuardrail:
    """Tests for the separate opt-in guarding pipeline stops."""

    def test_allowed_by_default(self) -> None:
        """Stopping is on by default and independent of the trigger opt-in."""
        with patch.dict(os.environ, _env(), clear=True):
            _require_stop_allowed()

    def test_rejected_when_disabled(self) -> None:
        """Test the stop flag can be turned off."""
        with (
            patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_STOP="false"), clear=True),
            pytest.raises(ToolError, match="BITBUCKET_ALLOW_PIPELINE_STOP"),
        ):
            _require_stop_allowed()


class TestPipelineScopeError:
    """Tests for translating a bare 403 into a token-scope explanation."""

    def _error(self, status: int) -> httpx.HTTPStatusError:
        request = Request("POST", "https://api.bitbucket.org/2.0/x")
        return httpx.HTTPStatusError(
            "boom", request=request, response=Response(status, request=request)
        )

    def test_403_names_the_missing_scope(self) -> None:
        """A 403 reads as a repository permission problem unless the scope is named."""
        error = _pipeline_scope_error(self._error(403))

        assert error is not None
        assert "write:pipeline:bitbucket" in str(error)

    def test_other_statuses_are_left_alone(self) -> None:
        """Only 403 is translated; everything else keeps its original error."""
        assert _pipeline_scope_error(self._error(404)) is None


class TestPipelineWriteTools:
    """Tests for the tool functions themselves, past the guardrails."""

    @respx.mock
    async def test_trigger_returns_uuid_and_build_number(self) -> None:
        """The tool answers with the run's identity, it does not wait for it to finish."""
        respx.post("https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/").mock(
            return_value=Response(
                201,
                json={"uuid": "{p9}", "build_number": 42, "state": {"name": "PENDING"}},
            )
        )
        env = _env(
            BITBUCKET_ALLOW_PIPELINE_TRIGGER="true",
            BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci",
        )

        with patch.dict(os.environ, env, clear=True):
            server._client = None
            try:
                result = await _tool_fn(bitbucket_trigger_pipeline)(
                    repo_slug="my-api", ref_name="main", pipeline="ci"
                )
            finally:
                server._client = None

        assert result == {
            "uuid": "{p9}",
            "build_number": 42,
            "state": "PENDING",
            "repo_slug": "my-api",
            "ref_name": "main",
            "pipeline": "ci",
        }

    @respx.mock
    async def test_trigger_reports_default_pipeline(self) -> None:
        """A run without a selector is reported as the default pipeline."""
        respx.post("https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/").mock(
            return_value=Response(201, json={"uuid": "{p10}", "build_number": 43})
        )

        with patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True):
            server._client = None
            try:
                result = await _tool_fn(bitbucket_trigger_pipeline)(
                    repo_slug="my-api", ref_name="main"
                )
            finally:
                server._client = None

        assert result["pipeline"] == "(default)"
        assert result["state"] is None

    @respx.mock
    async def test_trigger_maps_403_to_scope_error(self) -> None:
        """A 403 from Bitbucket surfaces as the scope explanation, not a raw HTTP error."""
        respx.post("https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/").mock(
            return_value=Response(403, json={"error": {"message": "Forbidden"}})
        )

        with patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True):
            server._client = None
            try:
                with pytest.raises(ToolError, match="write:pipeline:bitbucket"):
                    await _tool_fn(bitbucket_trigger_pipeline)(repo_slug="my-api", ref_name="main")
            finally:
                server._client = None

    @respx.mock
    async def test_stop_reports_success(self) -> None:
        """Stopping answers a plain confirmation once Bitbucket accepted the signal."""
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/pipe-1/stopPipeline"
        ).mock(return_value=Response(204))

        with patch.dict(os.environ, _env(), clear=True):
            server._client = None
            try:
                result = await _tool_fn(bitbucket_stop_pipeline)(
                    repo_slug="my-api", pipeline_uuid="pipe-1"
                )
            finally:
                server._client = None

        assert result == {"pipeline_uuid": "pipe-1", "stopped": True}

    @respx.mock
    async def test_stop_maps_403_to_scope_error(self) -> None:
        """The stop tool needs the same write scope, so it explains a 403 the same way."""
        respx.post(
            "https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/pipe-1/stopPipeline"
        ).mock(return_value=Response(403))

        with patch.dict(os.environ, _env(), clear=True):
            server._client = None
            try:
                with pytest.raises(ToolError, match="write:pipeline:bitbucket"):
                    await _tool_fn(bitbucket_stop_pipeline)(
                        repo_slug="my-api", pipeline_uuid="pipe-1"
                    )
            finally:
                server._client = None

    @respx.mock
    async def test_non_403_errors_are_not_rewritten(self) -> None:
        """Only 403 gets the scope explanation - a 500 must keep its own error."""
        respx.post("https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/").mock(
            return_value=Response(500)
        )

        with patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True):
            server._client = None
            try:
                with pytest.raises(httpx.HTTPStatusError):
                    await _tool_fn(bitbucket_trigger_pipeline)(repo_slug="my-api", ref_name="main")
            finally:
                server._client = None

    @respx.mock
    async def test_trigger_maps_variables_to_api_shape(self) -> None:
        """The tool's key/value dict becomes the API's list form, always unsecured."""
        route = respx.post("https://api.bitbucket.org/2.0/repositories/ws/my-api/pipelines/").mock(
            return_value=Response(201, json={"uuid": "{p11}", "build_number": 44})
        )

        with patch.dict(os.environ, _env(BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"), clear=True):
            server._client = None
            try:
                await _tool_fn(bitbucket_trigger_pipeline)(
                    repo_slug="my-api",
                    ref_name="main",
                    variables={"ENV": "staging", "REGION": "eu"},
                )
            finally:
                server._client = None

        body = json.loads(route.calls.last.request.content)
        assert body["variables"] == [
            {"key": "ENV", "value": "staging", "secured": False},
            {"key": "REGION", "value": "eu", "secured": False},
        ]
