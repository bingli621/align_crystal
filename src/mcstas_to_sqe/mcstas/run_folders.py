"""The run folders a `Simulation` writes into.

Each run writes into its own folder in the output folder (`default_output_dir()`), named by
default after the time it started and what it runs, e.g. `20261022-143005_scan_omega`.
`run_folder` picks that folder and clears the way for the run to write it; `list_runs`,
`latest_run` and `latest_beam` find the finished runs, and `clean_runs` removes the older ones
(never a `run_to_sample` one).
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

from mcstas_to_sqe import default_work_dir


def default_output_dir(work_dir=None):
    """The folder of the simulation output (a folder per run), McStasScript's output_path:
    `work_dir/mcstas_output` (None for `default_work_dir()`). Created by each run."""
    return Path(work_dir or default_work_dir()) / "mcstas_output"


def _check_name(folder_name):
    """Check that `folder_name` is a plain folder name: letters, digits, `.`, `_` and `-`,
    starting with a letter or digit.

    A run removes its folder before writing it, so a name like `..`, `/home` or `a/b` must never
    get through: it would remove a folder outside the output folder.

    Raises ValueError if `folder_name` is not a string or not such a name."""
    safe = isinstance(folder_name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", folder_name)
    if not safe:
        raise ValueError(
            f"folder_name {folder_name!r}: one folder name of letters, digits, '.', '_' and '-'"
        )


def _new_name(output_dir, mode):
    """A new run folder name, not yet taken in `output_dir`: the local time now and `mode`,
    e.g. `20261022-143005_scan_omega`.

    A run started in the same second as an earlier one gets `-2`, `-3`, ... appended, e.g.
    `20261022-143005_scan_omega-2`, so it never overwrites the earlier run."""
    name = unique = f"{datetime.now().astimezone():%Y%m%d-%H%M%S}_{mode}"
    n = 1
    while (output_dir / unique).exists():
        n += 1
        unique = f"{name}-{n}"
    return unique


def run_folder(output_dir, folder_name, mode):
    """The folder in `output_dir` a run writes into, `output_dir / folder_name`.

    `folder_name` None gives a new folder named by the time now and `mode` (what the run does,
    e.g. "run", "scan_omega", "run_to_sample"), so each run keeps its own output. A
    `folder_name` given names the folder outright, and a folder of that name from an earlier run
    is removed, so the run replaces it.

    The run folder itself is not created (McStas refuses to write into an existing folder), but
    `output_dir` is, with its parents (McStas does not create them).

    Raises ValueError if `folder_name` is not a plain folder name (see `_check_name`)."""
    if folder_name is None:
        folder_name = _new_name(output_dir, mode)
    _check_name(folder_name)
    path = output_dir / folder_name
    shutil.rmtree(path, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return path


def list_runs(output_dir=None):
    """The names of the finished run folders in `output_dir` (None for `default_output_dir()`),
    the ones with a `mccode.h5`, newest first, e.g.
    `["20261022-143005_scan_omega", "20261022-120000_run_to_sample"]`."""
    output_dir = Path(output_dir or default_output_dir())
    if not output_dir.is_dir():
        return []
    runs = [d for d in output_dir.iterdir() if (d / "mccode.h5").is_file()]
    runs.sort(key=lambda d: (d / "mccode.h5").stat().st_mtime, reverse=True)
    return [run.name for run in runs]


def latest_run(output_dir=None, pattern="*"):
    """The newest finished run folder in `output_dir` (None for `default_output_dir()`) whose
    name matches `pattern`, e.g. "*_scan_omega", "*_run_to_sample", "*_from_sample".

    Raises FileNotFoundError if there is none."""
    output_dir = Path(output_dir or default_output_dir())
    for name in list_runs(output_dir):
        if Path(name).match(pattern):
            return output_dir / name
    raise FileNotFoundError(f"no finished run {pattern!r} in {output_dir}")


def latest_beam(output_dir=None):
    """The newest beam file (`beam.mcpl.gz`, of a `run_to_sample`) of the finished runs in
    `output_dir` (None for `default_output_dir()`), or None if there is none."""
    output_dir = Path(output_dir or default_output_dir())
    beams = [output_dir / run / "beam.mcpl.gz" for run in list_runs(output_dir)]
    return next((beam for beam in beams if beam.is_file()), None)


def clean_runs(output_dir=None, keep=5):
    """Remove all but the `keep` newest finished runs of `output_dir` (None for
    `default_output_dir()`), and return the removed folders.

    Never removed, whatever their age:
    - a `run_to_sample` run (any folder with a `beam.mcpl.gz`, whatever its name): its beam file
      is the expensive simulation every `run_from_sample` and `scan_from_sample` starts from, and
      its `mccode.h5` has the incident monitor that normalizes them. Delete one by hand when it
      is no longer needed;
    - a folder without a `mccode.h5` (an unfinished run, or anything else in `output_dir`).

    `run_to_sample` runs count towards `keep`, so fewer other runs may be kept."""
    output_dir = Path(output_dir or default_output_dir())
    runs = [output_dir / run for run in list_runs(output_dir)]
    old = [run for run in runs[keep:] if not (run / "beam.mcpl.gz").is_file()]
    for run in old:
        shutil.rmtree(run)
    return old
