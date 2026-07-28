# biogen — Procedural Biology Ecosystem (TARGET_TAXON = 어류 / fish)

A **taxon-agnostic**, reproducible pipeline that turns provenance-tracked
biological data into: species presets → procedural mesh/rig/material → anatomy-
linked autonomous behavior + locomotion → an interacting virtual ecosystem, with
schema validation and regression tests.

Built by executing the "범용 멀티에이전트 생물 절차 모델링·자율행동 생태계" commission
prompt for fish. The design goal is the **one-word swap**: the target taxon lives
in exactly one config value, and swapping it retargets the whole pipeline (a
bird profile ships to prove it).

## Quick start

```bash
pip install -r requirements.txt          # numpy, PyYAML, jsonschema, pytest
./run.sh module-map                      # regenerate functional module map for the active taxon
./run.sh compile oncorhynchus_mykiss     # resolve a species preset (clade+morphotype+delta+seed)
./run.sh generate oncorhynchus_mykiss    # write mesh_lod0..3.obj + skeleton.json + material.json to exports/
./run.sh validate                        # schema + biomech + evidence audit for the vertical slice
./run.sh simulate                        # run the mixed-community ecosystem scenario
./run.sh simulate schooling_validation   # run the cruising-school NND validation scenario
./run.sh resolve-taxa                    # verify names against GBIF + WoRMS (needs network egress)
./run.sh build-all                       # generate + validate everything

pytest                                   # gate tests (G2..G9) + ETL fixtures
node tests/bench_lod.mjs                 # LOD benchmark against the browser build (G8)
```

(`run.sh` just sets `PYTHONPATH=src`; equivalently `pip install -e .` then use the
`biogen` command.)

## The one-word swap

Everything keys off one value in `config/target_taxon.yaml`:

```yaml
target_taxon: "어류"     # change this to "조류" (birds) to retarget
```

`src/biogen/taxon_profile.py` resolves it to `config/adaptation_profiles/<key>.yaml`,
which realizes the 13 functional slots (support, joints, feeding, actuation,
locomotion, physiology, covering, sensors, optics, behavior, ecology, variation)
for that clade, and regenerates the module map + source routing. No taxon literal
appears in code — a test (`tests/test_portability.py`) enforces it.

## Vertical slice (4 representative species)

| taxon | why chosen | morphotype | swim mode |
|---|---|---|---|
| *Oncorhynchus mykiss* (rainbow trout) | data-rich baseline | fusiform | subcarangiform |
| *Clupea harengus* (Atlantic herring) | behavior-divergent obligate schooler | fusiform_pelagic | carangiform |
| *Hippocampus kuda* (seahorse) | morphology-divergent, MPF propulsion | pipefish | dorsal_undulation |
| *Melanocetus johnsonii* (anglerfish) | data-poor inference stress test | globiform_bathy | subcarangiform_slow (Inferred) |

## Layout

```
config/       target_taxon.yaml (the one literal) + adaptation_profiles/{fish,bird}.yaml + performance_budget.yaml
schemas/      species_preset / joint / behavior / anatomy JSON Schemas
sources/      source_registry.yaml, license_manifest.csv, bibliography.bib
taxonomy/     taxon_index.csv
evidence/     evidence_ledger.csv (Measured/Derived/Inferred/ArtistAuthored + confidence) + gap report
ontology/     anatomy_ontology.jsonld + functional_module_map.yaml (generated)
bases/        clade/ + morphotype/ reusable bases
presets/      <taxon_id>/preset.json species deltas
src/biogen/   taxon_profile, preset_compiler, geometry, locomotion, sensory, behavior, ecosystem, lod, validate, cli
ecosystem/    scenarios/*.yaml (data-driven world composition)
exports/      generated mesh_lod*.obj + skeleton.json + material.json
tests/        pytest gate checks
docs/         master_plan, architecture, decision_log, known_limitations, validation_report, STAGE_REPORT, risk_register, dependency_graph
```

## Evidence discipline

Every numeric datum in `evidence/evidence_ledger.csv` carries `evidence_class`
(Measured/Derived/Inferred/ArtistAuthored), confidence, source, and (for
transfers) `transfer_from_taxon_id`. Inferred values are capped below measured
confidence and audited by `validate.py`. See `docs/known_limitations.md` for what
is and isn't grounded in primary measurement.

## Status

41/41 tests pass. See `docs/STAGE_REPORT.md` for the Stage 0–9 gate report,
`docs/validation_report.md` for measured validation numbers, and
`docs/performance_report.md` for the LOD benchmark.
