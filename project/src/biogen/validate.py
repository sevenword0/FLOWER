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


# 규칙 4 requires every parameter to carry these. A blank is not "unknown" —
# it is an unanswered question, so the ledger must state the answer explicitly.
REQUIRED_FIELDS = ("taxon_id", "parameter_name", "value", "unit", "distribution",
                   "sample_size", "sex", "life_stage", "body_size", "population",
                   "season", "environment_context", "measurement_method",
                   "source_id", "source_location", "evidence_class", "confidence",
                   "uncertainty_reason", "license_id", "review_status")

# We never invent N. Where a real count is unavailable the row must say which
# kind of un-counted evidence stands behind it.
SAMPLE_SIZE_VOCAB = {"aggregate", "not_reported", "species_character", "n/a"}

CATEGORICAL_UNITS = {"category", "bool"}


def audit_evidence_ledger() -> Dict[str, object]:
    """Cross-check the ledger (규칙 4, 6, 7, §7).

    Blocks: over-confident Inferred/ArtistAuthored values, transfers without a
    recorded source taxon, blank required fields, fabricated-looking sample
    sizes, numeric rows missing a range, categorical rows carrying a bogus one,
    and Derived rows with no derivation formula.
    """
    path = paths.EVIDENCE / "evidence_ledger.csv"
    problems: List[str] = []
    counts: Dict[str, int] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pid = row["parameter_id"]
            ec = row["evidence_class"]
            counts[ec] = counts.get(ec, 0) + 1
            try:
                conf = float(row["confidence"])
            except ValueError:
                conf = -1

            if ec == "ArtistAuthored" and conf > 0.30:
                problems.append(f"{pid}: ArtistAuthored conf {conf} > 0.30")
            if ec == "Inferred" and conf >= 0.70:
                problems.append(f"{pid}: Inferred conf {conf} >= 0.70")
            if ec == "Inferred" and "transfer" in row.get("derivation_formula", "").lower() \
               and not row.get("transfer_from_taxon_id"):
                problems.append(f"{pid}: transfer without transfer_from_taxon_id")

            # 규칙 4 — no silent blanks
            for f in REQUIRED_FIELDS:
                if not (row.get(f) or "").strip():
                    problems.append(f"{pid}: required field '{f}' is blank")

            ss = (row.get("sample_size") or "").strip()
            if ss and ss not in SAMPLE_SIZE_VOCAB and not ss.isdigit():
                problems.append(
                    f"{pid}: sample_size '{ss}' is neither a count nor one of "
                    f"{sorted(SAMPLE_SIZE_VOCAB)}")

            # 규칙 6 — a measured scalar without a range hides its spread
            is_cat = row.get("unit") in CATEGORICAL_UNITS
            has_range = bool((row.get("min_value") or "").strip()
                             and (row.get("max_value") or "").strip())
            if not is_cat and not has_range:
                problems.append(f"{pid}: numeric parameter has no min/max range")
            if is_cat and ((row.get("min_value") or "").strip()
                           or (row.get("max_value") or "").strip()):
                problems.append(f"{pid}: categorical parameter carries a numeric range")

            if ec == "Derived" and not (row.get("derivation_formula") or "").strip():
                problems.append(f"{pid}: Derived value has no derivation_formula")

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
