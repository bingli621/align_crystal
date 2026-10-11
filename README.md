# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/   the library (installed)
  core/         the entities: an instrument is a set of components (no file or McStas knowledge)
    components/       the kinds of component, one dataclass each, named after the McStas component
                      (misc.py: Component, Progress_bar, Slit, Arm; source.py: Source_simple;
                       detector.py: Monitor, Monitor_nD; sample.py: Single_crystal)
    instrument.py     Instrument: the components of an instrument, each recording its placement (any set of components)
    params.py         Param: all the parameters of an instrument, as one nested dict (`Instrument.from_dict`)
  yaml_io.py    the only module that knows YAML: yaml_loader (the default loader), write_yaml
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from an Instrument (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script); `config` is the Instrument
    h5_reader.py      read_scan: the NeXus output via mcstastox
  samples/      Sample + one folder per sample (aluminium/, la2ni7/ with its CIF)
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
instruments/    the project's instruments, outside the library: built from core, imported from the repository root
  single_crystal_diffractometer/   a plain folder (no __init__.py), one per instrument
    diffractometer.py  SingleCrystalDiffractometer(Instrument): its own rule for the source focus (its distance
                       follows from the component it focuses on); `from_parameters()` makes the default one
                       directly in code, with `Instrument.from_params(name, origin=origin, ...)`;
                       `from_file(file=None, loader=yaml_loader)` reads a file into one with a loader
    params.yaml        its complete parameters, as the nested dict `from_dict` takes; it names its components
                       in beam order
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

A different instrument is a new parameters file that lists its components (the McStas component of each
role, in order) and their parameters; a component derives its own null values.

Dependencies point inwards: the library never imports `instruments/` (a test checks it); `instruments/` uses
`align_crystal.core`, and `yaml_io` for the default loader of `SingleCrystalDiffractometer.from_file` (any function from a path to
a dict will do). `mcstas` simulates an `Instrument` that the caller creates; `reduction` reads the McStas output
with `mcstas.h5_reader`. The entities take and give plain nested dicts (`Instrument.from_dict`, `to_dict`) and
import nothing from the outer layers. pytest finds `instruments/` through `pythonpath = ["."]` in pyproject.toml.

## Configuration

All the parameters of an instrument are in one complete file: for the diffractometer
`instruments/single_crystal_diffractometer/params.yaml` (outside the library), with `components` (role to McStas component, in beam order), one section
per role plus `placements`
(`at`, `rotated`, `relative` of each component, which each component keeps). To change something,
copy the file, edit it and load the copy (or edit the dict: `from_dict(data)`). Unknown or missing keys are errors.

A value left `null` is calculated by the component itself in its `__post_init__`
(the source derives `wavelength` from `energy_meV`), or, if it depends on other components, by the
instrument in its own `__post_init__` (the source's focus distance `dist` is the position of the
component it focuses on, `focus_on`). Components never see the file.

```yaml
# my_params.yaml: params.yaml with, for example,
source:
  energy_meV: 20
  wavelength: null     # derived: 20 meV
detector:
  n_theta: 600
gonio_chi:
  angle: -5.893
placements:
  slit1: {at: [0, 0, 1.2], rotated: null, relative: source}
```

```python
from align_crystal.mcstas.simulater import run
from instruments import SingleCrystalDiffractometer

# config: the Instrument to simulate
h5 = run(config=SingleCrystalDiffractometer.from_file("my_params.yaml"), omega="-48,73", custom_flags="-N 122")  # scan omega
```

A component can get another McStas instance name with `name: other` in its section.

A diffractometer can be created in these ways:

```python
from instruments import SingleCrystalDiffractometer
from align_crystal.yaml_io import yaml_loader, write_yaml

d = SingleCrystalDiffractometer.from_file("my_params.yaml")   # from a file, read with a loader (YAML by default)
d = SingleCrystalDiffractometer.from_file()                   # the default file, next to the class
d = SingleCrystalDiffractometer.from_file("my_params.yaml", yaml_loader)   # the same, with the loader given explicitly
d = SingleCrystalDiffractometer.from_dict(yaml_loader("my_params.yaml"))    # or in two steps; any dict works
d = SingleCrystalDiffractometer.from_parameters()          # the default one, its components made in code
write_yaml(d.to_dict(), "copy.yaml")                       # save it, to be read back by the first two
```

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
