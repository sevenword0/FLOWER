# Known Limitations (프롬프트 A16 / §17.14)

Honest scope boundaries of this reference build. "Looks plausible" is not
scientific validation (§15).

## Data

1. **Reference values, not live API pulls.** The evidence ledger is seeded from
   canonical published literature and standard databases (see
   `sources/bibliography.bib`, `source_registry.yaml`). The API endpoints are
   documented and routed, but the ETL clients that fetch live data are a
   next-step deliverable, not exercised here. All values are graded by
   `evidence_class`; none are presented as freshly measured.
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
10. **No GPU/real-time engine binding.** LOD tiers and budgets are defined and
    the mesh/rig/material export cleanly, but a live Unreal/Unity build is out of
    scope for this environment.

## Portability

11. **Two profiles shipped (fish, bird).** The swap is proven for these. Other
    body plans (radial, colonial, modular) have coordinate/rig strategies
    reserved in the schema but no authored profile yet.
