"""Where the components are: their positions and orientations in the lab frame, as McStas places
them.

A component sits at `at` (m) in the frame of the component named `relative` (None: the lab frame),
rotated by `rotated` (deg: about x, then y, then z) relative to that one, as McStas AT and ROTATED
with RELATIVE. A value may be a McStas expression of instrument parameters ("-chi"; see
`utils.evaluate`): `instr_param_dict` gives them. A rotation is McStas's (`rot_set_rotation` in
mccode-r.c): the matrix from the lab frame to the component's own frame.
"""

import numpy as np

from align_crystal.instrument.utils import evaluate


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


def place_absolute(components: dict, instr_param_dict: dict) -> dict:
    """Each component placed ABSOLUTE: its `at`/`rotated` RELATIVE chain followed back to the lab
    frame, as McStas does. A dict by name of (position, rotation): position in m, rotation the
    matrix lab -> its frame.

    `components` (name -> component) are in order: one placed `relative` to another comes after
    it. `instr_param_dict` (McStas name -> value) gives the instrument parameters that the `at`
    and `rotated` expressions name ("omega", "-chi")."""
    at_rotated_absolute_dict = {}
    for name, c in components.items():
        parent_pos, parent_rot = (
            at_rotated_absolute_dict[c.relative] if c.relative else (np.zeros(3), np.eye(3))
        )
        at = np.array([evaluate(v, instr_param_dict) for v in c.at], float)
        rot = rotation(*(evaluate(v, instr_param_dict) for v in c.rotated)) @ parent_rot
        at_rotated_absolute_dict[name] = (parent_pos + parent_rot.T @ at, rot)
    return at_rotated_absolute_dict
