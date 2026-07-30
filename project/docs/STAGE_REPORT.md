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
**Residual (R9), partially closed:** the ETL client is now implemented
(`src/biogen/etl.py`, `./run.sh resolve-taxa`) with GBIF + WoRMS backends,
caching, conflict reporting and 17 offline fixture tests. It has *not* been run
against the live APIs — this environment's network policy denies those hosts
(`CONNECT 403`), so the resolver records `unresolved_network`, changes nothing,
and exits non-zero. `taxonomy/resolution_report.json` documents a blocked run,
not a verified one.

## Stage 2 — Ontology / schema / evidence ledger
**Deliverables:** `schemas/*.json`, `ontology/anatomy_ontology.jsonld`,
`evidence/evidence_ledger.csv` (40 parameters), `evidence_gap_report.md`.
**Gate G2 (all outputs validate against common schema):** PASS. Evidence classes:
Measured 30 / Derived 2 / Inferred 6 / ArtistAuthored 2. Audit finds 0 problems
(no blank required field, no Inferred≥0.7, no ArtistAuthored>0.3, every
transfer records its source taxon, no Derived value without a formula).

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
present; no measured reflectance golden-render comparison yet (limitation #3).
Shape-side validation now exists (`docs/shape_report.md`): silhouette IoU,
proportion and landmark error, all internal-consistency checks — <1 % proportion
error across the slice — but with no reference specimens they are not accuracy
claims (limitation #4).

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
Recruitment is now available (opt-in `World.reproduction`): energy-gated with a
logistic density brake, a herring population settles at carrying capacity
(30 → 48) instead of only declining, and offspring energy is paid by the parent.

## Stage 8 — Optimization / LOD
**Deliverables:** `lod.py` (Hero/Standard/Crowd/Far-field), `performance_budget.yaml`,
LOD mesh sets and per-tier tick/behavior fidelity.
**Gate G8 (budget met, silhouette/behavior within tolerance):** PARTIAL —
now measured. The browser build implements the distance policy end to end and
`project/tests/bench_lod.mjs` benchmarks it: the tier ladder is distinct
(2270→1006→354→98 tri, 23× hero→far field) and the policy cuts **59.9 % of
triangles** for **1.55×** the frame rate at 55 agents. Benchmarking caught a
real bug — the browser port clamped the tier index to 0..2, so far-field was
silently drawing at crowd detail. The scaling test then showed that past ~130
agents the workload is CPU-bound, so the *behaviour* ladder was implemented too:
it gives **7.5×** at 271 agents once the tiers engage, and tier radii are now
derived from the scenario's spatial scale rather than fixed globally. Still
unverified: the absolute 16.6 ms budget on target hardware (no GPU here,
software rasterizer only). See `docs/performance_report.md`.

## Stage 9 — Extensibility & portability
**Deliverables:** new species = add a preset (no code change); three adaptation
profiles (`fish`, `bird`, `cnidarian`) + `test_portability.py`.
**Gate G9 (no hardcoding / schema break / wrong slot residue):** PASS, and now
on a genuinely hard case. `어류 → 조류` is bilateral → bilateral: it swaps the rig
but never challenges the coordinate system. `해파리` (cnidarian medusa) is
**radially symmetric with no skeleton, no jaws, no fins and no spine**, and the
swap still regenerates cleanly:

| target | symmetry | rig strategy | absent sub-structures |
|---|---|---|---|
| 어류 | bilateral | `spline_spine` | — |
| 조류 | bilateral | `limbed_biped_with_wings` | buoyancy |
| 해파리 | **radial** | `radial_umbrella` | jaws, fins, scales/feathers, head |

Three distinct rig strategies, source routing retargeted away from the fish
authorities, and no taxon literal in code (package scan). The radial profile also
**exposed a semantic bug**: a slot was marked wholly N/A when any one
sub-structure was N/A, so the map claimed a jellyfish does not feed and a bird
has no physiology. `na` (slot absent) and `na_substructures` (slot re-realized,
these features absent) are now separate — which is what 규칙 "없으면 N/A 후 기능
대응 구조로 교체" actually asks for.

---

## Overall verdict (A16)

**Conditional APPROVED.** All hard gates (G0, G1, G2, G3, G5, G6, G7, G9) pass with
62/62 automated tests. G4 and G8 remain PARTIAL by environment, not by omission:
G4 lacks measured reflectance spectra, and G8 now has a real LOD benchmark but no
GPU to verify the absolute frame budget against. R9 (live taxonomic verification)
is implemented and unit-tested but blocked by this environment's network policy.
All three are documented in `known_limitations.md` and
`docs/performance_report.md`. No "plausible-but-unsupported" value survives the
evidence audit; data-poor cases are explicitly Inferred with recorded transfer
provenance, and a blocked verification run is never reported as a passing one.
