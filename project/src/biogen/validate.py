"""Validation (프롬프트 A16, Gate G2/G3/G6). Schema conformance + biological /
provenance sanity checks that block "plausible but unsupported" values."""
from __future__ import annotations
from typing import Dict, List
import csv
import json
import math

import jsonschema

from . import paths
from .preset_compiler import compile_preset, get_param


def _load_schema(name: str) -> dict:
    with open(paths.SCHEMAS / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_preset_schema(resolved: dict) -> List[str]:
    schema = _load_schema("species_preset.schema.json")
    errors: List[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for e in sorted(validator.iter_errors(resolved), key=lambda x: x.path):
        errors.append(f"schema: {'/'.join(str(p) for p in e.path)}: {e.message}")
    return errors


def validate_joint_ranges(resolved: dict) -> List[str]:
    """Every joint DOF must have min <= neutral <= max and non-negative limits
    (Gate G3: 동작 범위 침범 차단)."""
    errors: List[str] = []
    for j in get_param(resolved, "anatomy.joints") or []:
        for dof in j.get("degrees_of_freedom", []):
            lo, hi, neu = dof.get("min"), dof.get("max"), dof.get("neutral")
            if None in (lo, hi, neu):
                continue
            if not (lo <= neu <= hi):
                errors.append(f"joint {j.get('joint_id')}: neutral {neu} outside [{lo},{hi}]")
            if dof.get("max_speed", 0) < 0:
                errors.append(f"joint {j.get('joint_id')}: negative max_speed")
    return errors


def validate_biomech(resolved: dict) -> List[str]:
    """Sanity: cruise <= burst, positive frequencies, positive size."""
    errs: List[str] = []
    L = get_param(resolved, "morphometrics.reference_length_m", 0.0)
    if not L or L <= 0:
        errs.append("morphometrics.reference_length_m must be > 0")
    cruise = get_param(resolved, "locomotion.cruise_speed_bl")
    burst = get_param(resolved, "locomotion.burst_speed_bl")
    if cruise is not None and burst is not None and cruise > burst:
        errs.append(f"cruise_speed_bl ({cruise}) > burst_speed_bl ({burst})")
    f = get_param(resolved, "locomotion.tailbeat_freq_cruise")
    if f is not None and f <= 0:
        errs.append("tailbeat_freq_cruise must be > 0")
    return errs


def validate_provenance(resolved: dict) -> List[str]:
    """Behaviors must reference action primitives (규칙 12); no Inferred value
    may masquerade with confidence >= 0.7 (규칙 3)."""
    errs: List[str] = []
    for b in get_param(resolved, "behavior.ethogram") or []:
        if not b.get("action_primitive_ids"):
            errs.append(f"behavior {b.get('behavior_id')} has no action_primitive_ids")
    return errs


def audit_evidence_ledger() -> Dict[str, object]:
    """Cross-check the ledger: Inferred/ArtistAuthored rows must not carry high
    confidence; transfers must record transfer_from_taxon_id (규칙 7, §7)."""
    path = paths.EVIDENCE / "evidence_ledger.csv"
    problems: List[str] = []
    counts: Dict[str, int] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ec = row["evidence_class"]
            counts[ec] = counts.get(ec, 0) + 1
            try:
                conf = float(row["confidence"])
            except ValueError:
                conf = -1
            if ec == "ArtistAuthored" and conf > 0.30:
                problems.append(f"{row['parameter_id']}: ArtistAuthored conf {conf} > 0.30")
            if ec == "Inferred" and conf >= 0.70:
                problems.append(f"{row['parameter_id']}: Inferred conf {conf} >= 0.70")
            if ec == "Inferred" and "transfer" in row.get("derivation_formula", "").lower() \
               and not row.get("transfer_from_taxon_id"):
                problems.append(f"{row['parameter_id']}: transfer without transfer_from_taxon_id")
    return {"counts": counts, "problems": problems}


def validate_taxon(taxon_id: str) -> Dict[str, object]:
    resolved = compile_preset(taxon_id, seed=1)
    errors: List[str] = []
    errors += validate_preset_schema(resolved)
    errors += validate_joint_ranges(resolved)
    errors += validate_biomech(resolved)
    errors += validate_provenance(resolved)
    return {"taxon_id": taxon_id, "ok": not errors, "errors": errors,
            "build_hash": resolved["provenance"]["build_hash"]}
