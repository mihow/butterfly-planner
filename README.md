# Claude-First Python Template

A GitHub template for building Python projects with Claude Code as a first-class development partner.

## Features

- **Claude-First Development**: Pre-configured `.claude/` directory with CLAUDE.md, rules, skills, and agents
- **Modern Python**: Python 3.12+ with type hints, Pydantic, pytest
- **uv Package Management**: Fast, reliable dependency management
- **Test-Driven Development**: pytest setup with fixtures, markers, and coverage
- **Docker Support**: Multi-stage Dockerfile and docker-compose for development
- **CI/CD**: GitHub Actions workflow for lint, test, typecheck, and build
- **MCP Servers**: Pre-configured chrome-devtools and Python language server

## Quick Start

### Use This Template

1. Click **"Use this template"** on GitHub
2. Clone your new repository
3. Customize `pyproject.toml` (project name, description, author)
4. Rename `src/my_project/` to your package name
5. Update imports in tests and `.claude/CLAUDE.md`

### Local Setup

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests

# Start development
claude  # Opens Claude Code
```

### Docker Setup

```bash
# Run tests in container
docker compose run --rm test

# Development shell
docker compose run --rm dev

# Build production image
docker build -t my-project --target production .
```

## Project Structure

```
.
├── .claude/                    # Claude Code configuration
│   ├── CLAUDE.md              # Main project instructions
│   ├── settings.json          # MCP servers & permissions
│   ├── rules/                 # Modular coding rules
│   │   ├── python-style.md    # Python conventions
│   │   ├── testing.md         # Test guidelines
│   │   └── docker.md          # Docker best practices
│   ├── skills/                # Reusable Claude skills
│   │   ├── fix-issue/         # Fix GitHub issues
│   │   ├── tdd/               # Test-driven development
│   │   └── review/            # Code review checklist
│   ├── agents/                # Specialized subagents
│   │   ├── security-reviewer.md
│   │   └── test-writer.md
│   └── configs/               # Tool configurations
│       └── mcp/               # MCP server setup
├── .github/workflows/         # CI/CD pipelines
│   └── test.yml              # Lint, test, build workflow
├── src/my_project/            # Main package
│   ├── __init__.py
│   ├── cli.py                # Command-line interface
│   ├── config.py             # Configuration management
│   ├── core.py               # Business logic
│   └── models.py             # Pydantic data models
├── tests/                     # Test suite
│   ├── conftest.py           # Shared fixtures
│   ├── test_config.py
│   ├── test_core.py
│   └── test_models.py
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml         # Development services
├── pyproject.toml             # Project configuration
├── Makefile                   # Common commands
└── README.md                  # This file
```

## Claude Code Integration

### CLAUDE.md

The `.claude/CLAUDE.md` file is loaded at the start of every Claude Code session. It contains:
- Project overview and key commands
- Code style guidelines
- Project structure reference
- Learnings and gotchas

Keep it concise - only include things Claude can't infer from code.

### Rules (`.claude/rules/`)

Modular, topic-specific instructions that apply to matching files:

```markdown
---
paths:
  - "src/**/*.py"
---
# Python Style Rules
- Use modern type hints (list[str], X | None)
- Follow project conventions
```

### Skills (`.claude/skills/`)

Reusable workflows invoked with `/skill-name`:

- `/fix-issue 123` - Fix a GitHub issue from start to PR
- `/tdd` - Test-driven development workflow
- `/review` - Code review checklist

### Agents (`.claude/agents/`)

Specialized subagents for isolated tasks:

- `security-reviewer` - Security vulnerability analysis
- `test-writer` - Comprehensive test generation

### MCP Servers

Pre-configured in `.claude/settings.json`:

- **chrome-devtools**: Headless browser for UI testing
- **pylsp**: Python language server for code intelligence

Install dependencies:
```bash
npm install -g @anthropic/mcp-server-chrome-devtools
uv pip install python-lsp-server[all]
```

## Development Commands

```bash
# Tests
pytest                          # Run all tests
pytest --cov=my_project         # With coverage
pytest -m "not slow"            # Skip slow tests

# Code Quality
ruff check src tests            # Lint
ruff format src tests           # Format
mypy src                        # Type check

# Verification (CRITICAL - run before declaring done)
make verify                     # Full verification suite
make verify-mcp                 # Check MCP servers installed

# Docker
docker compose run --rm test    # Tests in container
docker compose run --rm lint    # Lint in container
docker compose run --rm dev     # Development shell

# CLI
my-project info                 # Show app info
my-project run --name example   # Run example
```

## Verification Philosophy

**Code is not "done" until it's verified running.**

This template enforces a verification-first approach:

1. **Unit tests are necessary but not sufficient** - Tests can be written to pass
2. **Smoke tests verify real execution** - `tests/test_smoke.py` actually runs the CLI
3. **`make verify` runs full suite** - Imports, tests, smoke tests, CLI execution
4. **MCP servers must be verified** - `make verify-mcp` checks they're actually installed

See `.claude/rules/verification.md` for the complete verification checklist.

## Customization Checklist

After creating a repository from this template:

- [ ] Update `pyproject.toml`:
  - [ ] Change `name` from "my-project"
  - [ ] Update `description`
  - [ ] Update `authors`
  - [ ] Update `project.urls`
  - [ ] Add/remove dependencies
- [ ] Rename `src/my_project/` to your package name
- [ ] Update imports in all Python files
- [ ] Update `.claude/CLAUDE.md` with project-specific info
- [ ] Update `.claude/rules/` if needed
- [ ] Configure MCP servers in `.claude/settings.json`
- [ ] Update this README
- [ ] Delete example code and write your own

## Best Practices

### For Claude Code

1. **Keep CLAUDE.md concise** - Only include what Claude can't infer from code
2. **Use rules for details** - Put specific guidelines in `.claude/rules/`
3. **Create skills for workflows** - Repeatable tasks become `/skill-name`
4. **Delegate to subagents** - Use agents for isolated, focused tasks
5. **Add learnings** - Document gotchas as you discover them

### For Development

1. **Write tests first** - Use `/tdd` skill for TDD workflow
2. **Commit often** - Small, focused commits
3. **Use type hints** - Modern Python 3.10+ style
4. **Run linters** - `ruff check` before committing
5. **Verify in Docker** - `docker compose run --rm test`

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with Claude Code
