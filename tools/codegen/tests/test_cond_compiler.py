"""Unit tests for `tools.codegen.cond_compiler`.

These exercise the substitution + tokenizer + emitter pipeline against the
real vendored schema (so that any schema-side surprises surface here, not in
generated runtime code).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tools.codegen.cond_compiler import (
    ExprCompiler,
    compile_version_literal,
    compile_versions_set,
)
from tools.codegen.parser import parse_schema

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "nifblend" / "schema" / "nif.xml"


@pytest.fixture(scope="module")
def schema():  # type: ignore[no-untyped-def]
    return parse_schema(SCHEMA_PATH)


@pytest.fixture(scope="module")
def compiler(schema):  # type: ignore[no-untyped-def]
    return ExprCompiler.for_schema(schema)


def _ident_passthrough(name: str) -> str:
    """Test resolver: emits `self.<lowercase_underscored>`. Mirrors what the
    real emitter does for fields belonging to the containing struct."""
    safe = name.replace("\\", "_").replace(" ", "_").lower()
    return f"self.{safe}"


def _is_valid_python_expr(src: str) -> bool:
    try:
        ast.parse(src, mode="eval")
    except SyntaxError:
        return False
    return True


# ---- tokenizer + simple ops ----------------------------------------------


@pytest.mark.parametrize(
    "src, expected_tokens",
    [
        ("Num Vertices", ["Num Vertices"]),
        ("Num Vertices > 0", ["Num Vertices", ">", "0"]),
        ("(a + b) * c", ["(", "a", "+", "b", ")", "*", "c"]),
        ("Vertex Desc >> 44", ["Vertex Desc", ">>", "44"]),
        (
            "(Has Bounding Volume == 1) && (Num Vertices > 0)",
            ["(", "Has Bounding Volume", "==", "1", ")", "&&", "(", "Num Vertices", ">", "0", ")"],
        ),
        # Float exponents must survive tokenization intact — the `+`/`-` after
        # `e`/`E` is part of the number, not an operator.
        ("x > 3.402823466e+38", ["x", ">", "3.402823466e+38"]),
        ("x > 1.0E-7", ["x", ">", "1.0E-7"]),
        ("x > 5e10", ["x", ">", "5e10"]),
    ],
)
def test_tokenize(src: str, expected_tokens: list[str]) -> None:
    from tools.codegen.cond_compiler import _tokenize

    assert _tokenize(src) == expected_tokens


@pytest.mark.parametrize(
    "operand",
    [
        "1",
        "-1",
        "+1",
        "1.5",
        "-1.5",
        "+1.5",
        "1e10",
        "1e+10",
        "1e-10",
        "+3.402823466e+38",
        "-1.0E-7",
    ],
)
def test_float_and_int_operands_pass_through(operand: str) -> None:
    """Numeric literals (including signed-exponent floats) must round-trip
    through `_emit_operand` unchanged so they remain valid Python literals."""
    from tools.codegen.cond_compiler import _emit_operand

    out = _emit_operand(operand, _ident_passthrough)
    assert out == operand
    assert _is_valid_python_expr(out)


# ---- vercond against real schema ------------------------------------------


def test_vercond_simple_named_token(compiler) -> None:  # type: ignore[no-untyped-def]
    out = compiler.compile_vercond("#BS_GTE_SKY#", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert "ctx.bs_version" in out
    assert ">=" in out
    assert "83" in out


def test_vercond_compound(compiler) -> None:  # type: ignore[no-untyped-def]
    out = compiler.compile_vercond("#BS_GTE_SKY# #AND# #NI_BS_LTE_FO4#", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert " and " in out
    assert "ctx.bs_version" in out


def test_vercond_with_version_literal(compiler) -> None:  # type: ignore[no-untyped-def]
    # `#BS202#` expands to `((#VER# #EQ# 20.2.0.7) #AND# (#BSVER# #GT# 0))`
    out = compiler.compile_vercond("#BS202#", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert "pack_version(20, 2, 0, 7)" in out
    assert "ctx.version" in out


# ---- cond against real schema ---------------------------------------------


def test_cond_simple_field_ref(compiler) -> None:  # type: ignore[no-untyped-def]
    out = compiler.compile_cond("Has Bounding Volume", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert out == "self.has_bounding_volume"


def test_cond_field_arithmetic(compiler) -> None:  # type: ignore[no-untyped-def]
    # `Data Size #GT# 0` → `self.data_size > 0`
    out = compiler.compile_cond("Data Size #GT# 0", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert "self.data_size" in out
    assert ">" in out


def test_cond_with_uint_max_token(compiler) -> None:  # type: ignore[no-untyped-def]
    # `#UINT_MAX#` is a default-attr token, not a cond-attr token, so it
    # should pass through unsubstituted in cond context. Verify the compiler
    # doesn't accidentally mix attribute scopes.
    with pytest.raises(ValueError):
        compiler.compile_cond("Foo == #UINT_MAX#", _ident_passthrough)


# ---- length / arg ---------------------------------------------------------


def test_length_field_ref(compiler) -> None:  # type: ignore[no-untyped-def]
    out = compiler.compile_length("Num Vertices", _ident_passthrough)
    assert out == "self.num_vertices"


def test_arg_bitshift(compiler) -> None:  # type: ignore[no-untyped-def]
    # BSTriShape's vertex_data field uses arg="Vertex Desc #RSH# 44"
    out = compiler.compile_arg("Vertex Desc #RSH# 44", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert "self.vertex_desc" in out
    assert ">>" in out
    assert "44" in out


# ---- version helpers ------------------------------------------------------


def test_compile_version_literal() -> None:
    assert compile_version_literal("20.2.0.7") == "pack_version(20, 2, 0, 7)"
    assert compile_version_literal("3.0") == "pack_version(3, 0)"


def test_compile_versions_set(schema) -> None:  # type: ignore[no-untyped-def]
    out = compile_versions_set("#SSE# #FO4# #F76#", schema)
    assert _is_valid_python_expr(out)
    assert "ctx.version" in out
    assert "ctx.user_version" in out
    assert "ctx.bs_version" in out
    assert " in {" in out


# ---- random spot checks against real BSTriShape fields --------------------


def test_real_bstrishape_vertex_data_vercond(compiler) -> None:  # type: ignore[no-untyped-def]
    # Field: Vertex Data, vercond="#BS_GTE_130#" → ctx.bs_version >= 130
    out = compiler.compile_vercond("#BS_GTE_130#", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert "ctx.bs_version" in out and "130" in out and ">=" in out


def test_real_bstrishape_vertex_data_cond(compiler) -> None:  # type: ignore[no-untyped-def]
    # Field: Vertex Data, cond="Data Size #GT# 0" → self.data_size > 0
    out = compiler.compile_cond("Data Size #GT# 0", _ident_passthrough)
    assert _is_valid_python_expr(out)
    assert out == "self.data_size > 0"
