"""Gate G6: locomotion primitives obey biomechanical limits and connect to the
rig (규칙 12: 행동 → 이동 프리미티브 → 관절)."""
import math
from biogen.preset_compiler import compile_preset
from biogen.locomotion import LocomotionController


def test_speed_within_cruise_burst_band():
    r = compile_preset("oncorhynchus_mykiss", seed=1)
    lc = LocomotionController.from_preset(r)
    assert lc.speed_bl(0.0) == lc.cruise_speed_bl
    assert math.isclose(lc.speed_bl(1.0), lc.burst_speed_bl)
    assert lc.cruise_speed_bl <= lc.speed_bl(0.5) <= lc.burst_speed_bl


def test_beat_frequency_positive_and_scales():
    r = compile_preset("oncorhynchus_mykiss", seed=1)
    lc = LocomotionController.from_preset(r)
    f_slow = lc.beat_frequency(0.0)
    f_fast = lc.beat_frequency(1.0)
    assert f_slow > 0
    assert f_fast > f_slow  # faster swimming -> higher tail-beat frequency


def test_mpf_swimmer_has_low_body_bending():
    """Seahorse (dorsal-fin/MPF) should barely bend its body vs a BCF swimmer."""
    seahorse = LocomotionController.from_preset(compile_preset("hippocampus_kuda", seed=1))
    trout = LocomotionController.from_preset(compile_preset("oncorhynchus_mykiss", seed=1))
    assert seahorse.is_mpf
    assert not trout.is_mpf
    kin_s = seahorse.step(0.1, 0.5)
    kin_t = trout.step(0.1, 0.5)
    assert kin_s["body_bend_amplitude_rad"] < kin_t["body_bend_amplitude_rad"]


def test_spine_curvature_grows_posteriorly_for_bcf():
    r = compile_preset("oncorhynchus_mykiss", seed=1)
    lc = LocomotionController.from_preset(r)
    kin = lc.step(0.1, 0.5)
    curv = [abs(c) for c in lc.spine_curvature(8, kin)]
    # posterior joints bend more than anterior ones (traveling wave envelope)
    assert max(curv[5:]) >= max(curv[:3])
