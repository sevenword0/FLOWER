"""Autonomous behavior (프롬프트 §10, A12).

Hierarchical selection = ethogram states scored by a Utility function over
normalized internal drives + sensory features, with minimum-dwell hysteresis so
state occupancy/transitions match observed distributions rather than random
flicker (규칙 13, §10.5). Each behavior references executable action primitives
(규칙 12) — steering + throttle are produced here and consumed by the
LocomotionController.

Behavior parameters (utility weights, drive dynamics, min dwell) are DATA from
the preset; this code is the shared behavior grammar (규칙 14: 종별 하드코딩 금지).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from .preset_compiler import get_param


DEFAULT_DRIVES = {"hunger": 0.3, "fear": 0.0, "fatigue": 0.1, "reproduction": 0.0}


@dataclass
class BehaviorController:
    behaviors: List[dict]
    drive_rates: Dict[str, float]
    min_dwell_s: float
    is_schooler: bool
    drives: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_DRIVES))
    current: Optional[str] = None
    dwell: float = 0.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0))

    @classmethod
    def from_preset(cls, resolved: dict, seed: int = 0) -> "BehaviorController":
        beh = get_param(resolved, "behavior.ethogram") or []
        rates = get_param(resolved, "behavior.drive_rates") or {
            "hunger": 0.02, "fatigue": 0.015, "fear_decay": 0.25, "reproduction": 0.001,
        }
        dwell = float(get_param(resolved, "behavior.min_dwell_s", 1.5))
        schooler = bool(get_param(resolved, "behavior.obligate_schooler", False))
        return cls(behaviors=beh, drive_rates=rates, min_dwell_s=dwell,
                   is_schooler=schooler, rng=np.random.default_rng(seed))

    # --- drive dynamics ----------------------------------------------------
    def update_drives(self, dt: float, features: Dict[str, float]) -> None:
        d = self.drives
        d["hunger"] = min(1.0, d["hunger"] + self.drive_rates.get("hunger", 0.02) * dt)
        d["fatigue"] = min(1.0, max(0.0, d["fatigue"]
                            + (self.drive_rates.get("fatigue", 0.015)
                               * (0.5 + features.get("effort", 0.0)) - 0.02) * dt))
        # fear driven by predator proximity, decays otherwise
        if features.get("predator_visible", 0.0) > 0.5:
            d["fear"] = min(1.0, d["fear"] + 2.0 * dt)
        else:
            d["fear"] = max(0.0, d["fear"] - self.drive_rates.get("fear_decay", 0.25) * dt)
        d["reproduction"] = min(1.0, d["reproduction"]
                                + self.drive_rates.get("reproduction", 0.001) * dt)

    def _feature_vector(self, features: Dict[str, float]) -> Dict[str, float]:
        f = dict(features)
        f.update(self.drives)
        f.setdefault("bias", 1.0)
        return f

    def _score(self, behavior: dict, feats: Dict[str, float]) -> float:
        w = behavior.get("utility", {})
        return float(sum(v * feats.get(k, 0.0) for k, v in w.items()))

    def select(self, dt: float, features: Dict[str, float]) -> dict:
        """Update drives, score behaviors, apply hysteresis, return command."""
        self.update_drives(dt, features)
        feats = self._feature_vector(features)

        if not self.behaviors:
            return {"behavior_id": "idle", "throttle": 0.0, "steer": "hold"}

        scores = [(self._score(b, feats), b) for b in self.behaviors]
        scores.sort(key=lambda t: t[0], reverse=True)
        best_score, best = scores[0]

        self.dwell += dt
        if self.current is not None and self.dwell < self.min_dwell_s:
            # keep current unless a high-salience override (fear) fires
            cur = next((b for b in self.behaviors if b["behavior_id"] == self.current), best)
            if not (feats.get("fear", 0) > 0.6 and best["behavior_id"] != self.current):
                best = cur
                best_score = self._score(cur, feats)

        if best["behavior_id"] != self.current:
            self.current = best["behavior_id"]
            self.dwell = 0.0

        # discharge drives on satisfying behaviors
        label = best.get("label", best["behavior_id"])
        if "forag" in label or "feed" in label:
            if features.get("prey_adjacent", 0.0) > 0.5:
                self.drives["hunger"] = max(0.0, self.drives["hunger"] - 0.5)
        if "rest" in label:
            self.drives["fatigue"] = max(0.0, self.drives["fatigue"] - 0.3 * dt)

        throttle = float(best.get("throttle", 0.3))
        return {
            "behavior_id": best["behavior_id"],
            "label": label,
            "throttle": throttle,
            "steer": best.get("steer", "wander"),
            "score": best_score,
            "action_primitive_ids": best.get("action_primitive_ids", []),
        }
