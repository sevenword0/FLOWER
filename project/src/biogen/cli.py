"""biogen command-line interface.

Usage:
    python -m biogen.cli module-map            # regenerate functional module map
    python -m biogen.cli adaptation-map        # print TAXON_ADAPTATION_MAP
    python -m biogen.cli compile <taxon_id>    # resolve + print a preset
    python -m biogen.cli generate <taxon_id>   # mesh/rig/material to exports/
    python -m biogen.cli validate [taxon_id]   # schema + biomech + evidence audit
    python -m biogen.cli simulate              # run the ecosystem vertical slice
    python -m biogen.cli resolve-taxa          # verify names against GBIF + WoRMS (needs network)
    python -m biogen.cli build-all             # generate + validate the whole slice

The active taxon comes ONLY from config/target_taxon.yaml.
"""
from __future__ import annotations
import json
import sys
import yaml

from . import paths
from .taxon_profile import load_profile
from .preset_compiler import compile_preset
from .geometry import generate_all
from .validate import validate_taxon, audit_evidence_ledger


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_module_map(_args):
    tp = load_profile()
    fmm = tp.functional_module_map()
    out = paths.ONTOLOGY / "functional_module_map.yaml"
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(fmm, fh, allow_unicode=True, sort_keys=False)
    print(f"# target_taxon={tp.target_taxon} profile={tp.profile_key} "
          f"rig={tp.rig_strategy} symmetry={tp.symmetry_type}")
    print(f"# wrote {out}")
    _print(fmm)


def cmd_adaptation_map(_args):
    tp = load_profile()
    _print(tp.adaptation_map)


def cmd_compile(args):
    taxon_id = args[0]
    _print(compile_preset(taxon_id, seed=1))


def cmd_generate(args):
    taxon_id = args[0]
    resolved = compile_preset(taxon_id, seed=1)
    written = generate_all(resolved, taxon_id)
    print(f"generated for {taxon_id} (build_hash={resolved['provenance']['build_hash'][:12]}):")
    _print(written)


def cmd_validate(args):
    tp = load_profile()
    targets = args if args else tp.vertical_slice
    results = [validate_taxon(t) for t in targets]
    audit = audit_evidence_ledger()
    ok = all(r["ok"] for r in results) and not audit["problems"]
    _print({"validate": results, "evidence_audit": audit, "all_ok": ok})
    return 0 if ok else 1


def cmd_simulate(args):
    """Run an ecosystem scenario. Scenario composition (taxon ids, roles, counts)
    is DATA loaded from ecosystem/scenarios/<name>.yaml — no taxon literal in code."""
    from .ecosystem import World
    scenario_name = args[0] if args else "vertical_slice"
    spath = paths.PROJECT_ROOT / "ecosystem" / "scenarios" / f"{scenario_name}.yaml"
    with open(spath, "r", encoding="utf-8") as fh:
        scn = yaml.safe_load(fh)
    w = scn.get("world", {})
    world = World(seed=w.get("seed", 11), dt=w.get("dt", 0.1),
                  bounds=tuple(w.get("bounds_m", (16.0, 8.0, 16.0))),
                  turbidity=w.get("turbidity", 0.1),
                  resource_regrow=w.get("resource_regrow", 0.05))
    for pop in scn.get("populations", []):
        world.add_population(pop["taxon_id"], pop["count"], pop["role"],
                             nnd_pref_bl=pop.get("nnd_pref_bl", 0.7),
                             cluster=pop.get("cluster", False))
    mcfg = scn.get("metrics", {})
    metrics = world.run(mcfg.get("steps", 600))
    schooler = mcfg.get("schooler_taxon_id")
    if schooler:
        metrics["mean_nnd_bl_schooler"] = world.mean_nnd_bl(schooler)
    _print(metrics)


def cmd_resolve_taxa(args):
    """Resolve accepted names + identifiers against GBIF and WoRMS.

    Writes taxonomy/resolution_report.json. Nothing in the taxon index is
    mutated automatically: disagreements are reported for review (규칙 8).
    Exit code 1 when no authority was reachable, so a blocked run cannot be
    mistaken for a verified one in CI.
    """
    from .etl import resolve_index
    rep = resolve_index(use_cache="--no-cache" not in args)
    _print({k: rep[k] for k in ("generated_at", "network_reachable",
                                "verdict_counts", "requires_review")
            if k in rep})
    print(f"# wrote {rep['_path']}")
    if not rep["network_reachable"]:
        print("# NOT VERIFIED: no taxonomic authority was reachable from this "
              "environment. The taxon index was left unchanged.")
        return 1
    return 0


def cmd_build_all(_args):
    tp = load_profile()
    cmd_module_map(None)
    summary = {}
    for tid in tp.vertical_slice:
        resolved = compile_preset(tid, seed=1)
        generate_all(resolved, tid)
        summary[tid] = validate_taxon(tid)
    _print({"build_all": summary})


COMMANDS = {
    "module-map": cmd_module_map,
    "adaptation-map": cmd_adaptation_map,
    "compile": cmd_compile,
    "generate": cmd_generate,
    "validate": cmd_validate,
    "simulate": cmd_simulate,
    "resolve-taxa": cmd_resolve_taxa,
    "build-all": cmd_build_all,
}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:]) or 0


if __name__ == "__main__":
    raise SystemExit(main())
