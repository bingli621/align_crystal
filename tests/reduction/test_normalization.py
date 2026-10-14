"""The reduction of a split run, on a small recorded one (tests/data/make_split_run.py)."""

from pathlib import Path

import mcstastox
import numpy as np
import pytest

from align_crystal.mcstas.h5_reader import numeric_parameters
from align_crystal.reduction import find_peaks, normalize_scan
from align_crystal.reduction.peaks import load_points

DATA = Path(__file__).parents[1] / "data" / "split_run"
SPLIT = DATA / "split"
MONITOR = DATA / "beam" / "mccode.h5"


def test_the_split_run_itself_does_not_store_the_energy():
    """Why the beam run is needed: McStas leaves out the energy when the source is not run."""
    with mcstastox.Read(str(SPLIT), entry_number=1) as data:
        params = numeric_parameters(data.get_instrument_parameters())
    assert "omega" in params and "energy_meV" not in params


def test_a_split_run_takes_the_missing_parameters_from_the_beam_run():
    scan = normalize_scan(SPLIT, monitor_file=MONITOR)
    params = [{k: v.value for k, v in g["parameters"].items()} for g in scan.values()]
    assert [p["energy_meV"] for p in params] == [14.0, 14.0]  # from the beam run
    # the entries' own values win: the beam run had omega 0 and chi 0
    assert [p["omega"] for p in params] == [-5.0, 5.0]
    assert [p["chi"] for p in params] == pytest.approx([-5.893, -5.893])


def test_the_peaks_of_a_split_run_can_be_found():
    points = load_points(SPLIT, monitor_file=MONITOR)
    n = len(points["w"])
    assert n > 0 and points["q"].shape == (n, 3) and np.all(np.isfinite(points["q"]))
    assert set(points["scan"]) == {0, 1}
    assert points["monitor"][0] == points["monitor"][1]  # one beam-run reading for every angle
    assert isinstance(find_peaks(SPLIT, monitor_file=MONITOR), list)
