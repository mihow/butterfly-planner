# MCP Server Configurations

Model Context Protocol (MCP) server configurations for Claude Code.

**Official Docs:** https://modelcontextprotocol.io/

## Recommended Servers

This template includes two recommended MCP servers pre-configured for safe, isolated operation.

### 1. Chrome DevTools

Browser automation for UI testing, screenshots, and web interaction.

**Features:**
- Headless mode (no visible browser window)
- Isolated profile (no access to your browser data)
- Sandboxed execution

```json
{
  "chrome-devtools": {
    "command": "npx",
    "args": [
      "-y",
      "@anthropic/mcp-server-chrome-devtools",
      "--headless",
      "--isolated"
    ]
  }
}
```

**Install:**
```bash
npm install -g @anthropic/mcp-server-chrome-devtools
```

### 2. Python Language Server (pylsp)

Enhanced Python intelligence for accurate code navigation.

**Features:**
- Go-to-definition
- Find all references
- Symbol search
- Hover documentation
- Real-time diagnostics

```json
{
  "pylsp": {
    "command": "pylsp",
    "args": [],
    "env": {
      "PYTHONPATH": "${workspaceFolder}/src"
    }
  }
}
```

**Install:**
```bash
uv pip install python-lsp-server[all]
# or
pip install python-lsp-server[all]
```

### Alternative: Pyright (Stricter Type Checking)

```json
{
  "pyright": {
    "command": "pyright-langserver",
    "args": ["--stdio"]
  }
}
```

**Install:**
```bash
npm install -g pyright
```

## Complete Configuration

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-chrome-devtools", "--headless", "--isolated"]
    },
    "pylsp": {
      "command": "pylsp",
      "args": [],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

## Other Useful Servers

| Server | Purpose | Install |
|--------|---------|---------|
| filesystem | Scoped file access | `npx @modelcontextprotocol/server-filesystem` |
| github | GitHub API | `npx @modelcontextprotocol/server-github` |
| postgres | Database queries | `npx @modelcontextprotocol/server-postgres` |
| fetch | HTTP requests | `npx @modelcontextprotocol/server-fetch` |

## Troubleshooting

### Server Not Found
```bash
which npx
which pylsp
npm list -g @anthropic/mcp-server-chrome-devtools
```

### Debug Mode
```bash
claude --verbose
```

### Chrome Issues
```bash
# Check Chrome is installed
which google-chrome || which chromium

# Test headless mode
npx @anthropic/mcp-server-chrome-devtools --headless --test
```

---

**See Also:**
- [Official MCP Docs](https://modelcontextprotocol.io/)
- [Available Servers](https://github.com/modelcontextprotocol/servers)
