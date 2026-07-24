# Decision Log

Key decisions and their rationale (프롬프트 규칙 16: choose sensible defaults and
proceed; §12 tool selection).

| # | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| D1 | Single taxon literal in `config/target_taxon.yaml`, resolved to an adaptation profile | 규칙 17 / Gate G9 portability. Code stays taxon-neutral; a self-check test enforces it. | Hard-coding fish structures in code |
| D2 | Reference build uses canonical published values in the evidence ledger, flagged by evidence_class | No live API keys in this environment; the pipeline is the deliverable, values are traceable + honestly graded (규칙 2,3,15) | Fabricating "measured" values; blocking on missing data |
| D3 | Python + NumPy + YAML + jsonschema stack | Runs headless with no DCC/binary dependency; matches §12 Research/ETL default; testable | Houdini/Blender/USD required at build time |
| D4 | Mesh output as plain-text OBJ + JSON skeleton/material | Prompt allows reproducible scripts/specs when binaries can't be produced (§1). OBJ is universally importable to Houdini/Blender/USD/UE | Emitting proprietary DCC files |
| D5 | Preset = layered deep-merge (clade+morphotype+species delta+context+seed) | 규칙: reuse bases, store species as deltas; determinism for Gate G5 | Independent per-species models |
| D6 | Behavior = ethogram + Utility scoring + min-dwell hysteresis; shared grammar, per-species data | 규칙 13,14; avoids random animation and per-species code | Pure FSM per species; pure RL black box (규칙 3) |
| D7 | Locomotion oscillator with constant-stride tail-beat scaling (Bainbridge/Videler) | Ties speed↔frequency↔rig with literature grounding (규칙 12) | Arbitrary animation curves |
| D8 | Schooling validated on an undisturbed cruising scenario; mixed community tests population stability | The observed NND (P0026) was measured on cruising schools; validate in-context (§6 conflict rule) | Forcing a predator-disturbed school to hit cruising NND |
| D9 | Predation bounded by handling time + hunger gating + schooling dilution | Gate G7 (no population collapse / infinite energy); reflects real predator satiation & dilution effect | Unbounded per-tick striking |
| D10 | 4-species vertical slice: trout / herring / seahorse / anglerfish | Spans data-rich baseline, behavior-divergent, morphology-divergent, data-poor inference (§13 Stage 0) | One species; all species at once |
