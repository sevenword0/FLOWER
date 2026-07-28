"""Shape validation metrics (프롬프트 §15 형상, Gate G4/G5).

The prompt asks for landmark error, silhouette overlap, and cross-section /
volume / proportion error. This module computes them from generated meshes.

**What these numbers can and cannot tell you.** Without digitised reference
specimens, there is no ground truth to score the LOD0 mesh against, so these
metrics are *internal consistency* checks, not accuracy claims:

  * LOD silhouette IoU — does decimation preserve the outline that identifies
    the animal at distance? This is a real, load-bearing check: it is exactly
    the tolerance Gate G8 asks about, and it needs no external reference.
  * Proportion error — does the generated mesh actually realise the depth and
    width ratios the preset asked for? This catches a generator that silently
    ignores its own parameters.
  * Landmark error — same idea, against the preset's own landmark stations.

Scoring against museum specimens or CT-derived landmarks remains open; see
`docs/known_limitations.md`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np

from .geometry import build_mesh
from .preset_compiler import get_param


def _keep(axis: str) -> List[int]:
    drop = {"x": 0, "y": 1, "z": 2}[axis]
    return [i for i in range(3) if i != drop]


def _triangles(mesh) -> np.ndarray:
    """Fan-triangulate the mesh's faces. OBJ faces are 1-indexed and may be
    quads (ring stitches) or triangles (caps and fins)."""
    tris: List[Tuple[int, int, int]] = []
    for f in mesh.faces:
        idx = [i - 1 for i in f]
        for k in range(1, len(idx) - 1):
            tris.append((idx[0], idx[k], idx[k + 1]))
    return np.asarray(tris, dtype=int)


def _body_vertices(mesh) -> np.ndarray:
    """Vertices belonging to the body group only. Fins deliberately extend past
    the body envelope, so proportion checks must exclude them."""
    verts = np.asarray(mesh.vertices, dtype=float)
    body_faces = mesh.groups.get("body", [])
    if not body_faces:
        return verts
    used = set()
    for fi in body_faces:
        for i in mesh.faces[fi]:
            used.add(i - 1)
    return verts[sorted(used)]


def silhouette_mask(mesh, axis: str = "z", res: int = 256,
                    bounds: Tuple[float, float, float, float] | None = None) -> np.ndarray:
    """Rasterise the mesh outline to a boolean mask by projecting along `axis`.

    Triangles are filled with a half-plane test per pixel, which is slow but
    dependency-free and exact enough at these resolutions. The projection is a
    silhouette, so overlapping triangles simply re-fill the same pixels.
    """
    keep = _keep(axis)
    V = np.asarray(mesh.vertices, dtype=float)[:, keep]
    F = _triangles(mesh)

    if bounds is None:
        lo, hi = V.min(axis=0), V.max(axis=0)
        pad = (hi - lo).max() * 0.05 + 1e-6
        bounds = (lo[0] - pad, hi[0] + pad, lo[1] - pad, hi[1] + pad)
    x0, x1, y0, y1 = bounds

    xs = np.linspace(x0, x1, res)
    ys = np.linspace(y0, y1, res)
    px, py = np.meshgrid(xs, ys)
    mask = np.zeros((res, res), dtype=bool)

    for tri in F:
        a, b, c = V[tri[0]], V[tri[1]], V[tri[2]]
        # barycentric sign test, vectorised over the pixel grid
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d
        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
        l3 = 1.0 - l1 - l2
        mask |= (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    return mask


def iou(m1: np.ndarray, m2: np.ndarray) -> float:
    inter = np.logical_and(m1, m2).sum()
    union = np.logical_or(m1, m2).sum()
    return float(inter / union) if union else 1.0


def lod_silhouette_iou(resolved: dict, axis: str = "z", res: int = 220) -> Dict[int, float]:
    """Silhouette IoU of each LOD against LOD0, in a shared frame.

    A shared bounding box matters: rasterising each mesh in its own box would
    normalise away exactly the shrinkage we are trying to detect.
    """
    meshes = [build_mesh(resolved, lod=L) for L in range(4)]
    keep = _keep(axis)
    allv = np.vstack([np.asarray(m.vertices, dtype=float)[:, keep] for m in meshes])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    pad = (hi - lo).max() * 0.05 + 1e-6
    box = (lo[0] - pad, hi[0] + pad, lo[1] - pad, hi[1] + pad)

    ref = silhouette_mask(meshes[0], axis, res, box)
    return {L: iou(ref, silhouette_mask(meshes[L], axis, res, box)) for L in range(4)}


def proportion_error(resolved: dict) -> Dict[str, float]:
    """Relative error between the proportions the preset asked for and what the
    generated LOD0 mesh actually measures.

    Two definitions matter here, and getting either wrong makes the metric lie:

    * **Length is standard length** — measured on the body group only. The
      caudal fin deliberately extends past the body, so including it reports a
      ~9 % length error for a generator that is in fact correct.
    * **Depth and width are measured at the station of maximum girth, about the
      local centreline** — not as a global bounding box. A taxon with a posture
      curve (the seahorse's upright S) has a body whose bbox height spans the
      whole posture; scoring that against `body_depth_ratio` reports >100 %
      error for a mesh that is built exactly to spec.
    """
    m = build_mesh(resolved, lod=0)
    body = _body_vertices(m)
    length = float(body[:, 0].max() - body[:, 0].min())   # standard length

    want_len = float(get_param(resolved, "morphometrics.reference_length_m", 0.0))
    want_depth = float(get_param(resolved, "morphometrics.body_depth_ratio", 0.0))
    want_width = float(get_param(resolved, "morphometrics.body_width_ratio",
                                 want_depth * 0.55))

    # Station of maximum girth. `body_depth_ratio` is defined at girth 1.0, so
    # the measurement is divided by the profile's peak value — a taxon whose
    # profile tops out below 1.0 (the seahorse peaks at 0.7) would otherwise
    # report that shortfall as generator error.
    gp = get_param(resolved, "morphometrics.girth_profile") or [[0.35, 1.0]]
    x_at_max, g_max = max(gp, key=lambda s: s[1])
    g_max = max(float(g_max), 1e-6)
    x0 = float(body[:, 0].min())
    band = body[np.abs(body[:, 0] - (x0 + x_at_max * length)) < length * 0.03]
    if len(band) < 3:
        band = body

    denom = max(length * g_max, 1e-9)
    got_depth = float(band[:, 1].max() - band[:, 1].min()) / denom
    got_width = float(band[:, 2].max() - band[:, 2].min()) / denom

    rel = lambda got, want: abs(got - want) / want if want else 0.0
    return {
        "length_m_measured": length,
        "length_rel_error": rel(length, want_len),
        "depth_ratio_measured": got_depth,
        "depth_rel_error": rel(got_depth, want_depth),
        "width_ratio_measured": got_width,
        "width_rel_error": rel(got_width, want_width),
    }


def landmark_error(resolved: dict) -> Dict[str, float]:
    """Compare the mesh's girth at each profile station against the profile the
    preset specified — i.e. did the loft honour its own control curve?"""
    m = build_mesh(resolved, lod=0)
    body = _body_vertices(m)
    length = float(body[:, 0].max() - body[:, 0].min())   # standard length
    x0 = float(body[:, 0].min())
    depth_ratio = float(get_param(resolved, "morphometrics.body_depth_ratio", 0.2))
    gp = get_param(resolved, "morphometrics.girth_profile") or []

    errs: List[float] = []
    for x_norm, g_want in gp:
        if g_want <= 1e-6:
            continue
        band = body[np.abs(body[:, 0] - (x0 + x_norm * length)) < length * 0.02]
        if len(band) < 3:
            continue
        # local cross-section height about that station's own centre, so a
        # posture curve does not inflate the measurement
        got_h = float(band[:, 1].max() - band[:, 1].min())
        want_h = depth_ratio * length * g_want
        if want_h > 1e-9:
            errs.append(abs(got_h - want_h) / want_h)
    return {"stations": len(errs),
            "mean_rel_error": float(np.mean(errs)) if errs else 0.0,
            "max_rel_error": float(np.max(errs)) if errs else 0.0}


def report(taxon_ids: List[str]) -> Dict[str, dict]:
    from .preset_compiler import compile_preset
    out = {}
    for tid in taxon_ids:
        r = compile_preset(tid, seed=1)
        out[tid] = {
            "lod_silhouette_iou": lod_silhouette_iou(r),
            "proportions": proportion_error(r),
            "landmarks": landmark_error(r),
        }
    return out
