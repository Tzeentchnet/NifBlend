"""Per-game bridge helpers (Phase 8d).

Each module in this package holds the **pure** logic for game-specific
utility operators -- shader-flag conversion, partition normalisation,
strip generation. The matching ``ops/games_*.py`` module wraps each
helper in a thin Blender Operator gated on the relevant
:class:`~nifblend.format.versions.GameProfile`.
"""
