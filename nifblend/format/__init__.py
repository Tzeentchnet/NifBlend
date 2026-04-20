"""Schema-derived types and primitives.

Layout:
- `primitives` — hand-written numpy-vectorized binary readers/writers for NIF
  scalar and small-vector types (replaces `new-pyffi/basic.py`).
- `versions` — version packing/comparison helpers (replaces `new-pyffi/versions.py`).
- `base` — `Block` / `Compound` / `ReadContext` base classes consumed by both
  hand-written code and the codegen output under `generated/`.
- `generated/` — output of `python -m tools.codegen`, committed to the repo.
  See `nifblend/schema/UPSTREAM.md` for the source data snapshot.

Phase 2 onward populates `version.py` with `GameProfile`.
"""
