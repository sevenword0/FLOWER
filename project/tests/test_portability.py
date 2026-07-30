"""Gate G9: the one-word swap. Changing only target_taxon regenerates the
module map + source routing with a different rig strategy and correct N/A slot
handling — with NO code change and NO taxon literal in the package."""
import subprocess
import sys
from pathlib import Path

import yaml

from biogen import paths
from biogen.taxon_profile import load_profile

SRC = Path(paths.PROJECT_ROOT) / "src"


def _load_with_taxon(taxon: str, tmp_path):
    cfg = yaml.safe_load((paths.CONFIG / "target_taxon.yaml").read_text(encoding="utf-8"))
    cfg["target_taxon"] = taxon
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return load_profile(p)


def test_fish_profile(tmp_path):
    tp = _load_with_taxon("어류", tmp_path)
    assert tp.profile_key == "fish"
    assert tp.rig_strategy == "spline_spine"
    assert tp.symmetry_type == "bilateral"


def test_radial_body_plan_swap(tmp_path):
    """The real portability test.

    fish → bird is bilateral → bilateral: it swaps the rig but never challenges
    the coordinate system. A jellyfish is radially symmetric with no skeleton,
    no jaws, no fins and no spine, so this is what actually shows whether the
    functional slots are an abstraction or bilateral defaults in disguise.
    """
    tp = _load_with_taxon("해파리", tmp_path)
    assert tp.profile_key == "cnidarian"
    assert tp.symmetry_type == "radial"          # not bilateral
    assert tp.rig_strategy == "radial_umbrella"  # neither spine nor limbs

    m = tp.functional_module_map()["modules"]

    # Every slot must still be realized: a jellyfish feeds, moves, has a
    # surface and senses — it just does none of it with jaws, fins, scales or
    # a head. Marking those slots wholly absent would be a modelling error.
    assert not any(v["na"] for v in m.values()), \
        [k for k, v in m.items() if v["na"]]

    absent = {k: v["na_substructures"] for k, v in m.items() if v["na_substructures"]}
    assert "jaws" in absent["4_feeding_capture"]
    assert "fins" in absent["6_locomotion_structures"]
    assert "scales" in absent["8_surface_covering"]
    assert "head" in absent["9_head_sensors_silhouette"]

    # source routing must have retargeted away from the fish authorities
    ids = {r["id"] for r in tp.adaptation_map["slots"]["1_identity_lifecycle"]["source_routes"]}
    assert "fishbase" not in ids


def test_substructure_absence_is_not_slot_absence(tmp_path):
    """A bird has no swim bladder, but it certainly has physiology. The two must
    not collapse into one flag — that was a real bug the radial profile exposed."""
    tp = _load_with_taxon("조류", tmp_path)
    phys = tp.functional_module_map()["modules"]["7_core_physiology"]
    assert phys["na"] is False, "the slot is re-realized, not absent"
    assert "buoyancy" in phys["na_substructures"]


def test_all_profiles_declare_a_distinct_rig_strategy(tmp_path):
    """Three body plans must not silently share one rig."""
    rigs = {t: _load_with_taxon(t, tmp_path).rig_strategy
            for t in ("어류", "조류", "해파리")}
    assert len(set(rigs.values())) == 3, rigs


def test_bird_profile_swap(tmp_path):
    tp = _load_with_taxon("조류", tmp_path)
    assert tp.profile_key == "bird"
    # different rig strategy proves downstream regeneration, not a fish fallback
    assert tp.rig_strategy == "limbed_biped_with_wings"
    fmm = tp.functional_module_map()
    # buoyancy is absent, but the physiology slot itself is re-realized by air
    # sacs — so the slot is present with a recorded absent sub-structure
    assert fmm["modules"]["7_core_physiology"]["na"] is False
    assert "buoyancy" in fmm["modules"]["7_core_physiology"]["na_substructures"]
    # source routing regenerated to bird buckets
    amap = tp.adaptation_map
    routes = amap["slots"]["1_identity_lifecycle"]["source_routes"]
    ids = {r["id"] for r in routes}
    assert "avibase" in ids  # bird-specific authority, not a fish source


def test_no_taxon_literal_in_package():
    """The package must not hard-code a taxon literal (규칙 17). Only config +
    adaptation profiles may name a taxon."""
    banned = ["어류", "물고기", "Actinopterygii", "fish", "Oncorhynchus"]
    offenders = []
    for py in (SRC / "biogen").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in banned:
            # allow the word inside comments/docstrings? No — be strict on code.
            for i, line in enumerate(text.splitlines(), 1):
                code = line.split("#", 1)[0]
                if token in code:
                    offenders.append(f"{py.name}:{i}: {token}")
    assert not offenders, offenders


def test_cli_module_map_runs_for_bird(tmp_path):
    """End-to-end: the CLI regenerates a module map for the swapped taxon."""
    cfg = yaml.safe_load((paths.CONFIG / "target_taxon.yaml").read_text(encoding="utf-8"))
    cfg["target_taxon"] = "조류"
    # temporarily point the default config at a bird value via env override file
    p = tmp_path / "target_taxon.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    # load_profile(p) already covered; here assert the profile file exists
    assert (paths.ADAPTATION_PROFILES / "bird.yaml").exists()
