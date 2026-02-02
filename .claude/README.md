# .claude Directory

This directory contains Claude Code configuration, rules, skills, and agents for AI-assisted development.

## Directory Structure

```
.claude/
├── CLAUDE.md              # Main project instructions (loaded every session)
├── settings.json          # MCP servers and permissions
├── README.md              # This file
│
├── rules/                 # Modular coding rules (auto-loaded)
│   ├── python-style.md    # Python conventions
│   ├── testing.md         # Test guidelines
│   └── docker.md          # Docker best practices
│
├── skills/                # Reusable workflows (/skill-name)
│   ├── fix-issue/         # Fix GitHub issues
│   ├── tdd/               # Test-driven development
│   └── review/            # Code review checklist
│
├── agents/                # Specialized subagents
│   ├── security-reviewer.md
│   └── test-writer.md
│
├── configs/               # Tool configurations
│   └── mcp/               # MCP server documentation
│
├── planning/              # Planning documents
│   ├── decisions/         # Architectural Decision Records (ADRs)
│   └── features/          # Feature planning
│
├── prompts/               # Prompt templates
│   └── README.md
│
├── research/              # Research documentation
│   └── README.md
│
└── docs/                  # Reference documentation
    ├── high-fidelity/     # Detailed, verified docs
    └── summaries/         # Quick reference
```

## Key Files

### CLAUDE.md

Loaded at the start of every Claude Code session. Contains:
- Project overview and commands
- Code style guidelines
- Learnings and gotchas

**Best practice:** Keep it concise. Only include what Claude can't infer from code.

### settings.json

MCP server configuration and permission allowlists:
- `chrome-devtools`: Headless browser automation
- `pylsp`: Python language server

### Rules (`rules/`)

Modular, file-scoped instructions. Use YAML frontmatter to scope to paths:

```markdown
---
paths:
  - "src/**/*.py"
---
# Python Rules
...
```

### Skills (`skills/`)

Reusable workflows invoked with `/skill-name`:
- `/fix-issue 123` - Fix a GitHub issue
- `/tdd` - TDD workflow
- `/review` - Code review checklist

### Agents (`agents/`)

Specialized subagents that run in isolated context:
- `security-reviewer` - Security vulnerability analysis
- `test-writer` - Test generation

## Usage

### View Loaded Memory

```
/memory
```

Shows all CLAUDE.md files and rules currently loaded.

### Invoke a Skill

```
/fix-issue 123
/tdd Add email validation
/review src/core.py
```

### Use a Subagent

```
Use the security-reviewer agent to review the auth module.
Use a subagent to write tests for the new feature.
```

## Adding Content

### New Rule

Create `.claude/rules/my-rule.md`:

```markdown
---
paths:
  - "src/api/**/*.py"
---
# API Rules

- Always validate input
- Return consistent error format
```

### New Skill

Create `.claude/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: Does something useful
---
# My Skill

Instructions for Claude when this skill is invoked.
```

### New Agent

Create `.claude/agents/my-agent.md`:

```markdown
---
name: my-agent
description: Specialized for X
tools: Read, Grep, Glob
model: sonnet
---
You are a specialist in X. Your job is to...
```

## Best Practices

1. **Keep CLAUDE.md small** - Move details to rules
2. **Scope rules narrowly** - Use `paths` frontmatter
3. **Create skills for workflows** - Not just instructions
4. **Use agents for isolation** - Separate context, focused tasks
5. **Document learnings** - Add gotchas to CLAUDE.md

---

See [Claude Code docs](https://code.claude.com/docs/en/memory) for more details.
