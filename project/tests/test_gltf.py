"""glTF 2.0 export (프롬프트 §12). Validates structural conformance — a file
that imports is worth more than one that merely exists."""
import json
import struct
import pytest
from biogen.preset_compiler import compile_preset
from biogen.gltf import build_gltf


@pytest.fixture(scope="module")
def asset():
    r = compile_preset("oncorhynchus_mykiss", seed=1)
    return build_gltf(r, "oncorhynchus_mykiss")


def test_core_structure(asset):
    g, blob = asset
    assert g["asset"]["version"] == "2.0"
    assert len(g["meshes"]) == 1 and len(g["materials"]) == 1
    prim = g["meshes"][0]["primitives"][0]
    assert prim["mode"] == 4                      # TRIANGLES
    for attr in ("POSITION", "NORMAL", "JOINTS_0", "WEIGHTS_0"):
        assert attr in prim["attributes"], attr


def test_accessors_fit_inside_their_buffer_views(asset):
    """The commonest way to ship a broken glTF is an accessor that runs past
    its view. Check every one against the declared buffer length."""
    g, blob = asset
    SIZE = {5126: 4, 5123: 2, 5121: 1}
    COMPONENTS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    assert g["buffers"][0]["byteLength"] == len(blob)
    for i, acc in enumerate(g["accessors"]):
        need = acc["count"] * COMPONENTS[acc["type"]] * SIZE[acc["componentType"]]
        view = g["bufferViews"][acc["bufferView"]]
        assert need <= view["byteLength"], f"accessor {i} overruns its view"
        assert view["byteOffset"] + view["byteLength"] <= len(blob)
        assert view["byteOffset"] % 4 == 0, "glTF requires 4-byte alignment"


def test_skin_joints_match_the_rig(asset):
    g, _ = asset
    joints = g["skins"][0]["joints"]
    assert len(joints) >= 4
    # every joint index must name a real node
    assert all(0 <= j < len(g["nodes"]) for j in joints)
    ibm = g["accessors"][g["skins"][0]["inverseBindMatrices"]]
    assert ibm["type"] == "MAT4" and ibm["count"] == len(joints)


def test_skin_weights_are_normalised(asset):
    """Weights that do not sum to 1 make a mesh shrink when skinned."""
    import numpy as np
    g, blob = asset
    prim = g["meshes"][0]["primitives"][0]
    acc = g["accessors"][prim["attributes"]["WEIGHTS_0"]]
    view = g["bufferViews"][acc["bufferView"]]
    w = np.frombuffer(blob, dtype=np.float32, count=acc["count"] * 4,
                      offset=view["byteOffset"]).reshape(-1, 4)
    assert np.allclose(w.sum(axis=1), 1.0, atol=1e-5)


def test_provenance_travels_with_the_asset(asset):
    """A generated asset should carry its build hash, so a mesh found later can
    be traced back to the preset that produced it."""
    g, _ = asset
    extras = g["asset"]["extras"]
    assert extras["taxon_id"] == "oncorhynchus_mykiss"
    assert extras["build_hash"]
    assert g["materials"][0]["extras"]["evidence_class"] == "runtime_approximation"


def test_glb_container_is_well_formed():
    from biogen.gltf import write_gltf
    r = compile_preset("clupea_harengus", seed=1)
    paths = write_gltf(r, "clupea_harengus")
    data = open(paths["glb"], "rb").read()
    magic, ver, total = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67 and ver == 2
    assert total == len(data), "declared GLB length must match the file"
    jlen, jtype = struct.unpack("<II", data[12:20])
    assert jtype == 0x4E4F534A                     # JSON chunk
    json.loads(data[20:20 + jlen].decode("utf-8"))  # must parse
