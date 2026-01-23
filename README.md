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

### Bitbucket App Password

1. Go to [Bitbucket App Passwords](https://bitbucket.org/account/settings/app-passwords/)
2. Create a new App Password with required permissions:
   - `repository:read`
   - `repository:write`
   - `pullrequest:read`
   - `pullrequest:write`

### Environment Variables

```bash
export BITBUCKET_USERNAME="your-username"
export BITBUCKET_APP_PASSWORD="your-app-password"
export BITBUCKET_WORKSPACE="your-workspace"  # optional default workspace
```

## Usage

### With Claude Code

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "python",
      "args": ["-m", "bitbucket_mcp"],
      "env": {
        "BITBUCKET_USERNAME": "your-username",
        "BITBUCKET_APP_PASSWORD": "your-app-password"
      }
    }
  }
}
```

### Standalone

```bash
python -m bitbucket_mcp
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
