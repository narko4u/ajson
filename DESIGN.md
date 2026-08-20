# Design: ajson

This document describes the design of AJSON (Agent JSON): the JSON superset for agent manifests, with a Python reference implementation, CLI, MCP server, and Docker packaging: the actors, the actions
they perform, and the data flow. It accompanies
[THREAT-ASSESSMENT.md](THREAT-ASSESSMENT.md) (threat model) and
[TESTING.md](TESTING.md) (test policy).

## Purpose

Ajson (agent json): the json superset for agent manifests, with a python reference implementation, cli, mcp server, and docker packaging.

## Actors

| Actor | Description |
| --- | --- |
| Manifest author | Writes AJSON manifests using the superset syntax. |
| CLI user | Runs the ajson CLI to validate/convert manifests. |
| MCP client | Connects to the ajson MCP server (mcp-server/). |

## Actions

| Action | Performed by | Implemented in |
| --- | --- | --- |
| Validate/convert manifests | CLI user | `ajson CLI, ajson/` |
| Serve via MCP | MCP client | `mcp-server/` |
| Publish Docker image | CI (release) | `Dockerfile, docker-publish.yml` |

## Data flow

```
repository (main branch)
        │
        ▼
CI (on push / pull_request) ──► validate / test / security jobs
        │
        ▼
tagged release ──► build artifacts + CycloneDX SBOM + Sigstore signatures + SHA256SUMS
```

## Design invariants

1. **Open by construction.** The content is freely licensed and version-controlled.
2. **Minimal dependencies.** Fewer dependencies means a smaller attack surface.
3. **Tamper-evident releases.** Where releases exist, assets carry Sigstore signatures and checksums.
