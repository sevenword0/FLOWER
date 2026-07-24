"""Gate G5: same preset + same seed -> byte-identical resolved preset and mesh
(결정적 재생). Different seed -> bounded individual variation."""
from biogen.preset_compiler import compile_preset
from biogen.geometry import build_mesh


def test_compile_is_deterministic():
    a = compile_preset("oncorhynchus_mykiss", seed=42)
    b = compile_preset("oncorhynchus_mykiss", seed=42)
    assert a["provenance"]["build_hash"] == b["provenance"]["build_hash"]


def test_mesh_is_deterministic():
    r = compile_preset("clupea_harengus", seed=7)
    m1 = build_mesh(r, lod=0).to_obj()
    m2 = build_mesh(r, lod=0).to_obj()
    assert m1 == m2


def test_individual_seed_varies_but_bounded():
    base = compile_preset("oncorhynchus_mykiss")  # no seed -> nominal
    L0 = base["morphometrics"]["reference_length_m"]
    lengths = []
    for s in range(20):
        r = compile_preset("oncorhynchus_mykiss", seed=s)
        lengths.append(r["morphometrics"]["reference_length_m"])
    # variation exists
    assert len(set(lengths)) > 1
    # but stays within the +/-15% bound of the nominal length
    assert all(0.85 * L0 <= x <= 1.15 * L0 for x in lengths)


def test_lod_reduces_geometry():
    r = compile_preset("oncorhynchus_mykiss", seed=1)
    v0 = len(build_mesh(r, lod=0).vertices)
    v3 = len(build_mesh(r, lod=3).vertices)
    assert v3 < v0
