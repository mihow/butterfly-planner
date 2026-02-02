# Planning Documentation

Store planning documents, architectural decisions, and feature specifications.

## Structure

```
planning/
├── decisions/     # Architectural Decision Records (ADRs)
├── features/      # Feature planning and specs
└── README.md      # This file
```

## Decisions (ADRs)

Use Architectural Decision Records for significant technical decisions:

```markdown
# ADR-001: [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded
**Date:** YYYY-MM-DD

## Context

What is the issue we're addressing?

## Decision

What did we decide?

## Consequences

What are the results of this decision?
```

## Features

Use feature specs for new functionality:

```markdown
# Feature: [Name]

## Goal

What problem does this solve?

## Requirements

- [ ] Requirement 1
- [ ] Requirement 2

## Implementation

High-level approach...

## Testing

How will we verify this works?
```
