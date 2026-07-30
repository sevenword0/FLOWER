"""Locomotion primitives (프롬프트 §10, A11).

Low-level motion is a per-swim-mode oscillator that maps a throttle command
(0..1) to a forward speed and a body/fin kinematic waveform, which in turn
drives the rig joints. Behavior selects primitives; primitives drive actuators
(규칙 12: 행동 → 이동 프리미티브 → 관절·작동기 연결 유지).

Speed/frequency scaling follows the classic tail-beat relation (Bainbridge
1958; Videler & Wardle 1991): stride length is roughly constant in body lengths,
so U(BL/s) ~ k * f, i.e. f ~ U/k. Values come from the evidence ledger via the
preset, never hard-coded per species.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .preset_compiler import get_param

# Median/paired-fin propulsors don't beat the caudal fin; they oscillate a
# median fin at high frequency and low amplitude.
MPF_MODES = {"labriform", "dorsal_undulation", "rajiform", "gymnotiform",
             "amiiform", "tetraodontiform"}


@dataclass
class LocomotionController:
    swim_mode: str
    body_length_m: float
    cruise_speed_bl: float
    burst_speed_bl: float
    tailbeat_freq_cruise: float
    stride_bl: float          # distance per beat in body lengths
    is_mpf: bool
    phase: float = 0.0

    @classmethod
    def from_preset(cls, resolved: dict) -> "LocomotionController":
        mode = get_param(resolved, "locomotion.swim_mode", "subcarangiform")
        L = float(get_param(resolved, "morphometrics.reference_length_m", 0.2))
        cruise = float(get_param(resolved, "locomotion.cruise_speed_bl", 1.5))
        burst = float(get_param(resolved, "locomotion.burst_speed_bl", max(cruise * 3, 4.0)))
        f_cruise = float(get_param(resolved, "locomotion.tailbeat_freq_cruise", 3.0))
        # stride length (BL/beat): U_bl = stride * f  ->  stride = U/f
        stride = cruise / f_cruise if f_cruise > 1e-6 else 0.6
        return cls(
            swim_mode=mode, body_length_m=L, cruise_speed_bl=cruise,
            burst_speed_bl=burst, tailbeat_freq_cruise=f_cruise,
            stride_bl=stride, is_mpf=mode in MPF_MODES,
        )

    def speed_bl(self, throttle: float) -> float:
        """Throttle 0..1 maps cruise..burst (clamped)."""
        t = min(max(throttle, 0.0), 1.0)
        return self.cruise_speed_bl + (self.burst_speed_bl - self.cruise_speed_bl) * t

    def speed_ms(self, throttle: float) -> float:
        return self.speed_bl(throttle) * self.body_length_m

    def beat_frequency(self, throttle: float) -> float:
        """Beat frequency from speed via constant-stride relation."""
        u = self.speed_bl(throttle)
        if self.is_mpf:
            # MPF: high base frequency, weakly speed-dependent
            return self.tailbeat_freq_cruise * (0.8 + 0.4 * min(throttle, 1.0))
        return max(u / self.stride_bl, 0.1)

    def step(self, dt: float, throttle: float) -> dict:
        """Advance the oscillator by dt seconds. Returns kinematic state that a
        rig evaluator turns into joint angles."""
        f = self.beat_frequency(throttle)
        self.phase = (self.phase + 2.0 * math.pi * f * dt) % (2.0 * math.pi)
        # Body-wave amplitude envelope: BCF grows toward the tail; MPF is a
        # localized median-fin wave (near-zero body bending).
        if self.is_mpf:
            body_amp = 0.02
            fin_amp = 0.8
        else:
            body_amp = 0.12 + 0.10 * min(throttle, 1.0)  # rad, peak tail bend
            fin_amp = 0.1
        return {
            "speed_ms": self.speed_ms(throttle),
            "beat_frequency_hz": f,
            "phase": self.phase,
            "body_bend_amplitude_rad": body_amp,
            "fin_amplitude_norm": fin_amp,
            "lateral_offset": body_amp * math.sin(self.phase),
        }

    def spine_curvature(self, n_joints: int, kin: dict) -> list:
        """Traveling-wave curvature along the spine for a rig with n_joints.
        Amplitude increases posteriorly for BCF swimmers."""
        amp = kin["body_bend_amplitude_rad"]
        phase = kin["phase"]
        wavelength = 1.0  # body lengths per wave (approx)
        out = []
        for i in range(n_joints):
            s = i / max(n_joints - 1, 1)
            envelope = s ** 1.5 if not self.is_mpf else (0.05 + 0.0 * s)
            out.append(amp * envelope * math.sin(phase - 2.0 * math.pi * s / wavelength))
        return out
