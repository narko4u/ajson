"""
AJSON - Agent JSON
A superset of JSON that compiles to canonical deterministic JSON.

Features:
  - Comments (// line and /* block */)
  - Multi-line strings (triple-quoted)
  - References (&anchor / *dereference, like YAML but deterministic)
  - Inline annotations (@type, @desc, @default, etc.)
  - Deterministic canonical output (sorted keys, no whitespace)

Copyright (c) 2026 Empire Labs Pty Ltd
SPDX-License-Identifier: MIT
"""

from .parser import (
    strip_comments,
    resolve_triple_quotes,
    compile_ajson,
    compile_file,
    compile_string,
)

__all__ = [
    "strip_comments",
    "resolve_triple_quotes",
    "compile_ajson",
    "compile_file",
    "compile_string",
]
__version__ = "0.1.1"
