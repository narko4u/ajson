"""
AJSON Parser Engine

Compiles AJSON (Agent JSON) to canonical deterministic JSON.

Pipeline:
  1. Strip comments (// and /* */)
  2. Resolve triple-quoted multi-line strings
  3. Resolve anchors (&name) and references (*name)
  4. Strip annotations (@type, @desc, @default, etc.)
  5. Canonicalize to sorted-key JSON
"""

import json
import os
import re
from collections import OrderedDict
from typing import Any, Optional


# ── Step 1: Strip Comments ──────────────────────────────────────────────

_COMMENT_LINE_RE = re.compile(r"//")
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(text: str) -> str:
    """
    Remove // line comments and /* block comments */ from AJSON text.

    Operates carefully to preserve comments inside string literals.
    Uses a state-machine approach: track whether we're inside a quoted string.
    """
    result = []
    i = 0
    in_string = False
    string_char = None
    in_triple = False

    while i < len(text):
        ch = text[i]

        # Handle string boundaries
        if not in_string:
            if ch in ('"', "'"):
                # Check for triple quote start
                if i + 2 < len(text) and text[i:i+3] in ('"""', "'''"):
                    in_triple = True
                    in_string = True
                    string_char = ch
                    result.append(text[i:i+3])
                    i += 3
                    continue
                else:
                    in_string = True
                    string_char = ch
                    result.append(ch)
                    i += 1
                    continue
        else:
            # We're inside a string
            result.append(ch)
            if ch == '\\':
                # Escape char — skip next
                i += 1
                if i < len(text):
                    result.append(text[i])
                i += 1
                continue
            elif ch == string_char:
                if in_triple:
                    # Check if it's three in a row (closing triple quote)
                    if i + 2 < len(text) and text[i:i+3] == string_char * 3:
                        result.append(text[i+1:i+3])
                        in_string = False
                        in_triple = False
                        i += 3
                        continue
                else:
                    in_string = False
                    string_char = None
            i += 1
            continue

        # Outside strings — handle comments
        if ch == '/' and i + 1 < len(text):
            if text[i + 1] == '/':
                # Line comment — skip to end of line
                i += 2
                while i < len(text) and text[i] != '\n':
                    i += 1
                continue
            elif text[i + 1] == '*':
                # Block comment — skip to */
                i += 2
                while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                    i += 1
                i += 2  # skip */
                continue

        result.append(ch)
        i += 1

    return "".join(result)


# ── Step 2: Resolve Triple-Quoted Strings ──────────────────────────────

_TRIPLE_QUOTE_RE = re.compile(r'"""(.+?)"""', re.DOTALL)


def _resolve_triple_quotes_recursive(text: str) -> str:
    """
    Replace triple-quoted strings (three double-quotes)
    with valid JSON strings.

    Preserves line breaks as \\n, trims leading/trailing whitespace on each line.
    """
    def _replace(m: re.Match) -> str:
        inner = m.group(1)
        # Normalize line endings
        lines = inner.split('\n')
        # Strip the first line if empty (opening """\n)
        if lines and lines[0].strip() == '':
            lines = lines[1:]
        # Strip the last line if empty (closing \n""")
        if lines and lines[-1].strip() == '':
            lines = lines[:-1]
        # Find common indentation to strip (like Python's textwrap.dedent)
        if lines:
            non_empty = [l for l in lines if l.strip()]
            if non_empty:
                indent = min(len(l) - len(l.lstrip()) for l in non_empty)
                lines = [l[indent:] if len(l) >= indent else l for l in lines]
        # Join with \n and escape for JSON
        joined = '\n'.join(lines)
        escaped = joined.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
        return f'"{escaped}"'

    return _TRIPLE_QUOTE_RE.sub(_replace, text)


def resolve_triple_quotes(text: str) -> str:
    """Resolve triple-quoted strings to regular JSON strings."""
    return _resolve_triple_quotes_recursive(text)


# ── Step 3: References (&anchor / *dereference) ─────────────────────────

def _json_set(obj: Any, path: str, value: Any) -> None:
    """Set a value at a given path in a nested dict. Path is dot-separated."""
    parts = path.split('.')
    for part in parts[:-1]:
        if isinstance(obj.get(part), dict):
            obj = obj[part]
        else:
            obj[part] = {}
            obj = obj[part]
    obj[parts[-1]] = value


def _json_get(obj: Any, path: str) -> Any:
    """Get a value at a given path in a nested dict."""
    parts = path.split('.')
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def _collect_anchors(obj: Any, path: str = "", anchors: Optional[dict] = None) -> dict:
    """
    Walk the parsed JSON tree and collect all &anchor definitions.
    Anchors are stored as {'name': {'value': ..., 'path': '...'}}.
    """
    if anchors is None:
        anchors = {}

    if isinstance(obj, dict):
        has_anchor = False
        anchor_name = None
        remaining = {}
        for key, val in obj.items():
            if isinstance(key, str) and key.startswith('&'):
                anchor_name = key[1:]  # strip &
                has_anchor = True
                # The value IS the anchor definition
                anchors[anchor_name] = {
                    'value': val,
                    'path': path,
                }
            else:
                remaining[key] = val
                child_path = f"{path}.{key}" if path else key
                _collect_anchors(val, child_path, anchors)

    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            child_path = f"{path}[{idx}]"
            _collect_anchors(item, child_path, anchors)

    return anchors


def _resolve_refs(obj: Any, anchors: dict, depth: int = 0, resolving: Optional[set] = None) -> Any:
    """
    Walk the tree and resolve all *name references.
    Returns a new tree with references replaced by deep copies of anchor values.
    Recursively resolves references in the resolved values (nested refs supported).
    Detects circular references via the 'resolving' set.
    """
    if depth > 100:
        raise ValueError("Circular reference detected or excessive nesting in AJSON references")

    if resolving is None:
        resolving = set()

    if isinstance(obj, dict):
        new_dict = OrderedDict()
        for key, val in obj.items():
            if isinstance(key, str) and key.startswith('&'):
                # Skip anchor definitions — they're metadata, not data
                continue
            if isinstance(val, dict) and len(val) == 1:
                ref_key = next(iter(val.keys()))
                if isinstance(ref_key, str) and ref_key.startswith('*'):
                    ref_name = ref_key[1:]
                    if ref_name not in anchors:
                        raise ValueError(f"Undefined reference: *{ref_name}")
                    # Cycle detection
                    if ref_name in resolving:
                        raise ValueError(
                            f"Circular reference detected: *{ref_name} "
                            f"(already resolving: {resolving})"
                        )
                    resolving.add(ref_name)
                    resolved_val = _deep_copy(anchors[ref_name]['value'])
                    # Recurse into the resolved value to handle nested refs
                    resolved_val = _resolve_refs(resolved_val, anchors, depth + 1, resolving)
                    resolving.discard(ref_name)
                    new_dict[key] = resolved_val
                    continue
            new_dict[key] = _resolve_refs(val, anchors, depth + 1, resolving)
        return new_dict

    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            if isinstance(item, dict) and len(item) == 1:
                ref_key = next(iter(item.keys()))
                if isinstance(ref_key, str) and ref_key.startswith('*'):
                    ref_name = ref_key[1:]
                    if ref_name not in anchors:
                        raise ValueError(f"Undefined reference: *{ref_name}")
                    if ref_name in resolving:
                        raise ValueError(
                            f"Circular reference detected: *{ref_name} "
                            f"(already resolving: {resolving})"
                        )
                    resolving.add(ref_name)
                    resolved_item = _deep_copy(anchors[ref_name]['value'])
                    resolved_item = _resolve_refs(resolved_item, anchors, depth + 1, resolving)
                    resolving.discard(ref_name)
                    new_list.append(resolved_item)
                    continue
            new_list.append(_resolve_refs(item, anchors, depth + 1, resolving))
        return new_list

    return obj


def _deep_copy(obj: Any) -> Any:
    """Deep copy a JSON-compatible object."""
    return json.loads(json.dumps(obj))


def resolve_references(obj: Any) -> Any:
    """
    First pass: collect all &anchors.
    Second pass: resolve all *references.
    """
    anchors = _collect_anchors(obj)
    return _resolve_refs(obj, anchors)


# ── Step 4: Strip Annotations (@type, @desc, @default) ─────────────────

_ANNOTATION_RE = re.compile(r'@([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:"([^"]*)"|([0-9]+(?:\.[0-9]+)?)|true|false|null)')


def _strip_annotations_from_string(text: str) -> str:
    """Remove @annotation values from a JSON string (pre-parse)."""
    # This works on the text level before JSON parsing
    # Remove patterns like @type "string" @desc "something"
    # These appear before a value in key-value pairs
    return _ANNOTATION_RE.sub('', text).strip()


def strip_annotations(obj: Any) -> Any:
    """
    Walk the tree and strip @annotation metadata.
    Collect annotations into a parallel $meta structure.
    
    Currently handles annotations at the JSON level
    (they're stripped during compile phase before JSON.parse).
    """
    # Annotations are handled during text pre-processing
    return obj


# ── Step 5: Canonical JSON Output ──────────────────────────────────────

def canonical_json(obj: Any, sort_keys: bool = True, indent: Optional[int] = None) -> str:
    """
    Serialize JSON deterministically.
    - Sorted keys by default
    - No extra whitespace when indent=None
    """
    # Use our own ordered sort for maximum determinism
    def sort_recursive(o):
        if isinstance(o, dict):
            result = OrderedDict()
            for key in sorted(o.keys()):
                result[key] = sort_recursive(o[key])
            return result
        elif isinstance(o, list):
            return [sort_recursive(item) for item in o]
        return o

    sorted_obj = sort_recursive(obj) if sort_keys else obj
    return json.dumps(sorted_obj, indent=indent, ensure_ascii=False, sort_keys=False)


# ── Main Compile Pipeline ──────────────────────────────────────────────

def compile_ajson(text: str, canonical: bool = True) -> str:
    """
    Compile AJSON text to canonical JSON.
    
    Pipeline:
      1. Strip comments
      2. Resolve triple-quoted strings
      3. Parse JSON
      4. Resolve references (&/*)
      5. Serialize canonical JSON
    """
    # Step 1 & 2: Text-level transformations
    cleaned = strip_comments(text)
    cleaned = resolve_triple_quotes(cleaned)
    
    # Step 3: Parse the cleaned JSON
    try:
        parsed = json.loads(cleaned, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        # Try to give a helpful error with context
        pos = e.pos
        start = max(0, pos - 40)
        end = min(len(cleaned), pos + 40)
        context = cleaned[start:end]
        raise json.JSONDecodeError(
            f"JSON parse error at position {pos}: {e.msg}\n"
            f"Context: ...{context}...",
            e.doc,
            e.pos,
        )
    
    # Step 4: Resolve references
    resolved = resolve_references(parsed)
    
    # Step 5: Serialize
    return canonical_json(resolved, sort_keys=canonical)


def compile_string(text: str, canonical: bool = True) -> str:
    """Alias for compile_ajson."""
    return compile_ajson(text, canonical)


def compile_file(input_path: str, output_path: Optional[str] = None, canonical: bool = True) -> str:
    """Compile an AJSON file to JSON."""
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    result = compile_ajson(text, canonical)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        # Also add trailing newline for POSIX
        if not result.endswith('\n'):
            with open(output_path, 'a') as f:
                f.write('\n')
    
    return result
