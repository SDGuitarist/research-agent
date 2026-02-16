---
status: complete
priority: p3
issue_id: "035"
tags: [code-review, security, dependencies]
dependencies: []
---

# Dependencies Use Minimum Version Pins Only

## Problem Statement

`requirements.txt` uses only `>=` version pins with no lock file. This allows untested newer versions to be installed, risking breakage or supply chain issues.

## Findings

- **Source:** Security Sentinel agent
- **Location:** `requirements.txt`

## Proposed Solutions

### Option A: Add requirements.lock (Recommended)
Generate a lock file with exact versions while keeping `requirements.txt` as the loose spec.
- **Effort:** Small (15 min)

## Acceptance Criteria

- [ ] Lock file exists with pinned versions
- [ ] `requirements.txt` unchanged (loose spec)
