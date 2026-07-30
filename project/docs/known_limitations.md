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

4. **Shape metrics are internal consistency, not accuracy.** Silhouette IoU,
   proportion and landmark error are now measured (`docs/shape_report.md`) and
   all four taxa realise their preset proportions to <1 %. But with no digitised
   reference specimens there is nothing to score the LOD0 mesh against, so none
   of it is an accuracy claim about real fish.
5. **Single-axis loft.** The body is a lofted elliptical cross-section along one
   centerline. This approximates fusiform/pelagic/globiform bodies well but only
   crudely captures the seahorse's right-angled head and curled prehensile tail
   (a centerline curve stands in for posture). A multi-segment / L-system rig is
   the correct future model for extreme morphologies.
6. **Fins are parametric membranes,** not ray-by-ray articulated fin webs. Fin
   rays and pterygiophore linkages are represented at the joint level, not as
   individual geometry.
7. **Cranial four-bar / suction feeding** is represented as a single jaw DOF plus
   a feeding-mechanism tag, not a solved multi-link kinematic mechanism.

## Behavior / ecosystem

8. **Schooling NND validated in the cruising context only.** Undisturbed
   cruising schools reproduce the observed 0.3–1.2 BL band robustly (0.76–0.82
   across seeds). Under repeated predator attack the instantaneous NND is larger
   and noisier while the school scatters and re-forms — realistic, but not
   compared to a measured disturbed-school distribution here.
9. **Trophic web is role-based and small.** Four roles (planktivore, grazer,
   mesopredator, ambush_predator) over one shared plankton resource field.
   Recruitment now exists (`World.reproduction`, energy-gated with a logistic
   density brake), so a run is population dynamics rather than a one-way
   decline — a herring population started at 30 settles at its carrying
   capacity of 48 instead of only declining. It is off by default so the
   recorded validation runs stay comparable. Still absent: sex/pairing,
   seasonal spawning windows, larval stages, and age-structured mortality.
10. **Environment fields are coarse.** A single logistic plankton grid + scalar
   turbidity. Flow, thermal/oxygen stratification, diel/tidal cycles are modeled
   as preset envelopes but not yet as dynamic driving fields.
11. **LOD works and self-gates; the absolute budget is still unverified.**
    Mesh LOD cuts 59.9 % of triangles, and behaviour LOD gives **7.5×** at 271
    agents once the tiers engage (`docs/performance_report.md`).

    The thresholds are deliberately *not* rescaled to a small domain. They are
    perceptual — a fish 40 body lengths away covers few pixels, so demoting it
    is free — and squeezing the ladder to fit a 16 m tank would degrade animals
    the viewer can plainly see, which is the one thing LOD must not do. Instead
    the ladder measures whether it is paying: every ~3 s it probes what fraction
    of agents actually fall below standard tier and stays enabled only above
    10 %. In the dense 271-agent scenario only 2.2 % are demotable, so it
    switches itself off and avoids the ~27 % overhead it would otherwise cost;
    a viewer who pulls back re-enables it on the next probe.

    Still open: the absolute 16.6 ms budget on target hardware is unverified,
    because this environment has no GPU and Chromium falls back to software
    rendering — only relative comparisons are meaningful. No Unreal/Unity
    binding either.

## Portability

12. **Three profiles shipped (fish, bird, cnidarian).** The swap is proven
    across a genuine body-plan change: the cnidarian profile is radially
    symmetric with no skeleton, jaws, fins or spine, and retargets cleanly.
    Still unauthored: **colonial and modular** plans (siphonophores, corals,
    clonal plants), which need the slot vocabulary to describe repeated
    sub-individuals rather than one body — the schema reserves the symmetry
    types but nothing exercises them. Also, the profiles beyond fish are
    module-map level only: no presets, meshes or behaviour are authored for
    them, so portability is proven for the *contract*, not end-to-end
    generation.
