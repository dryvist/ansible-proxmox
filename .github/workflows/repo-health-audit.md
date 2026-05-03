---
description: "Daily repository health audit"
engine: copilot

on:
  schedule: daily
  workflow_dispatch:

imports:
  - JacobPEvans/ai-workflows/.github/workflows/shared/repo-health-audit-config.md@3cd52eb8879fa1c4170b4c9753d002d2888e99b8

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read
  security-events: read

timeout-minutes: 15
---

# Repo Health Audit

{{#runtime-import JacobPEvans/ai-workflows/.github/workflows/shared/repo-health-audit-prompt.md@3cd52eb8879fa1c4170b4c9753d002d2888e99b8}}
