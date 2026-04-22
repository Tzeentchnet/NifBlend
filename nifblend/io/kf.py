"""KF (keyframe-animation) file helpers.

A `.kf` file is a standalone NIF whose root block is a
:class:`NiControllerSequence` (Gamebryo 10.0.1.0+; older NetImmerse files
used :class:`NiSequenceStreamHelper` and are out of scope for v1.0).
The file format is otherwise identical to a `.nif` -- header, block
table, footer -- so :func:`nifblend.io.block_table.read_nif` already
decodes it; this module just exposes the convenience predicates and the
sequence iterator the animation bridge (Phase 5 step 19+) and the
:mod:`nifblend.ops.import_kf` operator (step 21) will call.

No bridging happens here; converting a :class:`NiControllerSequence`
into a Blender Action is the job of :mod:`nifblend.bridge.animation_in`.
"""

from __future__ import annotations

from collections.abc import Iterator

from nifblend.format.generated.blocks import NiControllerSequence
from nifblend.io.block_table import BlockTable

__all__ = ["is_kf_file", "iter_controller_sequences", "kf_root_sequences"]


def is_kf_file(table: BlockTable) -> bool:
    """Return ``True`` if ``table``'s footer roots are all controller sequences.

    KF files always declare at least one root and every root is a
    :class:`NiControllerSequence`. A regular `.nif` whose scene graph
    happens to *contain* a sequence (referenced from a
    :class:`NiControllerManager`) will not satisfy this predicate because
    the footer root will be the scene's :class:`NiNode`, not the sequence.
    """
    roots = table.footer.roots
    if not roots:
        return False
    for raw_idx in roots:
        idx = int(raw_idx)
        if idx < 0 or idx >= len(table.blocks):
            return False
        if not isinstance(table.blocks[idx], NiControllerSequence):
            return False
    return True


def kf_root_sequences(table: BlockTable) -> list[NiControllerSequence]:
    """Return the :class:`NiControllerSequence` blocks listed in the footer.

    Raises :class:`ValueError` if ``table`` is not a KF file.
    """
    if not is_kf_file(table):
        raise ValueError("not a KF file: footer roots are not all NiControllerSequence")
    out: list[NiControllerSequence] = []
    for raw_idx in table.footer.roots:
        blk = table.blocks[int(raw_idx)]
        assert isinstance(blk, NiControllerSequence)  # guaranteed by is_kf_file
        out.append(blk)
    return out


def iter_controller_sequences(table: BlockTable) -> Iterator[NiControllerSequence]:
    """Yield every :class:`NiControllerSequence` block in ``table`` in order.

    Unlike :func:`kf_root_sequences` this also surfaces sequences that are
    referenced indirectly (e.g. from a :class:`NiControllerManager`) and
    works on regular `.nif` files, not just KF files.
    """
    for blk in table.blocks:
        if isinstance(blk, NiControllerSequence):
            yield blk
