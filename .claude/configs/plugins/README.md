# IDE Plugins & Extensions

IDE plugins, extensions, and tooling configurations.

## VS Code Extensions

### Claude Code Integration

```json
// .vscode/extensions.json
{
  "recommendations": [
    "anthropic.claude-code",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml"
  ]
}
```

### Settings

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

## Vim/Neovim Plugins

### Claude.vim (hypothetical)

```vim
" ~/.vimrc or ~/.config/nvim/init.vim

" Claude Code integration
Plug 'anthropic/claude.vim'

" Configure Claude
let g:claude_model = 'claude-3-5-sonnet-20241022'
let g:claude_auto_complete = 1

" Keybindings
nmap <leader>ca :ClaudeAsk<CR>
nmap <leader>cc :ClaudeComplete<CR>
nmap <leader>cr :ClaudeRefactor<CR>
```

## Git Hooks

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run tests
echo "Running tests..."
./run_tests.sh || exit 1

# Run linter
echo "Running linter..."
ruff check . || exit 1

# Run formatter check
echo "Checking formatting..."
black --check . || exit 1

echo "✅ Pre-commit checks passed"
```

### Pre-push Hook

```bash
#!/bin/bash
# .git/hooks/pre-push

# Run full test suite
echo "Running full test suite..."
pytest tests/ -v || exit 1

# Check for sensitive data
echo "Checking for secrets..."
git diff --cached --name-only | xargs grep -l "API_KEY\|SECRET\|PASSWORD" && exit 1

echo "✅ Pre-push checks passed"
```

## Linters & Formatters

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"

select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]

ignore = [
    "E501",  # line too long (handled by black)
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # Unused imports
"tests/*" = ["S101"]  # Assert usage
```

### Black Configuration

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ["py310"]
include = '\.pyi?$'
```

### MyPy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Tmux Configuration

```bash
# ~/.tmux.conf

# Better mouse support
set -g mouse on

# Scrollback history
set -g history-limit 10000

# Vi mode
setw -g mode-keys vi

# Status bar
set -g status-style bg=black,fg=green
set -g status-right "#[fg=cyan]#H #[fg=white]%H:%M"

# Pane borders
set -g pane-border-style fg=white
set -g pane-active-border-style fg=green

# Reload config
bind r source-file ~/.tmux.conf \; display "Reloaded!"
```

## Shell Aliases

```bash
# ~/.bashrc or ~/.zshrc

# Claude Code
alias claude='npx @anthropic/claude-code'
alias cl='claude'

# Testing
alias test='./run_tests.sh'
alias testw='watch -n 2 ./run_tests.sh'  # Watch tests

# Git
alias gs='git status'
alias gd='git diff'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

# Python
alias py='python3'
alias pip='python3 -m pip'
alias venv='python3 -m venv .venv && source .venv/bin/activate'

# Docker
alias dps='docker ps'
alias dcu='docker-compose up'
alias dcd='docker-compose down'
alias dcl='docker-compose logs -f'
```

## EditorConfig

```ini
# .editorconfig

root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100

[*.{yml,yaml,json}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

## Installation

### Setup Script

```bash
#!/bin/bash
# install-plugins.sh

echo "Installing development tools..."

# VS Code extensions
code --install-extension anthropic.claude-code
code --install-extension ms-python.python
code --install-extension charliermarsh.ruff

# Git hooks
cp .claude/configs/plugins/hooks/* .git/hooks/
chmod +x .git/hooks/*

# Tmux config
ln -sf $(pwd)/.claude/configs/plugins/tmux.conf ~/.tmux.conf

# Shell aliases
echo "# CTO Sidekick aliases" >> ~/.bashrc
cat .claude/configs/plugins/aliases.sh >> ~/.bashrc

echo "✅ Plugins installed"
```

---

**See Also:**
- [VS Code Extensions](https://marketplace.visualstudio.com/vscode)
- [Vim Plugins](https://vimawesome.com/)
- [Git Hooks](https://git-scm.com/docs/githooks)
