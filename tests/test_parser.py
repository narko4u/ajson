"""
AJSON Core Parser Tests
"""

import json
import pytest
from pathlib import Path

from ajson.parser import (
    compile_ajson,
    compile_file,
    strip_comments,
    resolve_triple_quotes,
)

FIXTURES = Path(__file__).parent / "fixtures"


def clean_json(s):
    """Compile then parse to dict."""
    return json.loads(compile_ajson(s))


# ── Comment Stripping ───────────────────────────────────────────────────

class TestStripComments:
    def test_line_comment(self):
        result = strip_comments('{"a": 1 // comment\n}')
        assert result.strip() == '{"a": 1 \n}'

    def test_block_comment(self):
        result = strip_comments('{"a": /* block */ 1}')
        assert "/*" not in result
        assert "*/" not in result

    def test_block_comment_multiline(self):
        result = strip_comments('{"a": /* multi\nline */ 1}')
        assert "/*" not in result

    def test_comments_inside_strings_preserved(self):
        """URLs with // preserved inside JSON string values."""
        result = strip_comments('{"url": "https://example.com/path"}')
        assert "https://" in result

    def test_block_comment_inside_string_preserved(self):
        result = strip_comments('{"val": "/* not a comment */"}')
        assert "/*" in result

    def test_multiple_comments(self):
        result = strip_comments('{\n  // first\n  "a": 1, /* second */\n  "b": 2 // third\n}')
        assert "//" not in result

    def test_empty_input(self):
        assert strip_comments("") == ""


# ── Triple-Quoted Strings ──────────────────────────────────────────────

class TestTripleQuotes:
    def test_simple_triple(self):
        result = resolve_triple_quotes('{"msg": "hello world"}')
        # No triple quotes in input, should pass through
        assert "hello" in result

    def test_multi_line_triple(self):
        raw = '{"msg": """Hello\nWorld"""}'
        result = resolve_triple_quotes(raw)
        # Should be a single-line JSON string with escaped newline
        assert "Hello" in result
        assert "World" in result
        assert "\\n" in result or "\n" not in result

    def test_triple_with_embedded_quotes(self):
        raw = """{"msg": """ + '"""He said "hello" """' + """}"""
        result = resolve_triple_quotes(raw)
        assert "hello" in result.lower()

    def test_triple_json_example(self):
        """JSON snippet inside triple quotes."""
        raw = '{"schema": """{"type": "object"}"""}'
        result = resolve_triple_quotes(raw)
        assert "type" in result


# ── Reference Resolution ───────────────────────────────────────────────

class TestReferences:
    def test_simple_reference(self):
        parsed = clean_json('{"&schema": {"type": "object"}, "data": {"*schema": null}}')
        assert parsed["data"]["type"] == "object"

    def test_multiple_references_same_anchor(self):
        parsed = clean_json(
            '{"&addr": {"street": "123 Main", "city": "Sydney"},'
            ' "billing": {"*addr": null},'
            ' "shipping": {"*addr": null}}'
        )
        assert parsed["billing"] == parsed["shipping"]

    def test_nested_references(self):
        parsed = clean_json(
            '{"&inner": {"value": 42},'
            ' "&outer": {"nested": {"*inner": null}},'
            ' "result": {"*outer": null}}'
        )
        assert parsed["result"]["nested"]["value"] == 42

    def test_undefined_reference(self):
        with pytest.raises((ValueError, KeyError)):
            clean_json('{"data": {"*undefined": null}}')

    def test_anchor_in_array(self):
        parsed = clean_json(
            '{"&item": {"x": 1},'
            ' "list": [{"*item": null}, {"*item": null}]}'
        )
        assert len(parsed["list"]) == 2
        assert parsed["list"][0] == parsed["list"][1]


# ── Canonical JSON ─────────────────────────────────────────────────────

class TestCanonical:
    def test_sorted_keys(self):
        result = compile_ajson('{"z": 1, "a": 2, "m": 3}')
        assert result.index('"a"') < result.index('"m"')
        assert result.index('"m"') < result.index('"z"')

    def test_deterministic_output(self):
        a = compile_ajson('{"b": 1, "a": 2}')
        b = compile_ajson('{"a": 2, "b": 1}')
        assert a == b

    def test_nested_sorted_keys(self):
        result = compile_ajson('{"z": {"z_inner": 1, "a_inner": 2}, "a": 1}')
        parsed = json.loads(result)
        assert list(parsed.keys()) == ["a", "z"]
        assert list(parsed["z"].keys()) == ["a_inner", "z_inner"]

    def test_array_preserved_order(self):
        result = compile_ajson('{"items": [3, 1, 2]}')
        assert json.loads(result)["items"] == [3, 1, 2]


# ── Full Pipeline ──────────────────────────────────────────────────────

class TestFullPipeline:
    def test_contract_template(self):
        fixture = str(FIXTURES / "contract_template.ajson")
        result = compile_file(fixture)
        parsed = json.loads(result)

        # No artifacts
        assert "&terms" not in result
        assert "&party_schema" not in result

        # References resolved
        assert parsed["contract_terms"]["max_retries"] == 3
        assert parsed["contract_terms"]["sla_seconds"] == 60
        assert len(parsed["actions"]) == 1
        assert len(parsed["parties"]) == 2
        assert parsed["aip_version"] == "1.0.0"

    def test_witnessos_receipt(self):
        fixture = str(FIXTURES / "witnessos_receipt.ajson")
        result = compile_file(fixture)
        parsed = json.loads(result)

        # No artifacts
        assert "&capability_schema" not in result

        # Evidence preserved
        assert parsed["evidence"]["sla_met"] is True
        assert parsed["evidence"]["duration_seconds"] == 12.005

        # Deterministic keys
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_roundtrip_equivalence(self):
        src = '{"&schema": {"type": "object"}, "data": {"*schema": null}}'
        assert compile_ajson(src) == compile_ajson(src)

    def test_invalid_input(self):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            compile_ajson("{invalid garbage here")

    def test_circular_reference_handling(self):
        """Deep nesting should be caught."""
        with pytest.raises((ValueError, RecursionError)):
            compile_ajson(
                '{"&a": {"ref": {"*a": null}}, "b": {"*a": null}}'
            )
