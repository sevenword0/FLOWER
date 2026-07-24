# Stage 0–9 Execution Report (프롬프트 §13, §17)

Gate-by-gate report for TARGET_TAXON = 어류. Each stage lists deliverables, gate
verdict, and residual risk.

---

## Stage 0 — Scope & vertical slice
**Deliverables:** `config/target_taxon.yaml`, `config/adaptation_profiles/fish.yaml`,
4-species slice (trout / herring / seahorse / anglerfish) chosen for data-rich,
behavior-divergent, morphology-divergent, and data-poor coverage.
**Gate G0 (swap-only regeneration):** PASS. `taxon_profile` rebuilds the module
map + source routing from the single config literal; `bird.yaml` proves the swap.
**Residual:** only bilateral body plans authored.

## Stage 1 — Taxonomy / sources / licensing
**Deliverables:** `taxonomy/taxon_index.csv` (accepted names, synonyms, ids),
`sources/source_registry.yaml`, `sources/license_manifest.csv`, `bibliography.bib`.
**Gate G1 (no name conflicts / unlicensed data into build):** PASS. Every source
carries license + redistribution flags; copyrighted literature is parameters-only.
**Residual (R9):** live API ETL clients documented but not exercised.

## Stage 2 — Ontology / schema / evidence ledger
**Deliverables:** `schemas/*.json`, `ontology/anatomy_ontology.jsonld`,
`evidence/evidence_ledger.csv` (40 parameters), `evidence_gap_report.md`.
**Gate G2 (all outputs validate against common schema):** PASS. Evidence classes:
Measured 30 / Derived 3 / Inferred 5 / ArtistAuthored 2. Audit finds 0 problems
(no Inferred≥0.7, no ArtistAuthored>0.3, transfers record source taxon).

## Stage 3 — Morphology / structure / joints / actuators
**Deliverables:** `bases/clade/actinopterygii.json`, `bases/morphotype/*.json`
(girth profiles, fin templates), joint objects with DOF limits in presets.
**Gate G3 (connectivity + ranges match references):** PASS. `validate_joint_ranges`
enforces min ≤ neutral ≤ max and non-negative speeds; cruise ≤ burst enforced.

## Stage 4 — Surface / optics / sensory
**Deliverables:** preset `appearance.material_parameters` (OpenPBR-approx),
`sensory_system` (vision cone + lateral line), anglerfish esca emissive (Inferred).
**Gate G4 (comparable across lighting/views):** PARTIAL. Material fields are
structured for spectral data, but only runtime-approx colors (ArtistAuthored) are
present; no measured reflectance golden-render comparison yet (see limitations #3).

## Stage 5 — Procedural model / rig vertical slice
**Deliverables:** `geometry.py` → `exports/<taxon>/mesh_lod0..3.obj` +
`skeleton.json` + `material.json`, regenerated with no manual post-processing.
**Gate G5 (deterministic regeneration):** PASS. Same preset+seed ⇒ identical
`build_hash` and identical OBJ (tested). LOD reduces vertex count monotonically.

## Stage 6 — Locomotion / behavior
**Deliverables:** `locomotion.py` (per-swim-mode oscillator, constant-stride
speed↔frequency), `behavior.py` (ethogram + Utility + hysteresis), presets'
`behavior.ethogram` linked to action primitives.
**Gate G6 (speed/turn/occupancy within observed ranges):** PASS. Faster throttle
⇒ higher beat frequency; MPF (seahorse) shows near-zero body bending vs BCF
(trout); BCF spine curvature grows posteriorly. Cruising-school NND = **0.76–0.82
BL** across seeds (observed 0.3–1.2, target 0.7 / P0026).

## Stage 7 — Ecosystem
**Deliverables:** `ecosystem.py` (sensory→behavior→locomotion→physics),
`ecosystem/scenarios/*.yaml`, finite logistic plankton field, role-based trophic
interactions.
**Gate G7 (interaction, no infinite resource/energy/collision):** PASS. Energy
and resource are clamped; predation bounded by handling time + hunger gating +
schooling dilution. Prey population stays **35–40 / 40** over 60 s (no collapse);
predator/prey interactions and bidirectional resource depletion occur.

## Stage 8 — Optimization / LOD
**Deliverables:** `lod.py` (Hero/Standard/Crowd/Far-field), `performance_budget.yaml`,
LOD mesh sets and per-tier tick/behavior fidelity.
**Gate G8 (budget met, silhouette/behavior within tolerance):** PARTIAL. Tiering,
budgets, and LOD meshes exist and are selectable by distance/importance; a
hardware benchmark on a target engine is out of scope (limitation #10).

## Stage 9 — Extensibility & portability
**Deliverables:** new species = add a preset (no code change); `bird.yaml` +
`test_portability.py`.
**Gate G9 (no hardcoding / schema break / wrong slot residue):** PASS. Swapping
`target_taxon` to 조류 regenerates the module map with the bird rig strategy
(`limbed_biped_with_wings`), bird source routing (avibase/ebird), and correct N/A
handling for buoyancy. A package scan confirms no taxon literal in code.

---

## Overall verdict (A16)

**Conditional APPROVED.** All hard gates (G0, G1, G2, G3, G5, G6, G7, G9) pass with
24/24 automated tests. G4 and G8 are PARTIAL by scope (no measured spectra / no
engine benchmark in this environment), documented in `known_limitations.md`. No
"plausible-but-unsupported" value survives the evidence audit; data-poor cases are
explicitly Inferred with recorded transfer provenance.
