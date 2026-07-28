# Known Limitations (프롬프트 A16 / §17.14)

Honest scope boundaries of this reference build. "Looks plausible" is not
scientific validation (§15).

## Data

1. **Reference values, not live API pulls — and the live pull is blocked here.**
   The evidence ledger is seeded from canonical published literature and
   standard databases (see `sources/bibliography.bib`, `source_registry.yaml`).
   The ETL client now exists (`src/biogen/etl.py`, `./run.sh resolve-taxa`) with
   GBIF and WoRMS backends, on-disk caching, conflict reporting and 17 offline
   fixture tests. It has **not** been exercised against the live APIs: this
   environment's network policy denies those hosts (`CONNECT 403`), so
   `resolve-taxa` records `unresolved_network`, leaves the taxon index
   untouched, and exits non-zero. `taxonomy/resolution_report.json` is therefore
   a record of a *blocked* run, not a verified one — do not read it as
   confirmation of any name. To actually verify, run it from an environment
   whose egress policy permits `api.gbif.org` and `www.marinespecies.org`.
   All values remain graded by `evidence_class`; none are presented as freshly
   measured.
2. **Anglerfish (data-poor) is largely Inferred.** Swim mode, cruise speed and
   behavior for *Melanocetus johnsonii* are transferred/scaled with confidence
   ≤ 0.35 and `transfer_from_taxon_id` recorded. Treat as a structural
   placeholder demonstrating the inference path, not a measured model.
3. **Appearance is ArtistAuthored (≤ 0.29).** No per-species reflectance spectra
   were used; colors are back-estimated from CC imagery and flagged as such
   (규칙 A08). The material model exposes spectral fields for future measured data.

## Geometry / rig

4. **Single-axis loft.** The body is a lofted elliptical cross-section along one
   centerline. This approximates fusiform/pelagic/globiform bodies well but only
   crudely captures the seahorse's right-angled head and curled prehensile tail
   (a centerline curve stands in for posture). A multi-segment / L-system rig is
   the correct future model for extreme morphologies.
5. **Fins are parametric membranes,** not ray-by-ray articulated fin webs. Fin
   rays and pterygiophore linkages are represented at the joint level, not as
   individual geometry.
6. **Cranial four-bar / suction feeding** is represented as a single jaw DOF plus
   a feeding-mechanism tag, not a solved multi-link kinematic mechanism.

## Behavior / ecosystem

7. **Schooling NND validated in the cruising context only.** Undisturbed
   cruising schools reproduce the observed 0.3–1.2 BL band robustly (0.76–0.82
   across seeds). Under repeated predator attack the instantaneous NND is larger
   and noisier while the school scatters and re-forms — realistic, but not
   compared to a measured disturbed-school distribution here.
8. **Trophic web is role-based and small.** Four roles (planktivore, grazer,
   mesopredator, ambush_predator) over one shared plankton resource field. No
   reproduction/recruitment, so runs are bounded observation windows, not
   long-term population dynamics.
9. **Environment fields are coarse.** A single logistic plankton grid + scalar
   turbidity. Flow, thermal/oxygen stratification, diel/tidal cycles are modeled
   as preset envelopes but not yet as dynamic driving fields.
10. **Mesh LOD is measured; behavior LOD is not implemented in the browser build.**
    The distance policy runs end to end and is benchmarked
    (`project/tests/bench_lod.mjs`, `docs/performance_report.md`): −59.9 %
    triangles, 1.55× frame rate at 55 agents. Two things remain open. The
    absolute 16.6 ms budget is unverified because this environment has no GPU
    (Chromium falls back to software rendering), so only relative comparisons
    are meaningful. And past ~130 agents the workload becomes CPU-bound — mesh
    LOD stops helping frame time entirely — because the browser build runs full
    perception for every agent at every tick. The behavior LOD ladder specified
    in `lod.py` (reduced sensors → flocking-only → density aggregate) and a
    spatial index for the O(n²) neighbour query are the next performance work,
    not further geometry reduction. No Unreal/Unity binding either.

## Portability

11. **Two profiles shipped (fish, bird).** The swap is proven for these. Other
    body plans (radial, colonial, modular) have coordinate/rig strategies
    reserved in the schema but no authored profile yet.
