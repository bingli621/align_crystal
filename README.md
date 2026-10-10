# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bingli621/align_crystal/branch/main/graph/badge.svg)](https://codecov.io/gh/bingli621/align_crystal)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/
  instrument/   the instrument as a configuration (no McStas knowledge)
    instrument.py     one dataclass per component, values left null are derived on load
    config_yaml.py    load_config / save_config
    params.yaml       all default values
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from a config (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script)
    h5_reader.py      read_scan: the NeXus output via mcstastox
  samples/      Sample + one folder per sample (aluminium/, la2ni7/ with its CIF)
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

Dependencies point inwards: `mcstas` and `reduction` use `instrument` and `samples`, never the other way round.

## Configuration

`instrument/params.yaml` holds every default: one section per McStas component (`component_name`,
its parameters) plus `placements` (`at`, `rotated`, `relative` of each component). Your own YAML
lists only what changes; unknown keys are rejected, and `null` values are derived (the
wavelength from `energy_meV`, the source focus distance from the sample position).

```yaml
# my_config.yaml
name: my_run
source:
  energy_meV: 20
detector:
  n_theta: 600
gonio_chi:
  angle: -5.893
placements:
  slit1:
    at: [0, 0, 1.2]
```

```python
from align_crystal.instrument import load_config
from align_crystal.mcstas.simulater import run

cfg = load_config("my_config.yaml")                 # also takes a dict of overrides, or nothing
h5 = run(config=cfg, omega="-48,73", custom_flags="-N 122")   # mcrun scan over omega
```

A component can get another McStas instance name with `name: other` in its section.

## Use

```bash
pixi run python src/align_crystal/mcstas/simulater.py   # edit MODE: one run, or beam dump + run from the beam
pixi run python scripts/plot_scan_2d.py                 # output/scan.gif
pixi run python scripts/plot_scan_Q.py                  # output/scan_Q.gif
pixi run python scripts/print_peaks.py                  # peak list of mcstas_output/latest
pixi run pytest --cov=align_crystal --cov-report=term-missing   # tests + coverage
```

Results go to `mcstas_output/` (`latest/`, and `beam/` + `split/` for the split run). A split run
simulates source to sample once (`dump_beam`) and then the crystal for many angles in parallel
(`run_from_beam`), which can be normalized with the beam run's incident monitor.

`mcstastox` is installed from the `entry_choice` branch, which can read individual scan entries.
