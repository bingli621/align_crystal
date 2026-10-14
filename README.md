# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/   the library (installed)
  core/         the entities: the diffractometer is a set of components (no McStas knowledge)
    components/       the components, one dataclass each, named after the McStas component
                      (misc.py: Component, Progress_bar, Slit, Arm; source.py: Source_simple;
                       detector.py: Monitor, Monitor_nD; sample.py: Single_crystal, aluminium, la2ni7)
    diffractometer.py SingleCrystalDiffractometer: its components, each recording where it sits, and its
                      rule for the source focus (its distance follows from the component it focuses on)
    cif/              a plain folder: La2Ni7.cif (ready-made crystals: aluminium(), la2ni7() in components/sample.py)
    builder.py        build_diffractometer(crystal=None): the default diffractometer made in code, with
                      the given crystal as its sample (None: aluminium)
    params.py         DesignParam: the design parameters, as one nested dict (`from_dict`); ControlParam
    params.yaml       the complete default parameters; it names the components in beam order
  yaml_io.py    the only module that knows YAML: yaml_loader (the default loader), write_yaml
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from the diffractometer (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script); `config` is the diffractometer
    h5_reader.py      read_scan: the NeXus output via mcstastox
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

Dependencies point inwards: `core` takes and gives plain nested dicts (`from_dict`, `to_dict`) and imports
nothing from the outer layers; only `from_file` loads `yaml_io`, when no other loader (any function from a
path to a dict) is given. `mcstas` simulates a `SingleCrystalDiffractometer` that the caller creates;
the sample is the diffractometer's `crystal` (a `Single_crystal`); `reduction` reads the McStas output with `mcstas.h5_reader`.

## Configuration

All the parameters of the diffractometer are in one complete file,
`src/align_crystal/core/params.yaml`, with its `controls` (the control parameters, see below) and one section per component name, in the order of the
instrument: its `component` (the McStas component), its parameters, and last where it sits (`at`,
`rotated`, `relative`). To change something,
copy the file, edit it and load the copy (or edit the dict: `from_dict(data)`). Unknown or missing keys are errors.

The file (`DesignParam`) holds all the parameters of the instrument. A value left `null` is calculated by the
component itself in its `__post_init__`, or, if it depends on other components, by the diffractometer in
its own `__post_init__` (the source's focus distance `dist` is the position of the component it
focuses on, `focus_on`). Components never see the file.

The control parameters (`ControlParam`) are the McStas instrument parameters, which each run may
set. The components are general: the file declares the controls in its `controls` section (start
`value`, `unit`, `comment`; a null value must be given by every run), and where a component takes a
number it names a control instead (or an expression of them), as in McStas: the diffractometer's
source has `energy_meV: energy_meV`, its goniometer arms `rotated: [0, omega, 0]` etc. A name that is
not a control is an error. `diffractometer.control_param(energy_meV=14, omega=30)` gives them all, with the values
a run sets in place of the start values; `.complete()` raises on one still unset. The reduction reads
the energy from the McStas output and converts it with `reduction.wavelength`.

```yaml
# my_params.yaml: params.yaml with, for example,
source:
  radius: 0.02
detector:
  n_theta: 600
slit:
  at: [0, 0, 1.2]
```

```python
from align_crystal.mcstas.simulater import run
from align_crystal.core import SingleCrystalDiffractometer

# config: the diffractometer to simulate
h5 = run(
    config=SingleCrystalDiffractometer.from_file("my_params.yaml"),
    energy_meV=14,
    omega="-48,73",
    custom_flags="-N 122",
)  # scan omega

# another sample: the crystal of the diffractometer
from align_crystal.core import build_diffractometer, la2ni7

h5 = run(
    config=build_diffractometer(la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")),
    energy_meV=14,
    omega="-48,73",
    custom_flags="-N 122",
)
```

A diffractometer can be created in these ways:

```python
from align_crystal.core import SingleCrystalDiffractometer, build_diffractometer
from align_crystal.yaml_io import yaml_loader, write_yaml

# from a file, read with a loader (YAML by default)
d = SingleCrystalDiffractometer.from_file("my_params.yaml")
# the default file, core/params.yaml
d = SingleCrystalDiffractometer.from_file()
# the same, with the loader given explicitly
d = SingleCrystalDiffractometer.from_file("my_params.yaml", yaml_loader)
# or in two steps; any dict works
d = SingleCrystalDiffractometer.from_dict(yaml_loader("my_params.yaml"))
# the default one, its components made in code (core/builder.py)
d = build_diffractometer()
# save its design parameters, to be read back by the first two
write_yaml(d.to_dict(), "copy.yaml")
```

## Use

```bash
pixi run python src/align_crystal/mcstas/simulater.py   # edit MODE: one run, or beam dump + run from the beam
pixi run python scripts/plot_scan_2d.py                 # output/scan.gif
pixi run python scripts/plot_scan_Q.py                  # output/scan_Q.gif
pixi run python scripts/print_peaks.py                  # peak list of mcstas_output/latest
pixi run pytest --cov=align_crystal --cov-report=term-missing   # tests + coverage
pixi run pre-commit install                             # once: ruff format on every commit
```

Results go to `mcstas_output/` (`latest/`, and `beam/` + `split/` for the split run). A split run
simulates source to sample once (`dump_beam`) and then the crystal for many angles in parallel
(`run_from_beam`), which can be normalized with the beam run's incident monitor.

`mcstastox` is installed from the `entry_choice` branch, which can read individual scan entries.
