"""LOD selection (프롬프트 §10 행동 LOD, §14, A15).

Maps distance-to-camera / importance to a tier that controls mesh LOD, behavior
fidelity and tick rate. Far-field agents collapse to density/biomass aggregates
rather than individuals (규칙: 보이지 않는 지역은 통계 상태).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import yaml
from . import paths

TIER_ORDER = ["hero", "standard", "crowd", "far_field"]


@dataclass
class LODPolicy:
    tiers: Dict[str, dict]
    # distance thresholds in body lengths (from camera)
    hero_bl: float = 10.0
    standard_bl: float = 40.0
    crowd_bl: float = 150.0

    @classmethod
    def load(cls) -> "LODPolicy":
        with open(paths.CONFIG / "performance_budget.yaml", "r", encoding="utf-8") as fh:
            budget = yaml.safe_load(fh)
        return cls(tiers=budget.get("lod_tiers", {}))

    def tier_for(self, distance_bl: float, important: bool = False) -> str:
        if important or distance_bl <= self.hero_bl:
            return "hero"
        if distance_bl <= self.standard_bl:
            return "standard"
        if distance_bl <= self.crowd_bl:
            return "crowd"
        return "far_field"

    def mesh_lod(self, tier: str) -> int:
        return int(self.tiers.get(tier, {}).get("mesh_lod", 0))

    def tick_hz(self, tier: str) -> int:
        return int(self.tiers.get(tier, {}).get("tick_hz", 30))
