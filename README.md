# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/   the library (installed)
  instrument/       the entities: the diffractometer is a set of components (no files, no McStas)
    components/       the components, one dataclass each, named after the McStas component
                      (misc.py: Component, Progress_bar, Slit, Arm; source.py: Source_simple;
                       detector.py: Monitor, Monitor_nD; sample.py: Single_crystal, aluminum, la2ni7)
    params.py         InstrParam, CtrlParam: one instrument / control parameter
    cif/              a plain folder: La2Ni7.cif (ready-made crystals: aluminum(), la2ni7() in components/sample.py)
    model/            this instrument, the single-crystal diffractometer
      diffractometer.py SingleCrystalDiffractometer(ctrl_params=()): makes its own components, each
                        recording where it sits, from a list of CtrlParam (the crystal, the energy);
                        the source focus distance follows from the component it focuses on
  io/           files of the instrument (an adapter around the entities)
    dict_io.py        to_dict, from_dict: the diffractometer to and from its nested dict; over_default
    yaml_io.py        the only module that knows YAML: yaml_loader, write_yaml, load(file, ctrl_params)
    params.yaml       the default diffractometer saved; it names the components in beam order
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from the diffractometer (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script); `config` is the diffractometer
    h5_reader.py      read_scan: the NeXus output via mcstastox
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

Dependencies point inwards (clean architecture): `instrument` holds the entities and imports nothing
from the outer layers (a test checks it). Around it are adapters: `io` converts the diffractometer
to and from its nested dict and YAML files, `mcstas` simulates a `SingleCrystalDiffractometer` that the caller creates;
the sample is the diffractometer's `crystal` (a `Single_crystal`, optional); `reduction` reads the McStas output with `mcstas.h5_reader`.

## Configuration

The diffractometer makes itself in code, `SingleCrystalDiffractometer()` (`instrument/model/diffractometer.py`): the
components in the order of the beam, with their values. Its components are plain attributes
(`d.slit.xwidth = 0.02`); what follows from them (the source's focus distance, the crystal's
reciprocal vectors) is computed when used, and `d.validate()` checks the whole again (the McStas builder does).

A parameters file is laid over the default one with `load(file, ctrl_params)`
(`io/yaml_io.py`), so it need hold only what differs: a value it gives wins, one it
leaves out, or sets to `null`, stays as made. Its layout is that of
`src/align_crystal/io/params.yaml`, the default diffractometer saved (a test keeps them equal): `instr_params` (the instrument
parameters, see below) and one section per component name: its `component` (the McStas component),
its parameters, and last where it sits (`at`, `rotated`, `relative`). Save your own with
`write_yaml(to_dict(d), "copy.yaml")`, edit it, and load it with `load("copy.yaml")`.
Unknown keys, and values missing from both, are errors.

The parameters are one nested dict (`io/dict_io.py`). A value left `null` is computed when used, not
saved: the source's focus distance `dist` is the position of the component it focuses on (`focus_on`).
Components never see the file.

The instrument parameters (a list of `InstrParam`) are the McStas instrument parameters. The diffractometer
declares them without values: the wavelength is calculated from `ei`, the goniometer angles are given
by each run (later: by a strategy). The components are general: the file declares them in its
`instr_params` section (`value`, `unit`, `comment`; a null value must be given by every run), and where a component takes a
number it names an instrument parameter instead (or an expression of them), as in McStas: the diffractometer's
goniometer arms have `rotated: [0, omega, 0]` etc. A name that is not an instrument parameter is an error.
`diffractometer.instrument_param(omega=30, chi=0, phi=0)` gives them all, with the values a run sets in
place of the declared ones; `complete_values(...)` gives their values by name, and raises on one still unset.

The control parameters (a list of `CtrlParam`) are given when the instrument is made: the sample
`crystal` and the incident energy `ei` (meV),
`SingleCrystalDiffractometer([CtrlParam("crystal", crystal), CtrlParam("ei", 14, "meV")])`; one left
out is None, an unknown name is an error. The energy is kept in the source (`source.ei`). The source converts
it to a wavelength (`source.wavelength`), which is the instrument parameter `wavelength` McStas gets
(`lambda0`), unless a run sets it. Every McStas run records its wavelength and angles, and the
reduction reads them from the scan (`find_peaks(folder)`); give `find_peaks(folder, wavelength(14))`
for older scans that do not store it.

```yaml
# my_params.yaml: only what differs from the default diffractometer, for example
source:
  radius: 0.02
detector:
  n_theta: 600
slit:
  at: [0, 0, 1.2]
```

```python
from align_crystal.mcstas.simulater import run
from align_crystal.instrument import CtrlParam, SingleCrystalDiffractometer
from align_crystal.io import load

# config: the diffractometer to simulate, the default one with the file laid over it
h5 = run(
    config=load("my_params.yaml", [CtrlParam("ei", 14, "meV")]),
    omega="-48,73",
    chi=0,
    phi=0,
    custom_flags="-N 122",
)  # scan omega

# a sample: the crystal of the diffractometer (none by default)
from align_crystal.instrument import la2ni7

h5 = run(
    config=SingleCrystalDiffractometer(
        [
            CtrlParam("crystal", la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")),
            CtrlParam("ei", 14, "meV"),
        ]
    ),
    omega="-48,73",
    chi=-5.893,
    phi=0,
    custom_flags="-N 122",
)
```

A diffractometer can be created in these ways:

```python
from align_crystal.instrument import CtrlParam, SingleCrystalDiffractometer, la2ni7
from align_crystal.io import from_dict, load, to_dict, write_yaml, yaml_loader

# the default one, made in code (instrument/model/diffractometer.py)
d = SingleCrystalDiffractometer()
d = SingleCrystalDiffractometer(
    [CtrlParam("crystal", la2ni7(at=[0, 0, 0], relative="gonio_phi")), CtrlParam("ei", 14, "meV")]
)
# with a file laid over it (read with a loader: YAML by default)
d = load("my_params.yaml")
d = load("my_params.yaml", [CtrlParam("ei", 14, "meV")], loader=yaml_loader)
# from a complete dict
d = from_dict(to_dict(d))
# change it, and check it again
d.slit.xwidth = 0.02
d.validate()
# save its parameters
write_yaml(to_dict(d), "copy.yaml")
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
