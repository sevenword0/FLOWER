"""Preset compiler.

Resolves the layered preset hierarchy (프롬프트 §2):

    SpeciesPreset = CladeBase + MorphotypeBase + SpeciesDelta
                    + ContextDelta(population, sex, life_stage, season, condition, size)
                    + IndividualSeed

Reuse of clade/morphotype bases is mandatory; species are stored as deltas
(규칙: 종마다 독립 모델 수작업 금지). Compilation is deterministic given the
same inputs + seed (Gate G5).
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import copy
import hashlib
import json
import numpy as np

from . import paths


def _load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def deep_merge(base: dict, over: dict) -> dict:
    """Recursive merge. dict merges; list/scalar override (규칙: 델타 적용)."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def pval(node: Any, default=None):
    """Extract a scalar from either a bare value or a {value, evidence_class}
    ledger-style object."""
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return node if node is not None else default


def get_param(resolved: dict, dotted: str, default=None):
    """Fetch a nested parameter by dotted path, unwrapping {value:...}."""
    cur: Any = resolved
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return pval(cur, default)


def canonical_hash(obj: dict) -> str:
    """Stable content hash for determinism/provenance (excludes volatile keys)."""
    clone = copy.deepcopy(obj)
    prov = clone.get("provenance", {})
    prov.pop("generated_at", None)
    prov.pop("build_hash", None)
    blob = json.dumps(clone, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _apply_individual_seed(resolved: dict, seed: int) -> dict:
    """Deterministic per-individual variation within recorded distributions
    (프롬프트 §10.7: 결정적 시드 + 확률적 개체차). Bounded, biologically safe."""
    rng = np.random.default_rng(seed)
    morph = resolved.setdefault("morphometrics", {})

    # +/-8% length variation, +/-5% depth ratio, keeping covariance sign.
    length = float(pval(morph.get("reference_length_m"), 0.2) or 0.2)
    depth_ratio = float(pval(morph.get("body_depth_ratio"), 0.2) or 0.2)
    length_var = float(rng.normal(1.0, 0.04))
    length_var = min(max(length_var, 0.85), 1.15)
    depth_var = float(rng.normal(1.0, 0.025))
    depth_var = min(max(depth_var, 0.92), 1.08)

    morph["reference_length_m"] = round(length * length_var, 5)
    morph["body_depth_ratio"] = round(depth_ratio * depth_var, 5)

    # small hue jitter for individual appearance
    appearance = resolved.setdefault("appearance", {})
    appearance["hue_jitter"] = round(float(rng.uniform(-0.03, 0.03)), 4)

    resolved.setdefault("_individual", {})["seed"] = int(seed)
    return resolved


def compile_preset(
    taxon_id: str,
    context: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> dict:
    """Compile a resolved preset for a taxon_id. Deterministic."""
    species_path = paths.PRESETS / taxon_id / "preset.json"
    if not species_path.exists():
        raise FileNotFoundError(f"No species delta preset for taxon_id={taxon_id!r}")
    species = _load_json(species_path)

    ph = species["parameter_hierarchy"]
    clade = _load_json(paths.CLADE_BASES / f"{ph['clade_base_id']}.json")
    morpho = _load_json(paths.MORPHOTYPE_BASES / f"{ph['morphotype_base_id']}.json")

    # Layer order: clade -> morphotype -> species delta.
    resolved = deep_merge(clade, morpho)
    resolved = deep_merge(resolved, species)

    # Context delta (sex/life_stage/season/...) overrides.
    if context:
        ctx_over = {"context": context}
        # sex/size-specific length overrides if present in species deltas
        resolved = deep_merge(resolved, ctx_over)
        _apply_context_scaling(resolved, context)

    resolved["kind"] = "resolved_preset"

    # Individual seed (optional).
    if seed is not None:
        _apply_individual_seed(resolved, seed)

    # Provenance
    prov = resolved.setdefault("provenance", {})
    prov.setdefault("evidence_refs", [])
    prov["build_hash"] = canonical_hash(resolved)
    prov["generated_at"] = "deterministic"  # no wall-clock -> reproducible
    return resolved


def _apply_context_scaling(resolved: dict, context: dict) -> None:
    """Allometric/context scaling (프롬프트 §9.1: 단순 균등 스케일 금지)."""
    morph = resolved.setdefault("morphometrics", {})
    allometry = morph.get("allometry", {})

    # sex-specific reference length (e.g. anglerfish dwarf males)
    sex = context.get("sex")
    sex_lengths = morph.get("reference_length_by_sex")
    if sex and isinstance(sex_lengths, dict) and sex in sex_lengths:
        morph["reference_length_m"] = pval(sex_lengths[sex])

    # life-stage scaling via allometric exponent on body depth
    stage = context.get("life_stage")
    stage_scale = allometry.get("life_stage_depth_scale", {}) if isinstance(allometry, dict) else {}
    if stage and stage in stage_scale:
        base_depth = float(pval(morph.get("body_depth_ratio"), 0.2) or 0.2)
        morph["body_depth_ratio"] = round(base_depth * float(stage_scale[stage]), 5)
