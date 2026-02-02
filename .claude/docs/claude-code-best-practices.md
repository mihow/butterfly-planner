# Claude Code Best Practices Reference

> Condensed from official docs at https://code.claude.com/docs/en/best-practices
> Last updated: 2025-02-01

## Core Principle

**Context window fills fast, and performance degrades as it fills.**

Claude's context window holds your entire conversation, files read, and command outputs. Managing this is the most important resource constraint.

---

## 1. Give Claude a Way to Verify Its Work

**This is the single highest-leverage thing you can do.**

| Strategy | Before | After |
|----------|--------|-------|
| Provide verification criteria | "implement email validation" | "write validateEmail. test: user@example.com=true, invalid=false. run tests after" |
| Verify UI visually | "make it look better" | "[paste screenshot] implement this. screenshot result and compare" |
| Address root causes | "build is failing" | "build fails with [error]. fix it and verify build succeeds" |

For UI changes, use chrome-devtools MCP to:
- Navigate to pages
- Take screenshots
- Test interactions
- Iterate until correct

---

## 2. Explore First, Then Plan, Then Code

**Separate research and planning from implementation.**

1. **Explore** (Plan Mode): Read files, understand codebase
2. **Plan** (Plan Mode): Create detailed implementation plan
3. **Implement** (Normal Mode): Code with verification
4. **Commit**: Descriptive message and PR

Skip planning for trivial tasks (typo fixes, one-line changes).

---

## 3. Provide Specific Context

| Strategy | Before | After |
|----------|--------|-------|
| Scope the task | "add tests for foo.py" | "write test for foo.py covering logged-out edge case. avoid mocks" |
| Point to sources | "why is ExecutionFactory weird?" | "look through ExecutionFactory git history, summarize how API evolved" |
| Reference patterns | "add calendar widget" | "look at HotDogWidget.php for patterns. follow pattern for new calendar widget" |

**Rich content options:**
- `@filename` to reference files
- Paste images directly
- Give URLs for documentation
- Pipe data: `cat log | claude`

---

## 4. Write an Effective CLAUDE.md

**Run `/init` to generate starter, then refine.**

### Include
- Bash commands Claude can't guess
- Code style rules that differ from defaults
- Testing instructions
- Repository etiquette
- Architectural decisions
- Developer environment quirks

### Exclude
- Anything Claude can figure out from code
- Standard language conventions
- Detailed API documentation (link instead)
- Information that changes frequently
- File-by-file descriptions
- Self-evident practices

**Keep it concise.** If Claude keeps ignoring a rule, the file is too long.

### Imports
```markdown
See @README.md for overview and @package.json for npm commands.

# Additional
- Git workflow: @docs/git-instructions.md
```

---

## 5. Use Modular Rules (`.claude/rules/`)

Organize instructions into focused files:

```
.claude/rules/
├── code-style.md
├── testing.md
└── security.md
```

**Path-specific rules:**
```markdown
---
paths:
  - "src/api/**/*.ts"
---
# API Rules
- Include input validation
- Use standard error format
```

---

## 6. Create Skills for Workflows

Skills extend Claude's knowledge and provide repeatable workflows.

```markdown
# .claude/skills/fix-issue/SKILL.md
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix GitHub issue: $ARGUMENTS
1. Use `gh issue view` to get details
2. Search codebase
3. Implement fix
4. Write tests
5. Create PR
```

Invoke with `/fix-issue 1234`

---

## 7. Use Subagents for Investigation

Subagents run in separate context windows, keeping your main conversation clean.

```
Use subagents to investigate how authentication handles token refresh.
```

The subagent explores, reads files, and reports back a summary without cluttering your context.

---

## 8. Manage Context Aggressively

- **`/clear`** between unrelated tasks
- **`/compact <instructions>`** to summarize while preserving key info
- **Subagents** for research (separate context)
- **Rewind** with `Esc Esc` or `/rewind` to restore previous state

---

## 9. Course-Correct Early

- **`Esc`**: Stop mid-action, context preserved
- **`Esc Esc`** or **`/rewind`**: Open rewind menu
- **`"Undo that"`**: Have Claude revert changes
- **`/clear`**: Reset context

If you've corrected Claude more than twice on the same issue, `/clear` and start fresh with a better prompt.

---

## 10. Common Failure Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Kitchen sink session | Unrelated tasks pollute context | `/clear` between tasks |
| Correcting over and over | Context polluted with failed approaches | `/clear` after 2 failures, write better prompt |
| Over-specified CLAUDE.md | Important rules get lost | Ruthlessly prune |
| Trust-then-verify gap | Plausible but broken code | Always provide verification |
| Infinite exploration | Hundreds of files read | Scope narrowly, use subagents |

---

## Quick Reference

### Verification Before "Done"
```bash
python -c "from my_project import *"  # Imports work
pytest -x                              # Tests pass
pytest tests/test_smoke.py             # Smoke tests
my-project info                        # CLI runs
```

### Context Commands
- `/clear` - Reset context
- `/compact` - Summarize context
- `/memory` - View loaded CLAUDE.md files
- `/rewind` - Restore previous state

### File Locations
- `./CLAUDE.md` or `./.claude/CLAUDE.md` - Project instructions
- `./.claude/rules/*.md` - Modular rules
- `./.claude/skills/*/SKILL.md` - Skills
- `./.claude/agents/*.md` - Subagent definitions
- `./CLAUDE.local.md` - Personal project preferences (gitignored)
- `~/.claude/CLAUDE.md` - User-level instructions

---

*Source: https://code.claude.com/docs/en/best-practices*
*See `.github/workflows/check-docs.yml` for automated update checks*
