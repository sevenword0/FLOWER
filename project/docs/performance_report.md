# Performance Report — LOD (프롬프트 §14, §15, Gate G8)

Measured with `node project/tests/bench_lod.mjs` against the browser build
(`fish/index.html`), 960×540, 55 agents unless stated.

## How to read these numbers

**Absolute frame times here are from a software rasterizer.** This environment
has no GPU, so Chromium falls back to SwiftShader. Treat the millisecond
columns as a *relative* comparison between LOD settings on identical work, not
as a hardware result. The triangle counts are rasterizer-independent and are the
load-bearing measurement.

## Mesh budget per tier

Ring/segment budgets come from `LOD_BUDGET`, shared by `biogen/geometry.py` and
the browser port so both produce the same silhouettes.

| taxon | LOD0 | LOD1 | LOD2 | LOD3 |
|---|---:|---:|---:|---:|
| oncorhynchus_mykiss | 2270 | 1006 | 354 | 98 |
| clupea_harengus | 2270 | 1006 | 354 | 98 |
| melanocetus_johnsonii | 2268 | 1004 | 352 | 96 |
| hippocampus_kuda | 2262 | 998 | 346 | 90 |

Triangles per tier drop by roughly 2.3× each step, **23× from hero to far
field**. Fin membranes survive to LOD3, so the silhouette that identifies a
species at distance is preserved while the body loft collapses.

## Frame cost by LOD setting (55 agents)

Tier assignment uses distance in **body lengths** (`lod.py`: hero ≤10 BL,
standard ≤40 BL, crowd ≤150 BL, then far field), so a 12 cm anglerfish drops a
tier nearer the camera than a 30 cm trout — the budget is perceptual, not metric.

| setting | median | p95 | triangles | draw calls | tier split (H/S/C/F) |
|---|---:|---:|---:|---:|---|
| **distance policy** | 1.10 ms | 2.20 ms | 50,078 | 6 | 0 / 47 / 8 / 0 |
| forced LOD0 | 1.70 ms | 2.70 ms | 124,814 | 4 | 55 / 0 / 0 / 0 |
| forced LOD1 | 1.10 ms | 2.40 ms | 55,294 | 4 | 0 / 55 / 0 / 0 |
| forced LOD2 | 0.70 ms | 1.20 ms | 19,434 | 4 | 0 / 0 / 55 / 0 |
| forced LOD3 | 0.30 ms | 1.20 ms | 5,354 | 4 | 0 / 0 / 0 / 55 |

The policy cuts **59.9 % of triangles** versus drawing everything at hero
detail, for **1.55×** the frame rate, at the cost of two extra draw calls
(tier splits fragment the instanced batch). Draw calls stay far under the
1500 budget in `performance_budget.yaml`.

## Scaling — where the bottleneck actually is

| agents | policy | forced LOD0 | frame gain | triangle cut |
|---:|---|---|---:|---:|
| 55 | 1.10 ms / 50k tri | 1.70 ms / 125k tri | 1.55× | −59.9 % |
| 131 | 6.10 ms / 130k tri | 6.10 ms / 297k tri | **1.00×** | −56.1 % |

At 131 agents the triangle cut still lands, but **frame time does not improve at
all**. The workload has stopped being geometry-bound: the cost is the JavaScript
side — per-agent perception is O(n²), plus instance-buffer packing — and mesh
LOD does nothing for either.

This is the useful finding. `lod.py` already specifies a *behavior* LOD ladder
(`full_sensory_internal_state` → `reduced_sensors` → `flocking_rules_limited_state`
→ `density_biomass_aggregate`) and reduced tick rates per tier, and the browser
build does **not** implement it — every agent runs full perception at 20 Hz
regardless of distance. Mesh LOD alone cannot hit a large-population budget;
the next real performance work is behavior LOD and spatial partitioning of the
neighbour query, not more geometry reduction.

## A bug this benchmark caught

Before measuring, LOD2 and LOD3 reported identical triangle counts (354/354).
The browser port clamped the tier index to `0..2`, a leftover from when it had
three tiers, so far-field silently rendered at crowd detail. Declaring four
tiers in config would have kept reporting "four tiers" indefinitely; measuring
them is what exposed that only three existed. Fixed, and the ladder above is the
post-fix measurement.

## Verdict — Gate G8

**PARTIAL.** Verified: the tier ladder exists and is distinct, the distance
policy assigns tiers as specified, and geometry cost falls as designed
(−59.9 % triangles, 23× hero→far-field). Not verified: the absolute
`frame_budget_ms: 16.6` target on the stated hardware, because no GPU is
available in this environment; and the large-population budget, which the
scaling test shows is CPU-bound and therefore blocked on behavior LOD rather
than on rendering.
