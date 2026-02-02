# Best Practices Sources

References for Claude Code best practices. Updated periodically via GitHub Action.

## Official Documentation

### Claude Code Best Practices
- **URL**: https://code.claude.com/docs/en/best-practices
- **Last Checked**: 2025-02-01
- **Key Topics**: Context management, verification, CLAUDE.md writing, subagents, hooks

### Claude Code Memory (CLAUDE.md)
- **URL**: https://code.claude.com/docs/en/memory
- **Last Checked**: 2025-02-01
- **Key Topics**: Memory hierarchy, rules, imports, path-specific rules

### Claude Code Skills
- **URL**: https://code.claude.com/docs/en/skills
- **Key Topics**: Creating skills, SKILL.md format, workflows

### Claude Code Sub-agents
- **URL**: https://code.claude.com/docs/en/sub-agents
- **Key Topics**: Agent definitions, tool restrictions, delegation

## Key Best Practices Summary

### CLAUDE.md
- Keep it concise - only include what Claude can't infer from code
- Use `/init` to bootstrap, then refine
- Include: commands Claude can't guess, style rules that differ from defaults, testing instructions
- Exclude: anything Claude can figure out from code, standard conventions, detailed API docs

### Verification
- Give Claude a way to verify its work (tests, screenshots, expected outputs)
- Unit tests are necessary but not sufficient
- Use smoke tests that actually run the code
- For UI: use chrome-devtools MCP for visual verification

### Context Management
- Context window fills fast - performance degrades as it fills
- Use `/clear` between unrelated tasks
- Use subagents for investigation (separate context)
- Scope investigations narrowly

### Rules (`.claude/rules/`)
- Keep rules focused - one topic per file
- Use `paths` frontmatter to scope to specific files
- Use descriptive filenames

### Skills
- Create skills for repeatable workflows
- Use `disable-model-invocation: true` for workflows with side effects
- Include verification steps in all skills

## Community Resources

### Boris Cherny's Tips
- **Source**: https://x.com/bcherny (Twitter/X)
- **Note**: Social media content - check directly for latest

### Anthropic GitHub
- **Claude Code Issues**: https://github.com/anthropics/claude-code/issues
- **Discussions**: Community patterns and solutions

## Update Schedule

This document is checked weekly by GitHub Action `.github/workflows/check-docs.yml`

When significant changes are detected:
1. Action creates an issue with diff summary
2. Human reviews and updates template as needed
3. This file is updated with new "Last Checked" date
