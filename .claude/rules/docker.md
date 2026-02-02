---
paths:
  - "Dockerfile"
  - "docker-compose.yml"
  - ".dockerignore"
---

# Docker Rules

## Multi-stage Builds

- `base`: Python + uv setup
- `dependencies`: Install dependencies (cached)
- `development`: Full dev environment with all tools
- `test`: Run tests during build
- `production`: Minimal image, non-root user

## Compose Services

- `dev`: Development shell with mounted source
- `test`: Run test suite
- `lint`: Run linting
- `app`: Production container

## Best Practices

- Use `--rm` flag for one-off containers
- Mount source read-only (`:ro`) except for output dirs
- Use named volumes for caches
- Don't include secrets in images
