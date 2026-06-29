---
type: policy
title: Data Protection Policy
description: Enterprise data protection, classification, and handling requirements
tags: ["compliance", "data-protection", "security", "GDPR", "privacy"]
timestamp: 2026-06-29T12:00:00Z
status: approved
author: Legal Department
---

# Data Protection Policy

## Data Classification

All data must be classified into one of three tiers:

| Tier | Category | Examples |
|------|----------|---------|
| Tier 1 | Public | Marketing materials, press releases |
| Tier 2 | Internal | Internal documentation, org charts |
| Tier 3 | Confidential | PII, financial records, trade secrets |

## Handling Requirements

- **Tier 3 data** must be encrypted at rest (AES-256) and in transit (TLS 1.3).
- Access to Tier 3 data requires explicit role-based authorization.
- All data breaches must be reported to the [Security Team](../engineering/security-incident-response.md) within 1 hour.

## Remote Work

Employees handling Tier 3 data while remote must follow the [Remote Work Policy](../hr/remote-work-policy.md) and use VPN at all times.
