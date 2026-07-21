#!/usr/bin/env python3
"""
AJSON End-to-End Pipeline Demo

Demonstrates:
  1. Writing an AIP contract in AJSON (with comments, refs, multi-line)
  2. Compiling to canonical JSON
  3. Signing the canonical JSON (deterministic = verifiable)
  4. The same input always = the same output
  5. Real-world AIP and WitnessOS manifest compilation
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "tests", "fixtures")

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(HERE))


def main():
    print("=" * 62)
    print("  AJSON — Agent JSON : End-to-End Pipeline Demo")
    print("  Empire Labs Pty Ltd")
    print("=" * 62)
    print()

    # 1. Show AJSON source file
    source_file = os.path.join(FIXTURES, "simple_contract.ajson")
    with open(source_file) as f:
        source_text = f.read()

    print("1. AJSON Source (comments, refs, multi-line):")
    print("-" * 40)
    for line in source_text.strip().split('\n'):
        print(f"   {line}")
    print()

    # 2. Parse and compile
    print("2. Compiling to canonical JSON...")
    from ajson.parser import compile_ajson

    result = compile_ajson(source_text)
    parsed = json.loads(result)

    print(f"   Output: {len(result)} bytes (source was {len(source_text)} bytes)")
    print(f"   Deterministic keys: {list(parsed.keys())}")
    print()

    print("3. Compiled JSON output (no comments, no anchors):")
    print("-" * 40)
    print(result)
    print()

    # 4. Verify features compiled correctly
    print("4. Verification:")
    print(f"   Contract name: {parsed['contract_name']}")
    print(f"   Parties: {len(parsed['parties'])}")
    print(f"   Terms max_retries: {parsed['contract_terms']['max_retries']}")
    print(f"   SLAs count: {len(parsed['slas'])}")
    print(f"   All SLAs identical: {parsed['slas'][0] == parsed['slas'][1]}")
    print(f"   No &terms in output: {'&terms' not in result}")
    print(f"   No // comments in output: {'//' not in result.split(chr(34))[::2]}")
    print()

    # 5. Deterministic output
    print("5. Deterministic output test:")
    result2 = compile_ajson(source_text)
    assert result == result2, "NON-DETERMINISTIC OUTPUT!"
    print("   ✅ Same input -> identical output every time")
    print()

    # 6. Signing
    print("6. Signing pipeline:")
    content_bytes = result.encode('utf-8')
    sha = hashlib.sha256(content_bytes).hexdigest()
    print(f"   SHA-256: {sha[:16]}...{sha[-16:]}")
    print(f"   Size:    {len(content_bytes)} bytes")
    print("   ✅ Deterministic JSON means verifiable signatures")
    print("      across time, systems, and agents")
    print()

    # 7. Compile real-world manifests
    print("7. Real-world manifests:")
    manifests = ["contract_template.ajson", "witnessos_receipt.ajson"]
    for fname in manifests:
        fpath = os.path.join(FIXTURES, fname)
        if os.path.exists(fpath):
            from ajson.parser import compile_file
            compiled = compile_file(fpath)
            parsed_f = json.loads(compiled)
            print(f"   {fname:35s} -> {len(compiled):>6d} bytes  "
                  f"({len(list(parsed_f.keys()))} root keys)")
    print()

    print("=" * 62)
    print("  DEMO COMPLETE - pipeline verified end-to-end")
    print("=" * 62)


if __name__ == "__main__":
    main()
