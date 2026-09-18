# Bitbucket MCP

[![CI](https://github.com/martinhlavacek/bitbucket-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/martinhlavacek/bitbucket-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP (Model Context Protocol) server for Bitbucket Cloud API. Enables AI assistants like Claude to interact with Bitbucket repositories, pull requests, and branches.

## Features

- 🔀 **Pull Requests** - Create, list, merge, approve, decline, and comment on PRs
- 🌿 **Branches** - List repository branches
- 📁 **Repositories** - Get repository information
- 🔍 **Diffs** - View PR diffs and changes
- 💬 **Comments** - Add and list PR comments
- 🚦 **Pipelines** - Read run status and logs; trigger and stop runs (opt-in)

## Installation

Install from source:

```bash
git clone https://github.com/martinhlavacek/bitbucket-mcp.git
cd bitbucket-mcp
pip install -e .
```

## Configuration

### Bitbucket API Token

> **Note:** App Passwords were deprecated in September 2025. Use API tokens instead.

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token with scopes**
3. Select **Bitbucket** as the application
4. Add required scopes:
   - `repository:read`
   - `repository:write`
   - `pullrequest:read`
   - `pullrequest:write`
5. Copy the token (it's only shown once!)

### Environment Variables

```bash
export BITBUCKET_EMAIL="your-email@example.com"
export BITBUCKET_API_TOKEN="your-api-token"
export BITBUCKET_WORKSPACE="your-workspace"  # optional, can be passed per-request
```

> **Finding your workspace:** The workspace is the first part of your Bitbucket repository URL:
> `https://bitbucket.org/{workspace}/{repo}` - for example, if your repo URL is
> `https://bitbucket.org/acme-corp/my-project`, your workspace is `acme-corp`.

## Usage

### With Claude Code

**Via CLI:**

```bash
claude mcp add --transport stdio \
  --env BITBUCKET_EMAIL=your-email@example.com \
  --env BITBUCKET_API_TOKEN=your-api-token \
  --env BITBUCKET_WORKSPACE=your-workspace \
  bitbucket -- python -m bitbucket_mcp
```

**Or add to your MCP configuration file:**

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "python",
      "args": ["-m", "bitbucket_mcp"],
      "env": {
        "BITBUCKET_EMAIL": "your-email@example.com",
        "BITBUCKET_API_TOKEN": "your-api-token",
        "BITBUCKET_WORKSPACE": "your-workspace"
      }
    }
  }
}
```

### Standalone

```bash
python -m bitbucket_mcp
```

## Docker

### Run with Docker

```bash
docker run -d \
  -p 8000:8000 \
  -e BITBUCKET_EMAIL=your-email@example.com \
  -e BITBUCKET_API_TOKEN=your-api-token \
  -e BITBUCKET_WORKSPACE=your-workspace \
  hlavaceklab/bitbucket-mcp:latest
```

### Connect Claude Code to Remote Server

**Via CLI:**

```bash
claude mcp add --transport http bitbucket http://localhost:8000/mcp
```

**Via JSON config:**

```json
{
  "mcpServers": {
    "bitbucket": {
      "url": "http://your-server:8000/mcp"
    }
  }
}
```

### Docker Compose

Create a `.env` file with your credentials:

```bash
BITBUCKET_EMAIL=your-email@example.com
BITBUCKET_API_TOKEN=your-api-token
BITBUCKET_WORKSPACE=your-workspace
```

Run with Docker Compose:

```bash
docker compose up -d
```

### Build Locally

```bash
docker build -t bitbucket-mcp .
docker run -d -p 8000:8000 \
  -e BITBUCKET_EMAIL=your-email@example.com \
  -e BITBUCKET_API_TOKEN=your-api-token \
  -e BITBUCKET_WORKSPACE=your-workspace \
  bitbucket-mcp
```

### Monitoring Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check (JSON) |
| `/metrics` | Prometheus metrics |

## Available Tools

| Tool | Description |
|------|-------------|
| `bitbucket_get_repo` | Get repository information |
| `bitbucket_list_branches` | List repository branches |
| `bitbucket_list_prs` | List pull requests |
| `bitbucket_get_pr` | Get pull request details |
| `bitbucket_create_pr` | Create a new pull request |
| `bitbucket_merge_pr` | Merge a pull request |
| `bitbucket_approve_pr` | Approve a pull request |
| `bitbucket_unapprove_pr` | Remove approval from a PR |
| `bitbucket_decline_pr` | Decline a pull request |
| `bitbucket_get_diff` | Get PR diff |
| `bitbucket_add_comment` | Add comment to a PR |
| `bitbucket_list_comments` | List PR comments |
| `bitbucket_get_pr_pipeline` | Get the latest CI pipeline status for a PR (running / passed / failed) |
| `bitbucket_get_pipeline_step_log` | Get a pipeline step's log (last 200 lines by default) |
| `bitbucket_list_pipelines` | List recent pipelines, optionally filtered by branch |
| `bitbucket_get_pipeline` | Get a pipeline with its per-step breakdown |
| `bitbucket_trigger_pipeline` | Trigger a pipeline run (opt-in, see below) |
| `bitbucket_stop_pipeline` | Signal a running pipeline to stop |

### Pipeline write operations

Triggering a pipeline is the one operation here that can spend build minutes and deploy to
an environment, so it is off by default and gated by two independent settings.

```bash
export BITBUCKET_ALLOW_PIPELINE_TRIGGER="true"
export BITBUCKET_PIPELINE_ALLOWLIST="my-api:ci,my-api:preview,web:ci"
export BITBUCKET_ALLOW_PIPELINE_STOP="true"   # this is the default
```

| Variable | Default | Answers |
| --- | --- | --- |
| `BITBUCKET_ALLOW_PIPELINE_TRIGGER` | `false` | May pipelines be triggered at all? |
| `BITBUCKET_PIPELINE_ALLOWLIST` | empty | Which custom pipelines may be triggered? |
| `BITBUCKET_ALLOW_PIPELINE_STOP` | `true` | May a running pipeline be stopped? |

The allowlist is scoped per repository (`repo-slug:pipeline-name`) because one server
instance serves every repository - a bare pipeline name would let a `deploy` allowed for a
staging repo also run the production `deploy` of another one. An empty allowlist means *no*
custom pipeline may run, not every one.

Running a branch's **default** pipeline needs no allowlist entry: it runs what a push to
that branch would have run anyway, so it cannot deploy anything a push could not.

> **Token scope:** these two tools need `write:pipeline:bitbucket`. It does **not** imply
> `read:pipeline:bitbucket`, which the read-only pipeline tools already use, so add it to
> your API token rather than swapping the existing scope.

#### Where to set these

The settings are read from the environment of the **server process**, so they belong wherever
that process is started - not in the client that connects to it.

Running the server over HTTP (Docker, shared host) rather than stdio, the client config holds
only a URL and no environment at all; the variables go on the host running the container:

```yaml
# docker-compose.yml on the server
services:
  bitbucket-mcp:
    image: hlavaceklab/bitbucket-mcp:latest
    environment:
      - BITBUCKET_ALLOW_PIPELINE_TRIGGER=true
      - BITBUCKET_PIPELINE_ALLOWLIST=my-api:ci,web:preview
```

```bash
docker compose up -d   # a restart is required; the config is read from the process env
```

> **A shared server means a shared allowlist.** One container serves every client that can
> reach it, so enabling the trigger enables it for all of them, running under the token
> configured on that host. There is no per-client or per-session scoping.

## Development

```bash
# Clone
git clone https://github.com/martinhlavacek/bitbucket-mcp.git
cd bitbucket-mcp

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Test
pytest

# Lint
ruff check .
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [FastMCP](https://gofastmcp.com) - Python framework for MCP servers
- [MCP Specification](https://modelcontextprotocol.io) - Model Context Protocol
- [GitHub MCP](https://github.com/modelcontextprotocol/servers) - Official GitHub MCP server
