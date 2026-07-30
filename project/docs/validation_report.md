# Validation Report (프롬프트 §15, A16)

Measured numbers from the reference build. Reproduce with `pytest` and the CLI.
All simulations are deterministic per seed.

## Automated gate tests

`pytest` → **62 passed** (`test_schema.py`, `test_determinism.py`,
`test_portability.py`, `test_locomotion.py`, `test_ecosystem.py`,
`test_etl.py`, `test_shape.py`, `test_gltf.py`).

## Data / provenance (Gate G2)

- Evidence ledger: 40 parameters — Measured 30, Derived 2, Inferred 6,
  ArtistAuthored 2. (P0016 was reclassified: it was labelled Derived but had no
  derivation formula, which makes it an Inferred estimate, not a computed one.)
- Every required field is populated. `sample_size` is a count where one exists
  and otherwise names the kind of un-counted evidence — `aggregate` 11,
  `species_character` 13, `not_reported` 11, `n/a` 5. No value was invented to
  fill a column.
- Evidence audit problems: **0** (no Inferred ≥ 0.7, no ArtistAuthored > 0.3,
  all transfers record `transfer_from_taxon_id`).
- All 4 resolved presets validate against `species_preset.schema.json`.

## Geometry (Gate G5)

Deterministic: same preset+seed ⇒ identical `build_hash` and identical OBJ.
LOD vertex counts decrease monotonically (Hero→Far):

| taxon | ref length | LOD0 | LOD1 | LOD2 | LOD3 |
|---|---|---|---|---|---|
| oncorhynchus_mykiss | 0.304 m | 1175 | 535 | 203 | 71 |
| clupea_harengus | 0.284 m | 1175 | 535 | 203 | 71 |
| hippocampus_kuda | 0.203 m | 1162 | 522 | 190 | 58 |
| melanocetus_johnsonii | 0.122 m | 1173 | 533 | 201 | 69 |

## Locomotion (Gate G6)

Speed→frequency scaling and swim-mode differentiation (constant-stride relation,
Bainbridge/Videler):

| taxon | swim mode | cruise (BL/s) | burst (BL/s) | f@cruise | f@burst | MPF? |
|---|---|---|---|---|---|---|
| oncorhynchus_mykiss | subcarangiform | 1.6 | 8.0 | 3.0 Hz | 15.0 Hz | no |
| clupea_harengus | carangiform | 2.0 | 10.0 | 3.5 Hz | 17.5 Hz | no |
| hippocampus_kuda | dorsal_undulation | 0.5 | 1.2 | 28 Hz | 42 Hz | yes |
| melanocetus_johnsonii | subcarangiform_slow (Inferred) | 0.3 | 2.0 | 1.2 Hz | 8.0 Hz | no |

- BCF swimmers show posteriorly-growing spine curvature; the MPF swimmer
  (seahorse) shows near-zero body bending — asserted in `test_locomotion.py`.

## Schooling — Gate G6 (cruising school)

Undisturbed cruising herring shoal, 40 individuals, 600 steps (60 s), 8 seeds
(11, 7, 3, 42, 99, 256, 777, 2024):

- **Mean NND = 0.782 BL** (min 0.738, max 0.818).
- Observed reference: 0.7 BL, band 0.3–1.2 BL (P0026, Pitcher & Partridge 1983).
- **Verdict: within band, stable across seeds** (no seed-luck).

## Ecosystem — Gate G7 (population stability)

Mixed community (40 herring, 6 trout, 2 anglerfish, 4 seahorse), 600 steps, 8 seeds:

- Herring survivors: **mean 37.6 / 40**, min 35 — **no population collapse**.
- Predation events per run: [3, 0, 3, 1, 2, 5, 1, 4] — interactions occur, rate
  bounded by handling time + hunger gating + schooling dilution.
- Energy ∈ [0,1] and plankton resource ∈ [0, cap] at all times (asserted).

## Portability — Gate G9

Three profiles, swapped by changing one config value:

| target | symmetry | rig strategy | absent sub-structures |
|---|---|---|---|
| 어류 | bilateral | `spline_spine` | — |
| 조류 | bilateral | `limbed_biped_with_wings` | buoyancy |
| 해파리 | **radial** | `radial_umbrella` | jaws, fins, scales/feathers, head |

- The cnidarian case is the load-bearing one: radial symmetry, no skeleton, no
  spine, no fins. `어류 → 조류` alone never tests the coordinate system.
- No slot is reported wholly absent for any profile, which is correct — all
  three animals feed, move, have a surface and sense. Only *sub-structures* are
  absent, and they are named.
- Three distinct rig strategies; source routing retargets away from the fish
  authorities.
- Package scan finds **0** taxon literals in `src/biogen/*.py` — and it earns
  its keep: it caught the word "jellyfish" in a docstring written minutes
  earlier during this very change.

## Taxonomic resolution (R9)

`./run.sh resolve-taxa` queries GBIF and WoRMS, caches raw responses, and
reconciles the answers against `taxonomy/taxon_index.csv` without mutating it.
Parsing and reconciliation are covered by 17 offline fixture tests, including
fuzzy-match flagging, synonym→accepted redirection, authority disagreement, and
the blocked-network path.

**Not verified against the live APIs.** This environment's network policy denies
`api.gbif.org` and `www.marinespecies.org` (`CONNECT 403`), so the run recorded
`network_reachable: false`, `unresolved_network` ×4, changed nothing, and exited
1. `taxonomy/resolution_report.json` is a record of a blocked run and must not be
read as name confirmation.

## LOD performance (G8)

Measured with `node project/tests/bench_lod.mjs`; full numbers in
`docs/performance_report.md`.

- Tier ladder is distinct: **2270 → 1006 → 354 → 98** triangles (23× hero→far field).
- Distance policy vs everything at hero detail: **−59.9 % triangles, 1.55× frame rate**
  at 55 agents, 6 draw calls (budget 1500).
- At 131 agents the triangle cut holds (−56.1 %) but frame time is unchanged
  (1.00×): the workload is CPU-bound there, which is why the behaviour ladder
  exists. With tiers engaged it gives **7.5×** at 271 agents.
- Absolute times come from a software rasterizer (no GPU here) and are valid only
  as relative comparisons.

## Shape (§15 형상)

Full numbers in `docs/shape_report.md`, raw in `docs/shape_metrics.json`.

- LOD silhouette IoU vs LOD0: **0.998–0.999 (LOD1)**, 0.949–0.963 (LOD2),
  0.851–0.889 (LOD3) — decimation preserves the identifying outline.
- Proportion error (length / depth / width): **< 1 %** for all four taxa, so
  the loft realises the ratios its preset asked for.
- Girth-profile landmark error: 0.4–0.8 % for the fusiform taxa, 6.3 % for the
  seahorse, where discrete sampling along the posture curve costs the most.

Writing these metrics exposed two faults **in the metrics themselves** — a
length measured over the caudal fin, and a depth measured as a global bounding
box on a curved body — both fixed. See the report.

## Recruitment (§11)

- `World.reproduction` is energy-gated with a logistic density brake. A herring
  population started at 30 grows to and settles at its carrying capacity of 48,
  rather than declining monotonically as before.
- Offspring energy is paid by the parent; agent energy stays within [0,1].
- Off by default, so the recorded NND and population validations stay comparable.

## glTF export (§12)

- `.gltf` + `.bin` + `.glb` per taxon, carrying mesh, an 8-joint spine skin and
  a PBR material in one file — OBJ left the rig and material stranded beside it.
- Tests check accessor bounds against the buffer, 4-byte alignment, skin weight
  normalisation, GLB container length, and that `build_hash` travels with the
  asset so a stray mesh can be traced back to its preset.

## Not fully validated (honest gaps)

- **G4 appearance:** no measured reflectance spectra; colors are ArtistAuthored
  (confidence ≤ 0.29). No golden-render comparison.
- **G8 performance:** absolute 16.6 ms budget unverified (no GPU). Behaviour
  LOD works (7.5× when tiers engage) but is inert in the default 16 m scenario.
- **Shape accuracy:** metrics are internal-consistency only; no reference
  specimens to score against.
- **Disturbed-school NND** not compared to a measured disturbed distribution.

See `known_limitations.md` for the full list.
