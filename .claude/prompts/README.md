# Prompt Templates

Store reusable prompt templates here.

## Purpose

This directory is for:
- Common prompt patterns
- System prompts for specific tasks
- Prompt engineering experiments

## Organization

Group by category:
- `code-review/` - Code review prompts
- `testing/` - Test generation prompts
- `documentation/` - Doc generation prompts

## Template

```markdown
# [Prompt Name]

**Purpose:** Brief description

**Variables:**
- `$CODE` - The code to analyze
- `$CONTEXT` - Additional context

---

[Actual prompt text with $VARIABLES]
```

## Usage

Reference prompts in skills or copy content directly.

## Guidelines

### Writing Good Prompts

1. **Be Specific**: Clear instructions and expectations
2. **Use Examples**: Show desired output format
3. **Set Context**: Provide relevant background
4. **Request Structure**: Ask for JSON/markdown for parsing

### Variable Naming

Use clear, descriptive variable names:
- `{task_description}` not `{task}`
- `{git_diff}` not `{diff}`
- `{project_name}` not `{proj}`
