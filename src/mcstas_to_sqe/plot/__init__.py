"""Pictures of any :class:`.Instrument`.

An adapter around the entities of core/, which imports nothing from here.
"""

from .top_view import SHAPES, rotation_axes, top_view_svg

__all__ = ["SHAPES", "rotation_axes", "top_view_svg"]
