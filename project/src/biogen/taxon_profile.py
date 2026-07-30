"""TaxonProfile: resolves config/target_taxon.yaml -> adaptation profile and
builds the TAXON_ADAPTATION_MAP + functional module map + source routing.

This is the mechanism behind the "one-word swap" (프롬프트 §2, §27, Gate G0/G9):
change only `target_taxon` in the config and everything downstream regenerates.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import yaml

from . import paths

# Which multi-agent roles (A00–A16) own which functional slot. Taxon-agnostic:
# slots are the stable interface; their *realization* comes from the profile.
SLOT_TO_AGENTS: Dict[str, List[str]] = {
    "1_identity_lifecycle": ["A01"],
    "2_structural_support": ["A04", "A10"],
    "3_joints_linkages": ["A04", "A10"],
    "4_feeding_capture": ["A04", "A05"],
    "5_actuation": ["A05", "A11"],
    "6_locomotion_structures": ["A06", "A10", "A11"],
    "7_core_physiology": ["A03", "A13"],
    "8_surface_covering": ["A07", "A08"],
    "9_head_sensors_silhouette": ["A09"],
    "10_optics_pattern": ["A08"],
    "11_behavior_movement": ["A12"],
    "12_ecology_interactions": ["A13"],
    "13_variation": ["A06", "A12"],
}

# Which source-routing bucket feeds which slot.
SLOT_TO_SOURCE_BUCKET: Dict[str, List[str]] = {
    "1_identity_lifecycle": ["taxonomy_authority"],
    "2_structural_support": ["morphometry_specimen", "literature"],
    "3_joints_linkages": ["morphometry_specimen", "literature"],
    "4_feeding_capture": ["literature"],
    "5_actuation": ["literature"],
    "6_locomotion_structures": ["morphometry_specimen", "literature"],
    "7_core_physiology": ["literature", "occurrence_behavior"],
    "8_surface_covering": ["morphometry_specimen", "media"],
    "9_head_sensors_silhouette": ["literature", "morphometry_specimen"],
    "10_optics_pattern": ["media", "literature"],
    "11_behavior_movement": ["occurrence_behavior", "literature"],
    "12_ecology_interactions": ["occurrence_behavior", "literature"],
    "13_variation": ["morphometry_specimen", "occurrence_behavior"],
}


def _load_yaml(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class TaxonProfile:
    target_taxon: str
    profile_key: str
    profile: Dict[str, Any]
    config: Dict[str, Any]
    adaptation_map: Dict[str, Any] = field(default_factory=dict)

    # --- accessors used across the pipeline -------------------------------
    @property
    def display_name(self) -> str:
        return self.profile.get("display_name", self.target_taxon)

    @property
    def symmetry_type(self) -> str:
        return self.profile["body_plan"]["symmetry_type"]

    @property
    def rig_strategy(self) -> str:
        return self.profile["body_plan"]["rig_strategy"]

    @property
    def morphotypes(self) -> Dict[str, Any]:
        return self.profile.get("morphotypes", {})

    @property
    def vertical_slice(self) -> List[str]:
        return self.config.get("vertical_slice", [])

    def source_routing(self) -> Dict[str, Any]:
        return self.profile.get("source_routing", {})

    def build_adaptation_map(self) -> Dict[str, Any]:
        """TAXON_ADAPTATION_MAP: functional slot -> realized structures +
        responsible agents + source routes. Regenerates per profile."""
        slots = self.profile["functional_slots"]
        routing = self.source_routing()
        amap: Dict[str, Any] = {
            "target_taxon": self.target_taxon,
            "profile_key": self.profile_key,
            "symmetry_type": self.symmetry_type,
            "rig_strategy": self.rig_strategy,
            "slots": {},
        }
        for slot_key, realized in slots.items():
            buckets = SLOT_TO_SOURCE_BUCKET.get(slot_key, [])
            routes = []
            for b in buckets:
                for src in routing.get(b, []):
                    routes.append({"bucket": b, **src})
            amap["slots"][slot_key] = {
                "realized_structures": realized,
                "responsible_agents": SLOT_TO_AGENTS.get(slot_key, []),
                **_na_analysis(realized),
                "source_routes": routes,
            }
        self.adaptation_map = amap
        return amap

    def functional_module_map(self) -> Dict[str, Any]:
        """Compact module map for docs/ontology output."""
        amap = self.adaptation_map or self.build_adaptation_map()
        return {
            "target_taxon": self.target_taxon,
            "profile_key": self.profile_key,
            "rig_strategy": self.rig_strategy,
            "symmetry_type": self.symmetry_type,
            "modules": {
                slot: {
                    "agents": info["responsible_agents"],
                    "source_buckets": sorted({r["bucket"] for r in info["source_routes"]}),
                    "na": info["na"],
                    "na_substructures": info["na_substructures"],
                }
                for slot, info in amap["slots"].items()
            },
        }


def _na_analysis(realized: Any) -> Dict[str, Any]:
    """Separate "this slot does not exist for this clade" from "one sub-structure
    of it does not exist" (규칙: 없으면 N/A + 기능 대응 구조로 교체).

    The distinction matters and conflating them loses information. A radially
    symmetric predator may have no jaws while its feeding slot is very much
    present, realized by tentacles and stinging cells. An air-breathing flier
    may have no swim bladder while its physiology slot is present, with air sacs
    doing the equivalent job. Marking either slot simply "N/A" would assert that
    the animal does not feed, or does not breathe.

    So `na` means the whole slot is absent, and `na_substructures` names the
    individual features that are absent while the slot itself is re-realized.
    """
    if not isinstance(realized, dict):
        return {"na": str(realized).upper() == "N/A", "na_substructures": []}

    absent = [k for k, v in realized.items() if str(v).upper() == "N/A"]
    present = [k for k, v in realized.items()
               if str(v).upper() != "N/A" and not k.startswith(("note", "_"))]
    return {
        "na": not present,                     # nothing realizes this slot at all
        "na_substructures": sorted(absent),    # re-realized, minus these features
    }


def load_profile(config_path=None) -> TaxonProfile:
    cfg_path = config_path or (paths.CONFIG / "target_taxon.yaml")
    config = _load_yaml(cfg_path)
    target = config["target_taxon"]

    # Resolve profile key: explicit override -> alias table -> identity.
    key = config.get("adaptation_profile")
    if not key:
        aliases = config.get("profile_aliases", {})
        key = aliases.get(target)
    if not key:
        raise ValueError(
            f"Cannot resolve adaptation profile for target_taxon={target!r}. "
            f"Add it to profile_aliases or set adaptation_profile in the config."
        )

    prof_path = paths.ADAPTATION_PROFILES / f"{key}.yaml"
    if not prof_path.exists():
        raise FileNotFoundError(
            f"Adaptation profile '{key}' not found at {prof_path}. "
            f"Create it to support target_taxon={target!r}."
        )
    profile = _load_yaml(prof_path)
    tp = TaxonProfile(target_taxon=target, profile_key=key, profile=profile, config=config)
    tp.build_adaptation_map()
    return tp
