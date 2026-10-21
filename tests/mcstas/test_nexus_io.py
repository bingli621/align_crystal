import h5py

from align_crystal.mcstas.nexus_io import merge_entries


def test_single_run_files_become_one_entry_each_in_their_order(tmp_path):
    files = []
    for omega in (-5, 5):
        files.append(tmp_path / f"run_{omega}.h5")
        with h5py.File(files[-1], "w") as f:
            f.create_group("entry1").attrs["omega"] = omega

    with h5py.File(merge_entries(files, tmp_path / "scan.h5")) as scan:
        assert list(scan) == ["entry1", "entry2"]
        assert [scan[e].attrs["omega"] for e in scan] == [-5, 5]
