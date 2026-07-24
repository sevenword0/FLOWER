# Master Plan — Procedural Biology Ecosystem (TARGET_TAXON = 어류 / fish)

Orchestrator (A00) plan realizing the commission prompt. The project is a
**taxon-agnostic** pipeline; `어류` is the current target, set in one place
(`config/target_taxon.yaml`). Swapping that value retargets everything.

## Goal (프롬프트 §1)

Deliver, within tool reach: a species-preset database, a procedural model
generator (mesh/rig/material), an anatomy-linked autonomous behavior + locomotion
system, an interacting virtual ecosystem, and a reproducible, provenance-tracked
data/build pipeline — with schemas, code, tests, sample presets and a minimal
working prototype. Not a proposal: runnable artifacts.

## Work breakdown → this repository

| Agent | Role | Delivered artifact(s) |
|---|---|---|
| A00 | Orchestrator/architect | `docs/master_plan.md`, `docs/dependency_graph.mmd`, `docs/decision_log.md`, `docs/risk_register.csv` |
| A01 | Taxonomy/naming/sources | `taxonomy/taxon_index.csv`, `sources/source_registry.yaml`, `sources/license_manifest.csv` |
| A02 | Literature/evidence | `evidence/evidence_ledger.csv`, `sources/bibliography.bib`, `evidence/evidence_gap_report.md` |
| A03 | Functional anatomy/ontology | `config/adaptation_profiles/*.yaml` (TAXON_ADAPTATION_MAP source), `ontology/anatomy_ontology.jsonld`, `ontology/functional_module_map.yaml` (generated) |
| A04/A05 | Support/joints/feeding + actuators | `bases/clade/*.json`, joint objects in presets, `src/biogen/geometry.py` skeleton |
| A06/A07 | Morphometrics/silhouette + external structures | `bases/morphotype/*.json` (girth profiles, fins) |
| A08/A09 | Material/optics + sensory | preset `appearance` + `src/biogen/sensory.py`, `material.json` exports |
| A10 | Procedural geometry/rig/deform | `src/biogen/geometry.py`, `exports/<taxon>/mesh_lod*.obj` + skeleton |
| A11 | Biomechanics/locomotion | `src/biogen/locomotion.py`, `locomotion` block in presets |
| A12 | Ethology/decision | `src/biogen/behavior.py`, `behavior.ethogram` in presets |
| A13 | Ecology/interaction | `src/biogen/ecosystem.py`, `ecosystem/scenarios/*.yaml` |
| A14 | Data engineering/software | `src/biogen/*` (compiler, CLI, validators), `pyproject.toml` |
| A15 | Performance/LOD | `src/biogen/lod.py`, `config/performance_budget.yaml`, LOD meshes |
| A16 | Integration/red-team/validation | `src/biogen/validate.py`, `tests/`, `docs/validation_report.md`, `docs/known_limitations.md` |

## Data contract (fixed in Wave 0, §5)

- Stable ids: `taxon_id`, `source_id`, `parameter_id`, functional-slot keys.
- Coordinate system + units: from the adaptation profile `body_plan` (fish:
  bilateral, +X rostro-caudal, SL-normalized). SI units.
- Evidence classes: `Measured | Derived | Inferred | ArtistAuthored` with
  confidence bands (§7). Every numeric datum carries provenance.
- Schemas in `schemas/` validate every produced preset (Gate G2).

## Execution waves (§5)

- **Wave 0** contracts: config, adaptation profiles, schemas, evidence ledger — done.
- **Wave 1** research: taxon index, sources, evidence ledger populated — done.
- **Wave 2** prototype: compiler → mesh/rig/material vertical slice — done.
- **Wave 3** ecology: ecosystem sim + LOD — done.
- **Wave 4** red-team: validators + pytest gates; findings fixed & documented — done.

See `docs/STAGE_REPORT.md` for the Stage 0–9 gate-by-gate report.
