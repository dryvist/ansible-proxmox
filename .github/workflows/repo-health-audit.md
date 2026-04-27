---
description: "Daily repository health audit"
engine: copilot

on:
  schedule: daily
  workflow_dispatch:

imports:
  - JacobPEvans/ai-workflows/.github/workflows/shared/repo-health-audit-config.md@feat/shared-health-audit

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read
  security-events: read

timeout-minutes: 15
---

# Repo Health Audit

{{#import JacobPEvans/ai-workflows/.github/workflows/shared/repo-health-audit-prompt.md@feat/shared-health-audit}}
