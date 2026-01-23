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
export BITBUCKET_WORKSPACE="your-workspace"  # optional default workspace
```

## Usage

### With Claude Code

**Via CLI:**

```bash
claude mcp add --transport stdio \
  --env BITBUCKET_EMAIL=your-email@example.com \
  --env BITBUCKET_API_TOKEN=your-api-token \
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
        "BITBUCKET_API_TOKEN": "your-api-token"
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
  martinhlavacek/bitbucket-mcp:latest
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

### Build Locally

```bash
docker build -t bitbucket-mcp .
docker run -d -p 8000:8000 \
  -e BITBUCKET_EMAIL=your-email@example.com \
  -e BITBUCKET_API_TOKEN=your-api-token \
  bitbucket-mcp
```

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
