<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/narko4u/ajson/main/assets/ajson-dark.svg">
  <img alt="AJSON — Agent JSON" src="https://raw.githubusercontent.com/narko4u/ajson/main/assets/ajson-light.svg">
</picture>

# AJSON — Agent JSON

**A superset of JSON purpose-built for autonomous agent communication, with deterministic compilation to canonical JSON.**

[![Tests](https://img.shields.io/badge/tests-25%20passing-brightgreen)](https://github.com/narko4u/ajson)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Built by Sovereign](https://img.shields.io/badge/built%20by-Sovereign-8A2BE2)](https://github.com/narko4u/ajson)

---

## Why AJSON?

JSON is the lingua franca of AI agents. Every LLM API, every tool-calling framework, every agent protocol speaks JSON. But JSON was designed for machines to parse, not for humans — or other agents — to write.

**AJSON fixes this without breaking anything.** It's a superset of JSON: every valid JSON file is valid AJSON. Write with superpowers, compile to canonical JSON for runtime.

```ajson
// AIP Contract in AJSON — comments, multi-line, and reusable references
{
  "contract_name": "Data Process",
  
  "description": """A data processing contract between
two autonomous agents governed by WitnessOS.""",

  // Reusable terms template
  "&terms": {
    "max_retries": 3,
    "sla_seconds": 60,
    "jurisdiction": "AU"
  },

  "contract_terms": {"*terms": null}
}
```

**Compiles to clean, deterministic JSON:**

```json
{"contract_name":"Data Process","contract_terms":{"jurisdiction":"AU","max_retries":3,"sla_seconds":60},"description":"A data processing contract between\ntwo autonomous agents governed by WitnessOS."}
```

---

## Features

| Feature | JSON | AJSON |
|---|---|---|
| Comments (`//` and `/* */`) | ❌ | ✅ |
| Multi-line strings (`"""..."""`) | ❌ | ✅ |
| Reusable references (`&anchor` / `*ref`) | ❌ | ✅ |
| Deterministic output (sorted keys) | ❌ (depends on library) | ✅ Always |
| Self-documenting schemas (`@type`, `@desc`) | ❌ | ✅ |
| Valid JSON — zero migration cost | — | ✅ Every JSON is valid AJSON |
| Zero dependencies | — | ✅ Pure Python stdlib |

---

## Quick Start

### Install

```bash
pip install ajson
```

Or use directly from source:

```bash
python3 -m ajson contract.ajson -o contract.json
```

### CLI Usage

```bash
# Compile AJSON to canonical JSON
ajson compile contract.ajson -o contract.json

# Validate an AJSON file
ajson validate contract.ajson

# Expand (show compiled tree)
ajson expand contract.ajson

# Watch mode — recompile on file change
ajson watch contract.ajson -o contract.json
```

### Python API

```python
from ajson import compile_ajson

ajson_text = """
// My contract
{
  "name": "example",
  "description": """Multi-line
description here""",
  "&schema": {"type": "object"},
  "data": {"*schema": null}
}
"""

canonical_json = compile_ajson(ajson_text)
# '{"data":{"type":"object"},"description":"Multi-line\\ndescription here","name":"example"}'
```

---

## Language Reference

### Comments

Both `//` line comments and `/* block comments */` are supported. Comments are stripped during compilation and never appear in the output.

```ajson
{
  // Line comment
  "a": 1,
  
  /* Block
     comment */
  "b": 2
}
```

### Multi-Line Strings

Triple-quoted strings (`"""..."""`) allow multi-line values with automatic dedentation.

```ajson
{
  "description": """This is a long
  description that spans multiple
  lines without ugly \n escaping."""
}
```

### References (Anchors & Dereferences)

Inspired by YAML anchors, AJSON supports reusable value templates:

```ajson
{
  // Define once
  "&schema": {
    "type": "object",
    "required": ["id", "timestamp"]
  },
  
  // Use everywhere
  "input": {"*schema": null},
  "output": {"*schema": null}
}
```

References are resolved at compile time with deep copy semantics. Circular references are detected and rejected.

### Inline Annotations

Annotations provide self-documenting schemas that are stripped from the output but available for tooling:

```ajson
{
  "max_records": @type "uint" 1000,
  "priority":   @type "enum" @default "normal" "high"
}
```

---

## Why Not YAML?

YAML is the natural comparison — it has comments, multi-line strings, and anchors. But YAML has critical problems for agent communication:

| Problem | YAML | AJSON |
|---|---|---|
| `yes` → boolean, `NO` → null | ✅ Untrapped pitfalls | ❌ Impossible |
| Indentation-dependent | ✅ Fragile | ❌ Bracket-delimited |
| Multiple valid representations | ✅ Non-deterministic | ❌ Always canonical |
| Agent framework support | ❌ None | ✅ Compiles to exactly what agents consume |
| Deterministic signing | ❌ Broken | ✅ Natural |

AJSON gives you the ergonomics of YAML with the determinism and agent-compatibility of JSON.

---

## Use Cases

- **AIP (Agent Interaction Protocol)**: Write contract templates with inline documentation, compile to signed JSON for agent execution
- **WitnessOS governance**: Self-documenting compliance manifests that compile to verifiable evidence receipts
- **ACI capability descriptions**: Rich capability files with reusable schema references
- **Agent-to-agent manifests**: Any structured data that agents exchange, with comments for human review

---

## Integration with Empire Labs Stack

AJSON is the authoring format for the [Empire Labs](https://empirelabs.com.au) agent ecosystem:

- **[AIP](https://github.com/narko4u/aip-spec)** — Agent Interaction Protocol (contract templates written in AJSON)
- **[WitnessOS](https://empirelabs.com.au)** — Agent governance and compliance (evidence receipts in AJSON)
- **[ACI](https://aci-spec.org)** — Autonomous Company Interface (capability descriptions in AJSON)

---

## Roadmap

| Version | Features |
|---|---|
| **v0.1** (current) | Comments, multi-line strings, references, canonical output, CLI |
| **v0.2** | Inline schema annotations, `@type`/`@desc`/`@default` support |
| **v0.3** | File inclusion (`@include "schema.ajson"`), multi-file compilation |
| **v0.4** | MCP server (agents use AJSON directly via MCP tools) |
| **v1.0** | Stable spec, language server, IDE integration |

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

This project follows the [ACI Code of Conduct](https://aci-spec.org/code-of-conduct).

---

## 🍻 Buy the Empire a Pint

If AJSON saved your agents from YAML hell and JSON purgatory, buy the Empire a pint. We like to split the G.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/empirelabs)

**Pay what you want.** No tiers, no rewards, no strings. Just a cold pint and a thank you from the Empire.

Every donation helps keep this project sovereign, dependency-free, and maintained on Empire time.

---

## License

AJSON is open source under the MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Empire Labs Pty Ltd

*Built by Empire Labs Pty Ltd | Maintained by **Sovereign** (Autonomous Agent)*
