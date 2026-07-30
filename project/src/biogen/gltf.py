"""glTF 2.0 export (프롬프트 §12 Lightweight Delivery).

OBJ carries geometry only, so the rig and material had to travel as separate
JSON files that no DCC or engine reads automatically. glTF carries mesh, skin
skeleton and PBR material in one file that Blender, Houdini, Unreal, Unity,
Godot and three.js all import directly.

Writes `.gltf` + a single `.bin` buffer (readable, diffable) and `.glb`
(single-file, what runtimes usually want). Stdlib only — the format is
assembled by hand rather than pulling in a dependency.

Skinning note: the spine joints are exported as a real glTF skin, with vertex
weights assigned along the body axis, so a consumer can drive the swimming
deformation with the same joint chain the runtime uses. Fin membranes bind
rigidly to their nearest spine joint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import base64
import json
import struct

import numpy as np

from . import paths
from .geometry import build_mesh, build_skeleton, build_material
from .preset_compiler import get_param

# glTF component / accessor constants
FLOAT, USHORT, UBYTE = 5126, 5123, 5121
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def _triangulate(mesh) -> np.ndarray:
    tris: List[Tuple[int, int, int]] = []
    for f in mesh.faces:
        idx = [i - 1 for i in f]
        for k in range(1, len(idx) - 1):
            tris.append((idx[0], idx[k], idx[k + 1]))
    return np.asarray(tris, dtype=np.uint16)


def _vertex_normals(verts: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals. glTF has no 'compute this for me'."""
    n = np.zeros_like(verts)
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    for i in range(3):
        np.add.at(n, tris[:, i], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return np.divide(n, np.where(ln < 1e-12, 1.0, ln))


def _skin_weights(verts: np.ndarray, joint_x: np.ndarray
                  ) -> Tuple[np.ndarray, np.ndarray]:
    """Bind each vertex to the two nearest spine joints along the body axis,
    linearly blended. That is exactly the traveling-wave deformation the
    runtime applies, expressed as a skin so other tools reproduce it."""
    nv = len(verts)
    joints = np.zeros((nv, 4), dtype=np.uint8)
    weights = np.zeros((nv, 4), dtype=np.float32)
    nj = len(joint_x)
    for i, v in enumerate(verts):
        x = v[0]
        k = int(np.searchsorted(joint_x, x))
        lo = max(0, min(k - 1, nj - 1))
        hi = max(0, min(k, nj - 1))
        if lo == hi:
            joints[i] = (lo, 0, 0, 0)
            weights[i] = (1.0, 0.0, 0.0, 0.0)
        else:
            span = joint_x[hi] - joint_x[lo]
            t = 0.0 if span < 1e-12 else float((x - joint_x[lo]) / span)
            t = min(max(t, 0.0), 1.0)
            joints[i] = (lo, hi, 0, 0)
            weights[i] = (1.0 - t, t, 0.0, 0.0)
    return joints, weights


class _Buf:
    """Accumulates binary blobs and hands back bufferView indices."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.views: List[dict] = []

    def add(self, arr: np.ndarray, target: int | None = None) -> int:
        while len(self.data) % 4:            # glTF requires 4-byte alignment
            self.data.append(0)
        off = len(self.data)
        self.data.extend(arr.tobytes())
        view: Dict[str, Any] = {"buffer": 0, "byteOffset": off,
                                "byteLength": arr.nbytes}
        if target is not None:
            view["target"] = target
        self.views.append(view)
        return len(self.views) - 1


def build_gltf(resolved: dict, taxon_id: str, lod: int = 0) -> Tuple[dict, bytes]:
    mesh = build_mesh(resolved, lod=lod)
    skel = build_skeleton(resolved)
    mat = build_material(resolved)

    verts = np.asarray(mesh.vertices, dtype=np.float32)
    tris = _triangulate(mesh)
    norms = _vertex_normals(verts, tris.astype(np.int32)).astype(np.float32)

    spine = skel["spine"]
    joint_x = np.array([j["position_m"][0] for j in spine], dtype=np.float32)
    joints, weights = _skin_weights(verts, joint_x)

    buf = _Buf()
    v_view = buf.add(verts, ARRAY_BUFFER)
    n_view = buf.add(norms, ARRAY_BUFFER)
    j_view = buf.add(joints, ARRAY_BUFFER)
    w_view = buf.add(weights, ARRAY_BUFFER)
    i_view = buf.add(tris.reshape(-1), ELEMENT_ARRAY_BUFFER)

    # inverse bind matrices: joints are translations along the body axis
    ibm = np.zeros((len(spine), 16), dtype=np.float32)
    for i, j in enumerate(spine):
        m = np.eye(4, dtype=np.float32)
        m[0, 3], m[1, 3], m[2, 3] = (-j["position_m"][0], -j["position_m"][1],
                                     -j["position_m"][2])
        ibm[i] = m.T.reshape(-1)          # glTF matrices are column-major
    ibm_view = buf.add(ibm.reshape(-1))

    accessors = [
        {"bufferView": v_view, "componentType": FLOAT, "count": len(verts),
         "type": "VEC3", "min": verts.min(axis=0).tolist(),
         "max": verts.max(axis=0).tolist()},
        {"bufferView": n_view, "componentType": FLOAT, "count": len(norms),
         "type": "VEC3"},
        {"bufferView": j_view, "componentType": UBYTE, "count": len(joints),
         "type": "VEC4"},
        {"bufferView": w_view, "componentType": FLOAT, "count": len(weights),
         "type": "VEC4"},
        {"bufferView": i_view, "componentType": USHORT, "count": tris.size,
         "type": "SCALAR"},
        {"bufferView": ibm_view, "componentType": FLOAT, "count": len(spine),
         "type": "MAT4"},
    ]

    base = list(mat.get("base_color", [0.5, 0.5, 0.55]))[:3] + [1.0]
    material = {
        "name": f"{taxon_id}_runtime_approx",
        "pbrMetallicRoughness": {
            "baseColorFactor": [float(c) for c in base],
            "metallicFactor": 0.0,
            "roughnessFactor": float(mat.get("roughness", 0.35)),
        },
        "doubleSided": True,               # fin membranes are single-surface
        "extras": {
            # provenance travels with the asset: colours here are runtime
            # approximations, not measured spectra (see evidence ledger)
            "evidence_class": mat.get("evidence_class", "runtime_approximation"),
            "iridescence": mat.get("iridescence", 0.0),
            "subsurface": mat.get("subsurface", 0.0),
        },
    }

    # node 0 is the mesh; spine joints follow as a parented chain
    nodes: List[dict] = [{"name": taxon_id, "mesh": 0, "skin": 0}]
    for i, j in enumerate(spine):
        prev = spine[i - 1]["position_m"] if i > 0 else [0.0, 0.0, 0.0]
        nodes.append({
            "name": j["joint_id"],
            "translation": [j["position_m"][k] - prev[k] for k in range(3)],
            **({"children": [i + 2]} if i + 1 < len(spine) else {}),
        })

    gltf = {
        "asset": {"version": "2.0", "generator": "biogen procedural pipeline",
                  "extras": {"taxon_id": taxon_id, "lod": lod,
                             "build_hash": resolved.get("provenance", {}).get("build_hash"),
                             "swim_mode": get_param(resolved, "locomotion.swim_mode"),
                             "rig_strategy": skel.get("rig_strategy")}},
        "scene": 0,
        "scenes": [{"nodes": [0, 1]}],
        "nodes": nodes,
        "meshes": [{"name": taxon_id, "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "JOINTS_0": 2, "WEIGHTS_0": 3},
            "indices": 4, "material": 0, "mode": 4}]}],
        "skins": [{"inverseBindMatrices": 5,
                   "joints": list(range(1, len(spine) + 1)),
                   "skeleton": 1}],
        "materials": [material],
        "accessors": accessors,
        "bufferViews": buf.views,
        "buffers": [{"byteLength": len(buf.data)}],
    }
    return gltf, bytes(buf.data)


def write_gltf(resolved: dict, taxon_id: str, lod: int = 0) -> Dict[str, str]:
    """Write `<taxon>.gltf` + `.bin` and a self-contained `.glb`."""
    gltf, blob = build_gltf(resolved, taxon_id, lod)
    out = paths.ensure_dir(paths.EXPORTS / taxon_id)

    # .gltf + external .bin
    g = json.loads(json.dumps(gltf))
    g["buffers"][0]["uri"] = f"{taxon_id}_lod{lod}.bin"
    (out / f"{taxon_id}_lod{lod}.bin").write_bytes(blob)
    (out / f"{taxon_id}_lod{lod}.gltf").write_text(
        json.dumps(g, indent=1), encoding="utf-8")

    # .glb — JSON chunk + BIN chunk, each padded to 4 bytes
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    bn = blob + b"\0" * ((4 - len(blob) % 4) % 4)
    glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bn))
           + struct.pack("<II", len(js), 0x4E4F534A) + js
           + struct.pack("<II", len(bn), 0x004E4942) + bn)
    (out / f"{taxon_id}_lod{lod}.glb").write_bytes(glb)

    return {"gltf": str(out / f"{taxon_id}_lod{lod}.gltf"),
            "bin": str(out / f"{taxon_id}_lod{lod}.bin"),
            "glb": str(out / f"{taxon_id}_lod{lod}.glb")}
