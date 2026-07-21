#!/usr/bin/env python3
"""
AJSON CLI — Agent JSON Compiler

Usage:
  ajson compile <input.ajson> [-o output.json]
  ajson validate <input.ajson>
  ajson expand <input.ajson>        # Show parsed tree with annotations
  ajson watch <input.ajson> -o <output.json>
  ajson version

Copyright (c) 2026 Empire Labs Pty Ltd
SPDX-License-Identifier: MIT
"""

import argparse
import json
import os
import sys
import time


def _load_parser():
    """Lazy import to avoid circular deps in setup."""
    from ajson.parser import compile_ajson, compile_file
    return compile_ajson, compile_file


def cmd_compile(args):
    compile_ajson, compile_file = _load_parser()
    
    if args.output:
        result = compile_file(args.input, args.output)
        size = os.path.getsize(args.output)
        print(f"✅ Compiled {args.input} → {args.output} ({size:,} bytes)")
    else:
        result = compile_file(args.input)
        sys.stdout.write(result)
        if not result.endswith('\n'):
            sys.stdout.write('\n')


def cmd_validate(args):
    compile_ajson, _ = _load_parser()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        
        result = compile_ajson(text)
        
        # Validate it's parseable JSON
        parsed = json.loads(result)
        
        print(f"✅ Valid AJSON: {args.input}")
        print(f"   Object type: {type(parsed).__name__}")
        if isinstance(parsed, dict):
            print(f"   Top-level keys: {len(parsed)}")
        elif isinstance(parsed, list):
            print(f"   Array length: {len(parsed)}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid AJSON: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Invalid AJSON: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_expand(args):
    """Show the compiled tree with metadata."""
    compile_ajson, _ = _load_parser()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        
        result = compile_ajson(text)
        parsed = json.loads(result)
        
        print(json.dumps(parsed, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_watch(args):
    compile_ajson, _ = _load_parser()
    
    last_mtime = 0
    print(f"👀 Watching {args.input} → {args.output} (Ctrl+C to stop)")
    
    try:
        while True:
            mtime = os.path.getmtime(args.input)
            if mtime > last_mtime:
                last_mtime = mtime
                try:
                    with open(args.input, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    result = compile_ajson(text)
                    
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(result)
                        f.write('\n')
                    
                    size = len(result)
                    print(f"  ⏱ {time.strftime('%H:%M:%S')} — Compiled ({size:,} bytes)")
                except Exception as e:
                    print(f"  ⚠️ {time.strftime('%H:%M:%S')} — Error: {e}", file=sys.stderr)
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n👋 Watch stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="AJSON — Agent JSON Compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ajson compile manifest.ajson -o manifest.json
  ajson validate manifest.ajson
  ajson expand manifest.ajson
  ajson watch manifest.ajson -o manifest.json
        """,
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # compile
    compile_parser = subparsers.add_parser("compile", help="Compile AJSON to JSON")
    compile_parser.add_argument("input", help="Input .ajson file")
    compile_parser.add_argument("-o", "--output", help="Output .json file (default: stdout)")
    
    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate AJSON file")
    validate_parser.add_argument("input", help="Input .ajson file")
    
    # expand
    expand_parser = subparsers.add_parser("expand", help="Show compiled tree")
    expand_parser.add_argument("input", help="Input .ajson file")
    
    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch file and recompile on change")
    watch_parser.add_argument("input", help="Input .ajson file")
    watch_parser.add_argument("-o", "--output", required=True, help="Output .json file")
    
    args = parser.parse_args()
    
    if args.version:
        from ajson import __version__
        print(f"AJSON v{__version__}")
        return
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    command_map = {
        "compile": cmd_compile,
        "validate": cmd_validate,
        "expand": cmd_expand,
        "watch": cmd_watch,
    }
    
    command_map[args.command](args)


if __name__ == "__main__":
    main()
