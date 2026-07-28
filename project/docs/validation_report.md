# Validation Report (프롬프트 §15, A16)

Measured numbers from the reference build. Reproduce with `pytest` and the CLI.
All simulations are deterministic per seed.

## Automated gate tests

`pytest` → **41 passed** (`tests/test_schema.py`, `test_determinism.py`,
`test_portability.py`, `test_locomotion.py`, `test_ecosystem.py`,
`test_etl.py`).

## Data / provenance (Gate G2)

- Evidence ledger: 40 parameters — Measured 30, Derived 3, Inferred 5,
  ArtistAuthored 2.
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

- `target_taxon: 조류` regenerates the module map with rig strategy
  `limbed_biped_with_wings`, bird source routing (avibase/ebird/macaulay), and
  N/A buoyancy correctly flagged and re-realized.
- Package scan finds **0** taxon literals in `src/biogen/*.py`.

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
  (1.00×) — the workload is CPU-bound there, so behavior LOD, not geometry, is
  the next lever.
- Absolute times come from a software rasterizer (no GPU here) and are valid only
  as relative comparisons.

## Not fully validated (honest gaps)

- **G4 appearance:** no measured reflectance spectra; colors are ArtistAuthored
  (confidence ≤ 0.29). No golden-render comparison.
- **G8 performance:** LOD measured and verified relatively, but the absolute
  16.6 ms budget is unverified (no GPU); behavior LOD not yet implemented.
- **Disturbed-school NND** not compared to a measured disturbed distribution.

See `known_limitations.md` for the full list.
