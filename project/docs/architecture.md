# Architecture

## Layers

```
config/            one taxon literal + adaptation profiles (the ONLY place a taxon is named)
   │
   ▼
taxon_profile.py   resolves target -> profile -> TAXON_ADAPTATION_MAP + module map + source routing
   │
schemas/           JSON Schemas every artifact validates against
evidence/          provenance ledger (Measured/Derived/Inferred/ArtistAuthored + confidence)
bases/ + presets/  clade/morphotype bases (reused) + species deltas
   │
   ▼
preset_compiler.py CladeBase + MorphotypeBase + SpeciesDelta + ContextDelta + IndividualSeed -> resolved preset (deterministic, hashed)
   │
   ├── geometry.py     lofted mesh + rig skeleton + material  (LOD 0..3)
   ├── locomotion.py   per-swim-mode oscillator (speed↔frequency↔rig)
   ├── sensory.py      vision cone + lateral-line detection
   ├── behavior.py     ethogram + Utility + hysteresis -> command (steer + throttle)
   └── ecosystem.py    agents: sensory→behavior→locomotion→physics + interactions + resource field
   │
lod.py             Hero / Standard / Crowd / Far-field tiering
validate.py        schema + biomech + provenance + evidence audit
tests/             gate checks G2..G9
```

## The behavior→motion→rig chain (규칙 12)

The core anti-siloing principle is a single unbroken data path:

```
environment + other agents
  → sensory model (detection)
  → internal drives (hunger/fear/fatigue/reproduction)
  → ethogram state selection + Utility score (behavior.py)
  → steering family + throttle command
  → locomotion primitive oscillator (locomotion.py)
  → spine/fin rig curvature (geometry.build_skeleton + spine_curvature)
  → position/deformation output (ecosystem integration)
```

No behavior exists without an `action_primitive_ids` link (schema-enforced), and
no locomotion primitive exists without kinematic limits from the preset.

## Determinism

`preset_compiler` and `geometry` avoid wall-clock and RNG except through an
explicit `IndividualSeed`. `ecosystem.World` takes a seed and draws all
randomness from one generator. Same inputs ⇒ identical `build_hash` and identical
trajectories (Gate G5/G6), which is what makes the regression tests meaningful.

## Retargeting (one-word swap)

`taxon_profile.load_profile` maps `target_taxon` → profile key via an alias
table, loads `adaptation_profiles/<key>.yaml`, and builds the module map from the
profile's functional slots + source routing. `bird.yaml` ships as a second
profile so the swap is demonstrable and CI-tested (`test_portability.py`).

## Export / interop

Meshes are OBJ, rig/material are JSON — importable into Houdini, Blender,
OpenUSD, Unreal, Unity, Godot, or glTF pipelines (§12). The live rig/control
graph is kept in the runtime (not baked into a scene format), matching the
prompt's guidance that USD is an interchange format, not the rig runtime.
