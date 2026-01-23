# Contributing to Bitbucket MCP

Thank you for your interest in contributing to Bitbucket MCP! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/martinhlavacek/bitbucket-mcp/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

### Suggesting Features

1. Check existing issues and discussions first
2. Create a new issue with the `enhancement` label
3. Describe the feature and its use case

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. Make your changes following our coding standards
4. Write or update tests as needed
5. Ensure all tests pass:
   ```bash
   pytest
   ```
6. Commit with conventional commit messages:
   ```bash
   git commit -m "feat: add new bitbucket tool"
   ```
7. Push and create a Pull Request

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring

### Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/bitbucket-mcp.git
   cd bitbucket-mcp
   ```

2. Create virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small

## Questions?

Feel free to open an issue for any questions!
