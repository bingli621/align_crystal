"""Pictures of an instrument (any `Instrument`): an adapter around the entities (core/ imports
nothing from here)."""

from .top_view import SHAPES, rotation_axes, top_view_svg

__all__ = ["SHAPES", "rotation_axes", "top_view_svg"]
