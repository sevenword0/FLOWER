# Evidence Gap Report — fish (어류) reference build

Generated for the Stage 1–2 vertical slice. Tracks what is Measured vs
Inferred/Derived/ArtistAuthored and where confidence is low (규칙 15, §7, A02).

## Coverage summary by species

| taxon_id | Measured | Derived | Inferred | ArtistAuthored | lowest conf |
|---|---|---|---|---|---|
| oncorhynchus_mykiss | 8 | 2 | 1 | 1 | 0.28 (pattern) |
| hippocampus_kuda | 7 | 1 | 0 | 1 | 0.25 (pattern) |
| clupea_harengus | 7 | 2 | 0 | 0 | 0.60 (alignment) |
| melanocetus_johnsonii | 4 | 0 | 5 | 0 | 0.30 (cruise speed) |

## Priority gaps (need primary measurement or better transfer)

1. **melanocetus_johnsonii kinematics** — no direct swimming measurements exist
   for this bathypelagic ambush predator. `swim_mode`, `cruise_speed` are
   Inferred via transfer from generic Lophiiformes / body-form scaling from
   `oncorhynchus_mykiss` with explicit confidence ≤ 0.35 and
   `transfer_from_taxon_id` recorded. **Do not** present as measured.
2. **hippocampus_kuda cruise speed** — dorsal-fin propulsion is well described
   qualitatively (Ashley-Ross 2002) but quantitative station-to-station speed
   is sparse; value Derived, confidence 0.4.
3. **Behavioral time-shares** (foraging/rest fractions) — mostly Inferred from
   ethogram reviews rather than per-species observation; flagged DRAFTED.
4. **Spectral appearance** — no per-species reflectance spectra used. Colors are
   ArtistAuthored (confidence ≤ 0.29) reconstructed from CC-licensed imagery,
   classified as image back-estimation, never measurement (규칙, A08).
5. **esca emission spectrum** for anglerfish — genus/family-level bioluminescence
   (~480 nm blue) applied; species-specific unmeasured (Inferred, 0.4).

## negative_search_log (queries that returned no usable primary datum)

| query | scope | result |
|---|---|---|
| "Melanocetus johnsonii" swimming kinematics tail-beat | OpenAlex/Crossref | no direct kinematic study found → transfer used |
| "Hippocampus kuda" reflectance spectrum nm | literature | no per-species spectrum → ArtistAuthored |
| "Clupea harengus" moment-arm jaw adductor | literature | not extracted for slice → actuator proxy only |

## Action

- Flag all confidence < 0.5 rows for red-team review (A16) before promotion to
  APPROVED.
- When a primary source is later added, update `evidence_class`, `source_id`,
  `confidence`, and set `review_status=APPROVED`; the preset compiler will pick
  up the change on rebuild (hash-based, §14).
