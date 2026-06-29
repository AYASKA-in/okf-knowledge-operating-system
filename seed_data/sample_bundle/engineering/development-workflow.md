---
type: procedure
title: Development Workflow
description: Standard git-based development workflow for engineering teams
tags: ["engineering", "git", "workflow", "development"]
timestamp: 2026-06-29T12:00:00Z
status: approved
author: Engineering Lead
---

# Development Workflow

## Branch Strategy

- `main` — Production-ready code. Protected, requires PR review.
- `develop` — Integration branch for feature work.
- `feature/*` — Individual feature branches branched from `develop`.

## Pull Request Process

1. Create a feature branch from `develop`.
2. Write tests and ensure all existing tests pass.
3. Submit a PR against `develop` with a clear description.
4. At least one senior engineer must approve.
5. Merge using squash-merge.

## Deployment

Refer to the [Deployment Guide](./deployment-guide.md) for release procedures.
