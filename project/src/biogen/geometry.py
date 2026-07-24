"""Procedural geometry + rig + material generation from a resolved preset.

Method (프롬프트 §9.1–9.3):
  * Loft elliptical cross-sections along a normalized centerline (body-axis
    spline). Cross-section girth comes from the morphotype base `girth_profile`;
    scale from species deltas (depth/width ratios). This is a parametric delta,
    NOT free-form mesh surgery (규칙: 해부학적 제약 델타).
  * Posture (e.g. upright seahorse) applied via a centerline y-offset curve.
  * Fins generated as parametric membranes at recorded fin stations.
  * Rig skeleton = spine joints along the centerline + fin-root joints, matching
    coordinate_system.rig_strategy.
  * LOD reduces ring/segment counts while preserving silhouette.

Outputs plain-text OBJ + JSON (no binary/DCC dependency, per 규칙 §1 최종임무:
바이너리를 만들 수 없으면 재현 스크립트/명세 제공).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import math
import numpy as np

from . import paths
from .preset_compiler import pval, get_param

# LOD ring/segment budgets (§14 변형 최적화).
LOD_BUDGET = {
    0: {"segments": 48, "ring": 24},
    1: {"segments": 32, "ring": 16},
    2: {"segments": 18, "ring": 10},
    3: {"segments": 8, "ring": 6},
}


@dataclass
class MeshData:
    vertices: List[Tuple[float, float, float]]
    faces: List[Tuple[int, ...]]  # 1-indexed OBJ faces
    groups: Dict[str, List[int]]  # face-group name -> face indices

    def to_obj(self, name: str = "creature") -> str:
        lines = [f"# biogen procedural mesh: {name}",
                 f"# vertices={len(self.vertices)} faces={len(self.faces)}",
                 f"o {name}"]
        for v in self.vertices:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        # emit faces grouped
        emitted = set()
        for gname, idxs in self.groups.items():
            lines.append(f"g {gname}")
            for fi in idxs:
                f = self.faces[fi]
                lines.append("f " + " ".join(str(i) for i in f))
                emitted.add(fi)
        # any ungrouped faces
        rest = [i for i in range(len(self.faces)) if i not in emitted]
        if rest:
            lines.append("g misc")
            for fi in rest:
                f = self.faces[fi]
                lines.append("f " + " ".join(str(i) for i in f))
        return "\n".join(lines) + "\n"


def _girth_profile(resolved: dict) -> np.ndarray:
    gp = get_param(resolved, "morphometrics.girth_profile")
    if not gp:
        # default fusiform-ish profile if morphotype lacks one
        gp = [[0.0, 0.02], [0.12, 0.6], [0.35, 1.0], [0.7, 0.55], [0.9, 0.18], [1.0, 0.03]]
    arr = np.array(gp, dtype=float)
    return arr


def _centerline_offset(resolved: dict, xs: np.ndarray) -> np.ndarray:
    """y-offset of the centerline per station (posture). Empty -> straight."""
    curve = get_param(resolved, "morphometrics.centerline_curve")
    if not curve:
        return np.zeros_like(xs)
    c = np.array(curve, dtype=float)
    return np.interp(xs, c[:, 0], c[:, 1])


def build_mesh(resolved: dict, lod: int = 0) -> MeshData:
    budget = LOD_BUDGET.get(lod, LOD_BUDGET[0])
    n_seg = budget["segments"]
    n_ring = budget["ring"]

    L = float(get_param(resolved, "morphometrics.reference_length_m", 0.2))
    depth_ratio = float(get_param(resolved, "morphometrics.body_depth_ratio", 0.2))
    width_ratio = float(get_param(resolved, "morphometrics.body_width_ratio",
                                  0.55 * depth_ratio))

    gp = _girth_profile(resolved)
    xs = np.linspace(0.0, 1.0, n_seg)
    girth = np.interp(xs, gp[:, 0], gp[:, 1])
    y_off = _centerline_offset(resolved, xs)

    ry = 0.5 * depth_ratio * L * girth          # dorsoventral radius
    rz = 0.5 * width_ratio * L * girth          # lateral radius

    verts: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, ...]] = []
    groups: Dict[str, List[int]] = {"body": []}

    ring_start_idx: List[int] = []
    for si, x in enumerate(xs):
        ring_start_idx.append(len(verts))
        cx = x * L
        cy = y_off[si] * L
        if girth[si] <= 1e-6:
            # collapse to a single point (nose/tail cap)
            verts.append((cx, cy, 0.0))
            continue
        for ri in range(n_ring):
            theta = 2.0 * math.pi * ri / n_ring
            vy = cy + ry[si] * math.sin(theta)
            vz = rz[si] * math.cos(theta)
            verts.append((cx, vy, vz))

    # stitch rings
    for si in range(n_seg - 1):
        a0 = ring_start_idx[si]
        b0 = ring_start_idx[si + 1]
        a_is_point = girth[si] <= 1e-6
        b_is_point = girth[si + 1] <= 1e-6
        if a_is_point and not b_is_point:
            for ri in range(n_ring):
                r1 = b0 + ri + 1
                r2 = b0 + (ri + 1) % n_ring + 1
                fi = len(faces)
                faces.append((a0 + 1, r2, r1))
                groups["body"].append(fi)
        elif b_is_point and not a_is_point:
            for ri in range(n_ring):
                r1 = a0 + ri + 1
                r2 = a0 + (ri + 1) % n_ring + 1
                fi = len(faces)
                faces.append((r1, r2, b0 + 1))
                groups["body"].append(fi)
        elif not a_is_point and not b_is_point:
            for ri in range(n_ring):
                a1 = a0 + ri + 1
                a2 = a0 + (ri + 1) % n_ring + 1
                b1 = b0 + ri + 1
                b2 = b0 + (ri + 1) % n_ring + 1
                fi = len(faces)
                faces.append((a1, a2, b2, b1))
                groups["body"].append(fi)

    # fins
    _add_fins(resolved, L, depth_ratio, width_ratio, verts, faces, groups)
    return MeshData(verts, faces, groups)


def _add_fins(resolved, L, depth_ratio, width_ratio, verts, faces, groups):
    fins = get_param(resolved, "external_structures.fins") or []
    for fin in fins:
        name = fin.get("name", "fin")
        x = float(pval(fin.get("x_norm"), 0.5)) * L
        span = float(pval(fin.get("span_norm"), 0.15)) * L
        height = float(pval(fin.get("height_norm"), 0.15)) * L
        kind = fin.get("kind", "median")
        gkey = f"fin_{name}"
        groups.setdefault(gkey, [])
        if kind == "median_dorsal":
            base = len(verts)
            verts += [(x - span / 2, depth_ratio * L * 0.5, 0.0),
                      (x + span / 2, depth_ratio * L * 0.5, 0.0),
                      (x + span / 2, depth_ratio * L * 0.5 + height, 0.0),
                      (x - span / 2, depth_ratio * L * 0.5 + height, 0.0)]
            fi = len(faces)
            faces.append((base + 1, base + 2, base + 3, base + 4))
            groups[gkey].append(fi)
        elif kind == "median_ventral":
            base = len(verts)
            verts += [(x - span / 2, -depth_ratio * L * 0.5, 0.0),
                      (x + span / 2, -depth_ratio * L * 0.5, 0.0),
                      (x + span / 2, -depth_ratio * L * 0.5 - height, 0.0),
                      (x - span / 2, -depth_ratio * L * 0.5 - height, 0.0)]
            fi = len(faces)
            faces.append((base + 1, base + 4, base + 3, base + 2))
            groups[gkey].append(fi)
        elif kind == "caudal":
            base = len(verts)
            verts += [(x, 0.0, 0.0),
                      (x + span, height, 0.0),
                      (x + span, -height, 0.0)]
            fi = len(faces)
            faces.append((base + 1, base + 2, base + 3))
            groups[gkey].append(fi)
        elif kind == "paired":
            zoff = width_ratio * L * 0.5
            for sign in (+1, -1):
                base = len(verts)
                verts += [(x, 0.0, sign * zoff),
                          (x - span, height * 0.5, sign * (zoff + span)),
                          (x - span, -height * 0.5, sign * (zoff + span))]
                fi = len(faces)
                if sign > 0:
                    faces.append((base + 1, base + 2, base + 3))
                else:
                    faces.append((base + 1, base + 3, base + 2))
                groups[gkey].append(fi)


def build_skeleton(resolved: dict, n_joints: int = 8) -> dict:
    """Rig skeleton per coordinate_system.rig_strategy."""
    L = float(get_param(resolved, "morphometrics.reference_length_m", 0.2))
    rig_strategy = get_param(resolved, "coordinate_system.rig_strategy", "spline_spine")
    xs = np.linspace(0.0, 1.0, n_joints)
    y_off = _centerline_offset(resolved, xs)
    spine = []
    for i, x in enumerate(xs):
        spine.append({
            "joint_id": f"spine_{i:02d}",
            "parent": f"spine_{i-1:02d}" if i > 0 else None,
            "position_m": [round(float(x * L), 5), round(float(y_off[i] * L), 5), 0.0],
            "dof": ["bend_z", "bend_y"] if i > 0 else ["root6"],
        })
    fin_joints = []
    for fin in (get_param(resolved, "external_structures.fins") or []):
        x = float(pval(fin.get("x_norm"), 0.5)) * L
        fin_joints.append({
            "joint_id": f"fin_{fin.get('name','fin')}",
            "parent": "spine_%02d" % min(n_joints - 1, int(pval(fin.get("x_norm"), 0.5) * (n_joints - 1))),
            "position_m": [round(x, 5), 0.0, 0.0],
            "dof": ["flex", "abduct"],
        })
    return {
        "rig_strategy": rig_strategy,
        "coordinate_system": resolved.get("coordinate_system", {}),
        "spine": spine,
        "fin_joints": fin_joints,
    }


def build_material(resolved: dict) -> dict:
    """Runtime-approx material (프롬프트 §9.4: 측정/근사 분리)."""
    mat = dict(get_param(resolved, "appearance.material_parameters") or {})
    mat.setdefault("model", "OpenPBR-approx")
    mat.setdefault("base_color", [0.5, 0.5, 0.55])
    mat.setdefault("roughness", 0.35)
    mat.setdefault("iridescence", 0.0)
    mat.setdefault("subsurface", 0.1)
    mat["hue_jitter"] = get_param(resolved, "appearance.hue_jitter", 0.0)
    mat["evidence_class"] = "runtime_approximation"
    return mat


def generate_all(resolved: dict, taxon_id: str, lods=(0, 1, 2, 3)) -> Dict[str, str]:
    """Generate meshes (per LOD), skeleton, material and write to exports/."""
    out_dir = paths.ensure_dir(paths.EXPORTS / taxon_id)
    written: Dict[str, str] = {}
    for lod in lods:
        mesh = build_mesh(resolved, lod=lod)
        p = out_dir / f"mesh_lod{lod}.obj"
        p.write_text(mesh.to_obj(f"{taxon_id}_lod{lod}"), encoding="utf-8")
        written[f"mesh_lod{lod}"] = str(p)
    skel = build_skeleton(resolved)
    (out_dir / "skeleton.json").write_text(json.dumps(skel, indent=2, ensure_ascii=False), encoding="utf-8")
    written["skeleton"] = str(out_dir / "skeleton.json")
    mat = build_material(resolved)
    (out_dir / "material.json").write_text(json.dumps(mat, indent=2, ensure_ascii=False), encoding="utf-8")
    written["material"] = str(out_dir / "material.json")
    return written
