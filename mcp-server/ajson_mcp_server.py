#!/usr/bin/env python3
"""
AJSON MCP Server — Exposes AJSON compilation as MCP tools.

Safe for HTTP hosting: stateless, no secrets, no side effects.
All tools are pure computation — input in, output out.

Tools:
  - ajson_compile     Compile AJSON text to canonical JSON
  - ajson_validate    Validate AJSON text with detailed report
  - ajson_expand      Compile AJSON to pretty-printed expanded JSON

Usage:
  python ajson_mcp_server.py          # stdio mode (for agent configs)
  python ajson_mcp_server.py --http   # HTTP mode (safe for remote use)

Copyright (c) 2026 Empire Labs Pty Ltd
SPDX-License-Identifier: MIT
"""

import argparse
import json
import sys
from typing import Any

import anyio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ErrorData,
)
import mcp.server.stdio


# ── AJSON Bridge ──────────────────────────────────────────────────────

def _import_ajson():
    """Lazy import ajson — works when installed or from source."""
    import ajson.parser
    return ajson.parser


def _compile(text: str, canonical: bool = True) -> str:
    """Compile AJSON text to JSON. Wraps parser exceptions."""
    parser = _import_ajson()
    return parser.compile_ajson(text, canonical=canonical)


def _validate(text: str) -> dict:
    """
    Validate AJSON text. Returns a report dict.
    Never raises — returns structured result.
    """
    parser = _import_ajson()
    try:
        compiled = parser.compile_ajson(text)
        # Verify it round-trips as valid JSON
        parsed = json.loads(compiled)
        result = {
            "valid": True,
            "type": type(parsed).__name__,
            "size_chars": len(compiled),
            "summary": "Valid AJSON — compiles to canonical JSON successfully."
        }
        if isinstance(parsed, dict):
            result["keys"] = list(parsed.keys())
            result["key_count"] = len(parsed)
        elif isinstance(parsed, list):
            result["length"] = len(parsed)
        return result
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "error": str(e),
            "position": e.pos,
            "line": None,
            "summary": f"JSON parse error at position {e.pos}: {e.msg}"
        }
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e),
            "position": None,
            "summary": f"Reference error: {e}"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "position": None,
            "summary": f"Unexpected error: {e}"
        }


# ── MCP Server ────────────────────────────────────────────────────────

app = Server("ajson")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ajson_compile",
            description=(
                "Compile AJSON (Agent JSON) text to canonical deterministic JSON. "
                "AJSON supports: // and /* */ comments, triple-quoted multi-line strings, "
                "&anchor /*reference references, canonical sorted-key output. "
                "Returns compiled JSON as a string."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ajson_text": {
                        "type": "string",
                        "description": "The AJSON source text to compile"
                    },
                    "canonical": {
                        "type": "boolean",
                        "description": "Sort keys deterministically (default: true)",
                        "default": True
                    }
                },
                "required": ["ajson_text"]
            }
        ),
        Tool(
            name="ajson_validate",
            description=(
                "Validate AJSON text and return a detailed report. "
                "Checks syntax, references, and JSON validity. "
                "Never raises — always returns a structured valid/invalid report."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ajson_text": {
                        "type": "string",
                        "description": "The AJSON source text to validate"
                    }
                },
                "required": ["ajson_text"]
            }
        ),
        Tool(
            name="ajson_expand",
            description=(
                "Compile AJSON to pretty-printed expanded JSON. "
                "Same as ajson_compile but with indentation for human readability. "
                "Useful for inspecting the compiled output."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ajson_text": {
                        "type": "string",
                        "description": "The AJSON source text to expand"
                    },
                    "indent": {
                        "type": "integer",
                        "description": "Indentation spaces (default: 2)",
                        "default": 2
                    }
                },
                "required": ["ajson_text"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        if name == "ajson_compile":
            text = arguments["ajson_text"]
            canonical = arguments.get("canonical", True)
            result = _compile(text, canonical=canonical)
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )

        elif name == "ajson_validate":
            text = arguments["ajson_text"]
            report = _validate(text)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(report, indent=2, default=str))]
            )

        elif name == "ajson_expand":
            text = arguments["ajson_text"]
            indent = arguments.get("indent", 2)
            compiled = _compile(text)
            parsed = json.loads(compiled)
            pretty = json.dumps(parsed, indent=indent, ensure_ascii=False)
            return CallToolResult(
                content=[TextContent(type="text", text=pretty)]
            )

        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )

    except json.JSONDecodeError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"JSON error: {e}")],
            isError=True
        )
    except ValueError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"AJSON error: {e}")],
            isError=True
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {e}")],
            isError=True
        )


# ── Entry Points ──────────────────────────────────────────────────────

async def run_stdio():
    """Run MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ajson",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_http(host: str = "0.0.0.0", port: int = 8100):
    """Run MCP server over HTTP (safe for AJSON — no secrets)."""
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from starlette.responses import JSONResponse

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request,
            request.app.state.app,
        ) as streams:
            await app.run(
                streams[0], streams[1],
                InitializationOptions(
                    server_name="ajson",
                    server_version="0.1.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    async def handle_health(request):
        return JSONResponse({
            "status": "ok",
            "server": "ajson-mcp",
            "version": "0.1.0",
            "safe": True,
            "tools": ["ajson_compile", "ajson_validate", "ajson_expand"]
        })

    starlette_app = Starlette(
        routes=[
            Route("/health", handle_health),
            Route("/sse", handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )
    starlette_app.state.app = app

    print(f"🔧 AJSON MCP Server (HTTP mode)")
    print(f"   Health: http://{host}:{port}/health")
    print(f"   SSE:    http://{host}:{port}/sse")
    print(f"   Tools:  compile, validate, expand")
    print(f"   Safe:   ✅ Stateless — no secrets, no keys, no side effects")
    uvicorn.run(starlette_app, host=host, port=port)


def main():
    parser = argparse.ArgumentParser(description="AJSON MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode (default: stdio)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=8100, help="HTTP port")
    args = parser.parse_args()

    if args.http:
        run_http(host=args.host, port=args.port)
    else:
        anyio.run(run_stdio)


if __name__ == "__main__":
    main()
