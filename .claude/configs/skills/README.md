# Claude Skills

Reusable skills for Claude Code.

## What are Skills?

Skills are modular capabilities that can be invoked with `/skill-name` in Claude Code.

**Official Docs:** https://docs.claude.ai/docs/skills

## Active Skills

Document your actively used skills here.

### Standard Skills

List your commonly used built-in or custom skills:

- `/commit` - Create git commits with proper formatting
- `/review-pr` - Review pull requests
- `/test` - Run test suite and analyze results
- `/deploy` - Deploy application
- `/docs` - Generate documentation

### Custom Skills

#### Example: Code Review Skill

```yaml
# ~/.claude/skills/code-review/skill.yaml
name: code-review
description: Comprehensive code review with checklist
version: 1.0.0

prompts:
  - name: review
    template: |
      Review this code for:
      - Logic errors
      - Security vulnerabilities
      - Performance issues
      - Code style
      - Test coverage

      ```
      {code}
      ```

tools:
  - name: run-linter
    command: ruff check {file}
  - name: run-tests
    command: pytest {test_file}
```

## Creating Skills

### 1. Create Skill Directory

```bash
mkdir -p ~/.claude/skills/my-skill
```

### 2. Create skill.yaml

```yaml
name: my-skill
description: What this skill does
version: 1.0.0

prompts:
  - name: main
    template: |
      Your prompt template here
      Use {variables} for substitution

tools:
  - name: my-tool
    command: echo "Hello"
```

### 3. Test Skill

```bash
claude
> /my-skill
```

## Skill Templates

### Test Generation Skill

```yaml
name: generate-tests
description: Generate unit tests for code
version: 1.0.0

prompts:
  - name: generate
    template: |
      Generate comprehensive unit tests for this code:

      ```{language}
      {code}
      ```

      Include:
      - Happy path tests
      - Edge cases
      - Error handling
      - Mock external dependencies

tools:
  - name: run-tests
    command: pytest -v {test_file}
```

### Documentation Skill

```yaml
name: document-code
description: Generate documentation for code
version: 1.0.0

prompts:
  - name: docstrings
    template: |
      Add comprehensive docstrings to this code:

      ```{language}
      {code}
      ```

      Follow {style_guide} style.

tools:
  - name: check-docs
    command: pydoc-markdown --check {file}
```

## Best Practices

1. **Single Responsibility**: Each skill does one thing well
2. **Reusable**: Works across projects
3. **Well-Documented**: Clear description and examples
4. **Tested**: Verify skill works as expected
5. **Versioned**: Track changes to skills

## Skill Organization

```
~/.claude/skills/
├── code-review/
│   ├── skill.yaml
│   └── README.md
├── test-generation/
│   ├── skill.yaml
│   └── examples/
├── deployment/
│   ├── skill.yaml
│   └── scripts/
└── documentation/
    ├── skill.yaml
    └── templates/
```

## Sharing Skills

Skills can be shared via:
- Git repositories
- npm packages
- Direct file sharing

```bash
# Install skill from repo
git clone https://github.com/user/claude-skill-name ~/.claude/skills/skill-name

# Or symlink from this repo
ln -s $(pwd)/.claude/configs/skills/my-skill ~/.claude/skills/my-skill
```

## Troubleshooting

### Skill Not Found
```bash
# Check skill directory
ls ~/.claude/skills/

# Verify skill.yaml syntax
cat ~/.claude/skills/my-skill/skill.yaml
```

### Skill Not Loading
- Check YAML syntax
- Verify skill name matches directory
- Restart Claude Code

---

**See Also:**
- [Official Skills Docs](https://docs.claude.ai/docs/skills)
- [Skill Examples](https://github.com/anthropics/claude-skills)
