"""Files of the instrument: an adapter around the entities (core/ imports nothing from here).

Any instrument (an `Instrument`): a file names its class (`instrument:`), and io/ builds that one.

dict_io.py   to_dict, from_dict: an instrument to and from its nested dict; from_overrides: the
             default instrument with a dict of only what differs laid over it; merge
yaml_io.py   load(path, **kwargs): a YAML file laid over the default of the instrument it names;
             save(instrument, path); read_yaml, write_yaml
"""

from .dict_io import from_dict, from_overrides, merge, to_dict
from .yaml_io import load, read_yaml, save, write_yaml

__all__ = [
    "from_dict",
    "from_overrides",
    "load",
    "merge",
    "read_yaml",
    "save",
    "to_dict",
    "write_yaml",
]
