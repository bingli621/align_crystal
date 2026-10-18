"""Where the components are: their positions and orientations in the lab frame, as McStas places them.

A component sits at `at` (m) in the frame of the component named `relative` (None: the lab frame),
rotated by `rotated` (deg: about x, then y, then z) relative to that one, as McStas AT and ROTATED
with RELATIVE. A value may be the name of an instrument parameter, or minus one ("-chi"): `values`
gives them. A rotation is McStas's (`rot_set_rotation` in mccode-r.c): the matrix from the lab frame
to the component's own frame.
"""

import numpy as np


def rotation(rx, ry, rz) -> np.ndarray:
    """The McStas rotation matrix of ROTATED (rx, ry, rz), deg: lab frame -> the rotated frame."""
    cx, cy, cz = np.cos(np.radians([rx, ry, rz]))
    sx, sy, sz = np.sin(np.radians([rx, ry, rz]))
    return np.array(
        [
            [cy * cz, sx * sy * cz + cx * sz, sx * sz - cx * sy * cz],
            [-cy * sz, cx * cz - sx * sy * sz, sx * cz + cx * sy * sz],
            [sy, -sx * cy, cx * cy],
        ]
    )


def _number(value, values: dict) -> float:
    """`value`: a number, the name of an instrument parameter, or minus one ("-chi")."""
    if isinstance(value, str):
        sign, name = (-1, value[1:]) if value.startswith("-") else (1, value)
        return sign * values[name]
    return value


def place(components: dict, values: dict) -> dict:
    """The (position, rotation) of each component (by name) in the lab frame: position in m,
    rotation lab -> its frame. `components` are in order (one placed `relative` to another comes
    after it); `values` are the instrument parameters by name."""
    placed = {}
    for name, c in components.items():
        parent_pos, parent_rot = placed[c.relative] if c.relative else (np.zeros(3), np.eye(3))
        at = np.array([_number(v, values) for v in c.at], float)
        rot = rotation(*(_number(v, values) for v in c.rotated)) @ parent_rot
        placed[name] = (parent_pos + parent_rot.T @ at, rot)
    return placed
