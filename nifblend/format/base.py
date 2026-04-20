"""Base classes for hand-written and generated NIF type code.

Generated dataclasses inherit from `Block` (top-level NIF objects, the
`niobject` schema kind) or `Compound` (re-usable structs, the `struct` schema
kind). Both define a `read(stream, ctx)` classmethod and `write(stream, ctx)`
method emitted by the codegen.

`ReadContext` carries the NIF header globals (`Version`, `User Version`,
`BS Header\\BS Version`) plus an arg stack used by fields that pass
parameters into nested compound reads (the `arg=` schema attribute, e.g.
`BSVertexData`'s `Vertex Desc >> 44` flag word).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any

__all__ = ["ReadContext", "Block", "Compound"]


@dataclass(slots=True)
class ReadContext:
    """Per-read state shared with every nested `read` call.

    Attributes mirror the three NIF schema globals (`#VER#`, `#USER#`,
    `#BSVER#`) used in `vercond` / `cond` expressions. Generated code reads
    these directly as `ctx.version`, `ctx.user_version`, `ctx.bs_version`.

    `args` is a stack: the codegen pushes the value of an `arg=` expression
    before calling a nested `read` and pops on return. Nested code reads the
    top of stack as `ctx.arg`.
    """

    version: int = 0
    user_version: int = 0
    bs_version: int = 0
    args: list[Any] = field(default_factory=list)

    @property
    def arg(self) -> Any:
        return self.args[-1] if self.args else 0

    def push_arg(self, value: Any) -> None:
        self.args.append(value)

    def pop_arg(self) -> None:
        self.args.pop()


class Compound:
    """Marker base for `struct`-kind generated dataclasses.

    Generated subclasses define their own `read(cls, stream, ctx)` and
    `write(self, stream, ctx)`. This base intentionally has no body — it
    exists only for `isinstance` checks and to anchor the import graph.
    """

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Compound:
        raise NotImplementedError(f"{cls.__name__} has no generated read()")

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raise NotImplementedError(f"{type(self).__name__} has no generated write()")


class Block(Compound):
    """Marker base for `niobject`-kind generated dataclasses."""
