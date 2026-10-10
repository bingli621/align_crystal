"""Reading and writing an Instrument as YAML (the entities in instrument/ know nothing of files)."""

from align_crystal.file_io.loader import load_config, save_config

__all__ = ["load_config", "save_config"]
