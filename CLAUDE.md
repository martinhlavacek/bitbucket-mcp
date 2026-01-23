# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Bitbucket MCP is a Model Context Protocol (MCP) server for Bitbucket Cloud API. It enables AI assistants like Claude to interact with Bitbucket repositories, pull requests, and branches.

Built with [FastMCP](https://gofastmcp.com) framework.

## Build & Development Commands

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run single test
pytest tests/test_file.py::test_function_name -v

# Run with coverage
pytest --cov=src/bitbucket_mcp --cov-report=html

# Lint
ruff check src tests

# Format
ruff format src tests

# Type check
mypy src --ignore-missing-imports

# Run the server (stdio transport)
python -m bitbucket_mcp

# Run with HTTP transport
fastmcp run src/bitbucket_mcp/server.py:mcp --transport http --port 8000
```

## Required Environment Variables

```bash
export BITBUCKET_USERNAME="your-username"
export BITBUCKET_APP_PASSWORD="your-app-password"
export BITBUCKET_WORKSPACE="optional-default-workspace"
```

## Project Structure

```
src/bitbucket_mcp/
├── __init__.py      # Package exports
├── __main__.py      # CLI entry point
├── config.py        # Configuration from environment
├── client.py        # Bitbucket API HTTP client
└── server.py        # FastMCP server with tools
tests/
├── test_config.py   # Config tests
└── test_client.py   # Client tests with mocked API
```

## Architecture

- **FastMCP Server** (`server.py`): Exposes tools via MCP protocol
- **BitbucketClient** (`client.py`): Async HTTP client for Bitbucket API
- **BitbucketConfig** (`config.py`): Environment-based configuration

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `bitbucket_get_repo` | Get repository information |
| `bitbucket_list_branches` | List repository branches |
| `bitbucket_list_prs` | List pull requests |
| `bitbucket_get_pr` | Get PR details |
| `bitbucket_create_pr` | Create new PR |
| `bitbucket_merge_pr` | Merge PR |
| `bitbucket_approve_pr` | Approve PR |
| `bitbucket_unapprove_pr` | Remove approval |
| `bitbucket_decline_pr` | Decline PR |
| `bitbucket_get_diff` | Get PR diff |
| `bitbucket_add_comment` | Add comment to PR |
| `bitbucket_list_comments` | List PR comments |

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring

## Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all functions
- Write docstrings for public functions
- 100 character line length
- Use async/await for API calls
