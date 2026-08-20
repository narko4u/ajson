# VEX - Vulnerability Exploitability eXchange

Status: current as of the latest release. Reviewed before each release.

This document states the exploitability status of known vulnerabilities in the
components of this project, per the OSPS VM-04.02 control.
"Not affected" means the vulnerable component is present in the supply chain
but the vulnerable code path cannot be reached or does not affect the
shipped artifact.

## Component inventory

| Component | Type | Version | Published? |
|-----------|------|---------|------------|
| ajson package | Python package | 0.1.0 | Yes |
| ajson CLI | CLI entry point | 0.1.0 | Yes |
| mcp-server/ | MCP server | 0.1.0 | Yes |
| Docker image | Container | 0.1.0 | Yes |

## Statements

| Component | Vulnerability | Status | Justification |
|-----------|---------------|--------|---------------|
| Published content | (any) | Not affected | Static content does not execute; integrity is covered by version control and release signing |
| Shipped tooling | (any) | Under assessment | Assessed at release time against reachable code paths |
| CI/build components | (any) | Not affected | Not shipped to end users; only ever run in ephemeral CI on trusted inputs |

## Change policy

- This VEX is updated whenever a new component is added, a vulnerability is
  reported, or a release is prepared.
- New releases must not ship while a High or Medium severity finding in a
  reachable component is unresolved (see `SECURITY.md` remediation thresholds).
