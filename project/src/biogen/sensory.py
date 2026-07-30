"""Sensory model (프롬프트 A09, §10). Separates real sensory capability from a
runtime detection proxy (규칙: 실제 감각 능력과 게임용 감지 반경 분리)."""
from __future__ import annotations
from dataclasses import dataclass
import math
from .preset_compiler import get_param


@dataclass
class SensoryModel:
    vision_range_m: float
    vision_fov_rad: float
    lateral_line_range_m: float   # near-field flow sensing (fish-specific slot)
    body_length_m: float

    @classmethod
    def from_preset(cls, resolved: dict) -> "SensoryModel":
        L = float(get_param(resolved, "morphometrics.reference_length_m", 0.2))
        vr = float(get_param(resolved, "sensory_system.vision_range_bl", 8.0)) * L
        fov = float(get_param(resolved, "sensory_system.vision_fov_deg", 300.0)) * math.pi / 180.0
        ll = float(get_param(resolved, "sensory_system.lateral_line_range_bl", 1.0)) * L
        return cls(vision_range_m=vr, vision_fov_rad=fov, lateral_line_range_m=ll, body_length_m=L)

    def detects(self, self_pos, self_heading, other_pos, turbidity: float = 0.0) -> bool:
        """Detection = within (turbidity-attenuated) vision cone, OR within the
        omnidirectional lateral-line near field."""
        dx = other_pos[0] - self_pos[0]
        dy = other_pos[1] - self_pos[1]
        dz = other_pos[2] - self_pos[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist <= self.lateral_line_range_m:
            return True
        eff_range = self.vision_range_m * (1.0 - min(max(turbidity, 0.0), 0.95))
        if dist > eff_range or dist < 1e-9:
            return False
        # heading is a unit vector; check angle
        hx, hy, hz = self_heading
        cosang = (dx * hx + dy * hy + dz * hz) / dist
        cosang = min(max(cosang, -1.0), 1.0)
        return math.acos(cosang) <= self.vision_fov_rad * 0.5
