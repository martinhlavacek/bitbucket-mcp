# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server for Bitbucket Cloud API, providing tools for pull requests, branches, and repositories management.

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
```

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix  
- `docs:` - Documentation changes
- `test:` - Test changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring

## Code Style

- Follow PEP 8
- Use type hints for all functions
- Write docstrings for public functions
