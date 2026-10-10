# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bingli621/align_crystal/branch/main/graph/badge.svg)](https://codecov.io/gh/bingli621/align_crystal)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/
  instrument/   instruments as configurations (no McStas knowledge)
    components.py     the kinds of component, one dataclass each (named after the McStas component: Source_simple, Slit, Single_crystal, Monitor_nD, ...)
    instrument.py     Instrument: the components of an instrument, each recording its placement (any set of components)
    diffractometer.py Diffractometer(Instrument): its components, derivations and defaults
    params.yaml       all default values of the diffractometer
  file_io/      loader.py: load_config / save_config, an Instrument from/to YAML
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

A different instrument is a new subclass of `Instrument` (its components, defaults file and
derivations, like `Diffractometer`), loaded with `load_config(..., cls=MyInstrument)`.

Dependencies point inwards: `file_io`, `mcstas` and `reduction` use `instrument` and `samples`, never the other way round.

## Configuration

`instrument/params.yaml` holds every default of the diffractometer: one section per McStas component
(its parameters) plus `placements` (`at`, `rotated`, `relative` of each component, which each component keeps). Your own YAML
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
from align_crystal.file_io import load_config
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
