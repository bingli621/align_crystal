"""Top view of any instrument, as SVG.

The view is from above (+y), at the instrument's current angles, with the beam (+z) to the right
and +x (left of the beam) up.

- Each component is drawn by its type (``SHAPES``: a tick, a dot, an arc, or nothing) and
  labelled with its name. A type not in ``SHAPES`` is drawn as a dot.
- The rotation axes come from the instrument itself (:func:`rotation_axes`). Every component
  whose ``rotated`` names an instrument parameter turns about that axis. The axes are numbered
  in beam order (outermost first), each drawn with the sense in which a positive angle turns it
  (right-handed about the axis).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from mcstas_to_sqe.core.base import Instrument
from mcstas_to_sqe.core.components import (
    Arm,
    Monitor,
    Monitor_nD,
    Progress_bar,
    Single_crystal,
    Slit,
    Source_simple,
)
from mcstas_to_sqe.core.geometry import place_absolute

# a component's shapes, each (kind, lab points); `lab` maps a point of its frame to the lab frame
Lab = Callable[..., np.ndarray]
Shapes = list[tuple[str, list[np.ndarray]]]

# the symbol an angle is labelled with, by its instrument parameter (else its name)
SYMBOLS = {
    "omega": "ω",
    "chi": "χ",
    "phi": "φ",
    "theta": "θ",
    "psi": "ψ",
    "kappa": "κ",
    "gamma": "γ",
}


def _nothing(c: Any, lab: Lab) -> Shapes:
    return []


def _tick(c: Any, lab: Lab) -> Shapes:
    return [("tick", [lab()])]


def _dot(c: Any, lab: Lab) -> Shapes:
    return [("dot", [lab()])]


def _monitor_nd(c: Monitor_nD, lab: Lab) -> Shapes:
    """Draw a banana detector as its arc, any other ``Monitor_nD`` as a tick.

    theta is signed: negative is right of the beam (-x).
    """
    if "banana" not in c.options:
        return _tick(c, lab)
    theta = np.radians(np.linspace(*c.theta_limits, 121))
    return [("curve", [lab((c.radius * np.sin(t), 0, c.radius * np.cos(t))) for t in theta])]


# how each type of component is drawn: a function of the component and `lab` (the lab point of a
# point of its frame) giving its shapes, each (kind, lab points); a type not here: a dot
SHAPES = {
    Arm: _nothing,
    Progress_bar: _nothing,
    Source_simple: _tick,
    Slit: _tick,
    Monitor: _tick,
    Monitor_nD: _monitor_nd,
    Single_crystal: _dot,
}


def rotation_axes(instrument: Instrument) -> list[tuple[str, str, np.ndarray]]:
    """Find the rotation axes of an instrument, in beam order (outermost first).

    Every ``rotated`` entry that is an instrument parameter gives an axis: its place in
    ``rotated`` gives x, y or z, and a leading ``-`` the sign (``"omega"``: +, ``"-chi"``: -).
    Any other expression has no single axis and sign, and is left out. When a component turns
    about more than one axis, each is taken in the component's frame, which is exact only for
    one.

    Parameters
    ----------
    instrument:
        The instrument.

    Returns
    -------
    :
        ``(component name, instrument parameter, axis)`` for each axis, with the unit axis
        (signed) in the component's own frame.
    """
    names = {p.name for p in instrument.instr_params}
    axes = []
    for name, c in instrument.components.items():
        for k, entry in enumerate(c.rotated):
            if not isinstance(entry, str):
                continue
            entry = entry.strip()
            sign = -1 if entry.startswith("-") else 1
            param = entry.removeprefix("-").strip()
            if param in names:
                axes.append((name, param, sign * np.eye(3)[k]))
    return axes


def top_view_svg(instrument: Instrument, path: str | Path | None = None) -> str:
    """Draw an instrument seen from above (+y), at its current angles, as SVG.

    The beam (+z) runs to the right and +x up. Components are drawn by ``SHAPES`` and labelled,
    with the beam as a line through them in order. The rotation axes (:func:`rotation_axes`)
    are numbered outermost first, each at its component:

    - an axis in the horizontal plane as an arrow, with a curved arrow showing how the top (+y)
      of the sample turns;
    - a vertical axis as a circular arrow, showing how it turns seen from above.

    Parameters
    ----------
    instrument:
        The instrument.
    path:
        File to save the SVG to. If ``None``, it is not saved.

    Returns
    -------
    :
        The SVG text.
    """
    from matplotlib.colors import to_hex  # only when drawn: importing does not need it

    instr_param_dict = {p.name: p.value for p in instrument.instr_params}
    placed = place_absolute(instrument.components, instr_param_dict)  # name -> (position, rotation)

    def frame(name: str) -> Lab:
        def lab(local: Any = (0.0, 0.0, 0.0)) -> np.ndarray:
            """Map the point ``local`` (m) of the frame of ``name`` to the lab frame."""
            position, rotation = placed[name]
            return position + rotation.T @ np.asarray(local, float)

        return lab

    shapes = {
        name: SHAPES.get(type(c), _dot)(c, frame(name)) for name, c in instrument.components.items()
    }
    beam_points = [frame(name)() for name, s in shapes.items() if s]  # the drawn ones, in order

    # the frame: a lab point (x, y, z) is drawn at (z, -x), in pixels (SVG y is down)
    scale = 300  # px per m
    points = np.array(
        [p for s in shapes.values() for _, ps in s for p in ps]
        + [position for position, _ in placed.values()]
    )
    margin, top = 120, 50  # px: room for the rotation axes around its edges, the title on top
    z0, x1 = points[:, 2].min(), points[:, 0].max()
    width = (points[:, 2].max() - z0) * scale + 2 * margin
    height = (x1 - points[:, 0].min()) * scale + 2 * margin + top

    def px(point: np.ndarray) -> np.ndarray:
        return np.array([(point[2] - z0) * scale + margin, (x1 - point[0]) * scale + margin + top])

    def xy(p: np.ndarray) -> str:
        return f"{p[0]:.1f},{p[1]:.1f}"

    def line(a: np.ndarray, b: np.ndarray, colour: str, w: float = 2, head: bool = False) -> str:
        end = ' marker-end="url(#head)"' if head else ""
        return (
            f'<path d="M{xy(a)} L{xy(b)}" fill="none" stroke="{colour}" stroke-width="{w}"{end}/>'
        )

    def text(p: Any, s: str, anchor: str = "middle", colour: str = "black") -> str:
        return (
            f'<text x="{p[0]:.1f}" y="{p[1]:.1f}" text-anchor="{anchor}" fill="{colour}">{s}</text>'
        )

    # matplotlib's default colours
    axis_colour, beam, curve, dot, tick = map(to_hex, ("C0", "C1", "C2", "C4", "C7"))
    axes = rotation_axes(instrument)
    params = ", ".join(f"{p.name} {p.value:g} {p.unit}" for p in instrument.instr_params)
    order = ", ".join(
        f"{i} {SYMBOLS.get(param, param)} ({name})" for i, (name, param, _) in enumerate(axes, 1)
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        + 'font-family="sans-serif" font-size="13">',
        '<defs><marker id="head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
        + f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{axis_colour}"/>'
        + "</marker></defs>",
        '<rect width="100%" height="100%" fill="white"/>',
        text((10, 20), f"{instrument.name}: {params}; top view, beam to the right, +x up", "start"),
        text((10, 38), f"rotation axes, outermost first: {order or 'none'}", "start"),
        f'<polyline points="{" ".join(xy(px(p)) for p in beam_points)}" fill="none" '
        + f'stroke="{beam}" stroke-width="1"/>',
    ]
    for name, s in shapes.items():
        for kind, ps in s:
            p = px(ps[0])
            if kind == "tick":  # its label above and to the left (clear of the rotation axes)
                svg += [line(p - (0, 8), p + (0, 8), tick, 3), text(p - (2, 24), name, "end")]
            elif kind == "curve":  # its label below its middle
                svg += [
                    f'<polyline points="{" ".join(xy(px(q)) for q in ps)}" fill="none" '
                    + f'stroke="{curve}" stroke-width="4"/>',
                    text(px(ps[len(ps) // 2]) + (0, 22), name),
                ]
            else:  # a dot, its label up and to the right (outside the axes circles)
                svg += [
                    f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="5" fill="{dot}"/>',
                    text(p + (36, -40), name, "start"),
                ]

    for i, (name, param, axis) in enumerate(axes):
        centre = px(placed[name][0])
        a = placed[name][1].T @ axis  # the axis in the lab frame
        along = np.array([a[2], -a[0]])  # on the screen: its length, the part in the plane
        label = f"{i + 1} {SYMBOLS.get(param, param)}"
        if np.hypot(*along) < 0.5:  # vertical: a circular arrow, counterclockwise if up
            r, start = 22 + 14 * i, np.radians(-60)  # labels in a row, lower right
            stop = start + np.sign(a[1]) * np.radians(300)
            ends = [centre + r * np.array([np.cos(t), -np.sin(t)]) for t in (start, stop)]
            sweep = 0 if a[1] > 0 else 1
            svg += [
                f'<path d="M{xy(ends[0])} A{r},{r} 0 1 {sweep} {xy(ends[1])}" fill="none" '
                + f'stroke="{axis_colour}" stroke-width="2" marker-end="url(#head)"/>',
                text(ends[0] + 16 * (ends[0] - centre) / r + (0, 5), label, colour=axis_colour),
            ]
        else:  # in the plane: its arrow, and the way the top (+y) turns, a x y
            tip = centre + 80 * along
            turn = np.array([a[0], a[2]]) / np.hypot(a[0], a[2])  # (a x y) on the screen
            bow = along / np.hypot(*along)
            mid = centre + 55 * along
            svg += [
                line(centre, tip, axis_colour, 2, head=True),
                f'<path d="M{xy(mid - 14 * turn)} Q{xy(mid + 14 * bow)} {xy(mid + 14 * turn)}" '
                + f'fill="none" stroke="{axis_colour}" stroke-width="1.5" '
                + 'marker-end="url(#head)"/>',
                text(tip + 18 * bow + (0, 5), label, colour=axis_colour),
            ]
    svg.append("</svg>")
    out = "\n".join(svg)
    if path is not None:
        Path(path).write_text(out, encoding="utf-8")
    return out
