# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Config

issue-provider: github
git-provider: github
repo-url: https://github.com/martinhlavacek/bitbucket-mcp

## Branch Naming

pattern: {scope}/gh-{id}-{name}

## Build Commands

build: pytest
test: ruff check src tests && pytest

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
export BITBUCKET_EMAIL="your-email@example.com"
export BITBUCKET_API_TOKEN="your-api-token"
export BITBUCKET_WORKSPACE="optional-default-workspace"
```

> Legacy `BITBUCKET_USERNAME` + `BITBUCKET_APP_PASSWORD` also supported for backward compatibility.

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

## Archon Task Management

**VŽDY** používej Archon MCP pro task management během implementace.

### Tool Reference

**Projects:**

- `find_projects(query="...")` - Search projects
- `find_projects(project_id="...")` - Get specific project
- `manage_project("create"/"update"/"delete", ...)` - Manage projects

**Tasks:**

- `find_tasks(query="...")` - Search tasks by keyword
- `find_tasks(task_id="...")` - Get specific task
- `find_tasks(filter_by="status"/"project"/"assignee", filter_value="...")` - Filter tasks
- `manage_task("create"/"update"/"delete", ...)` - Manage tasks

**Knowledge Base:**

- `rag_get_available_sources()` - List all sources
- `rag_search_knowledge_base(query="...", source_id="...")` - Search docs
- `rag_search_code_examples(query="...", source_id="...")` - Find code

### Important Notes

- Task status flow: `todo` → `doing` → `review` → `done`
- Keep queries SHORT (2-5 keywords) for better search results
- Higher `task_order` = higher priority (0-100)
- Tasks should be 30 min - 4 hours of work
- **VŽDY aktualizuj task status** při změně fáze práce

## Default Workflow

### Příprava

- Vytvoř projekt v Archon přes MCP
- Zeptej se na **cube** a **milestone** pokud nejsou uvedeny v issue
- Vytvoř v Archonu tasky pro implementaci
- Vždy vytvoř jako poslední task "Code review" (zůstane v todo dokud není vše hotovo)
- Ulož implementační plán do Archon docs jako **markdown** (ne JSON!)
- Vytvoř branch ve formátu `{scope}/gh-{issue-id}-{nazev-issue}`
- Propoj branch s projektem přes MCP

### Implementace

- **Průběžně aktualizuj tasky v Archonu** (doing → review → done)
- Po dokončení každé fáze IHNED aktualizuj příslušný task
- Testy musí vždy pokrývat nové funkcionality

### Dokončení

- Ověř že jde aplikace zbuildovat
- Ověř že všechny linty jsou OK
- Ověř že všechny testy prošly
- Vytvoř PR, propoj s projektem přes MCP
- Task "Code review" přesuň z todo do review
- **Ostatní implementační tasky přesuň do done**

### Po merge

- Aktualizuj stav issue (closed)
- Aktualizuj stav PR (merged) přes MCP
- Task "Code review" přesuň do done
