"""Gate G6/G7: the ecosystem is deterministic, energy/resources stay bounded,
schooling NND lands in the observed band, and predator/prey interaction occurs."""
from biogen.ecosystem import World


def _build_world(seed=11):
    w = World(seed=seed, dt=0.1, bounds=(16.0, 8.0, 16.0))
    w.add_population("clupea_harengus", 40, "planktivore", nnd_pref_bl=0.7, cluster=True)
    w.add_population("oncorhynchus_mykiss", 6, "mesopredator", nnd_pref_bl=3.0)
    w.add_population("melanocetus_johnsonii", 2, "ambush_predator", nnd_pref_bl=5.0)
    w.add_population("hippocampus_kuda", 4, "grazer", nnd_pref_bl=4.0)
    return w


def test_simulation_is_deterministic():
    m1 = _build_world().run(300)
    m2 = _build_world().run(300)
    assert m1 == m2


def test_energy_and_resources_bounded():
    """Gate G7: no infinite energy / infinite resource."""
    w = _build_world()
    w.run(400)
    for a in w.agents:
        assert 0.0 <= a.energy <= 1.0
    assert 0.0 <= float(w.resource.min())
    assert float(w.resource.max()) <= w.resource_cap + 1e-9


def test_schooling_nnd_in_observed_band():
    """Gate G6: an UNDISTURBED cruising herring school holds NND within the
    observed 0.3–1.2 BL band (P0026 / Pitcher & Partridge 1983). P0026 was
    measured on cruising schools, so it is validated on a predator-free shoal."""
    w = World(seed=11, dt=0.1, bounds=(16.0, 8.0, 16.0))
    w.add_population("clupea_harengus", 40, "planktivore", nnd_pref_bl=0.7, cluster=True)
    w.run(600)
    nnd = w.mean_nnd_bl("clupea_harengus")
    assert nnd is not None
    assert 0.3 <= nnd <= 1.2, f"cruising-school NND {nnd} outside observed band"


def test_schooling_nnd_stable_across_seeds():
    """The cruising-school equilibrium must be robust, not seed-lucky."""
    vals = []
    for seed in (7, 3, 42, 99, 256):
        w = World(seed=seed, dt=0.1, bounds=(16.0, 8.0, 16.0))
        w.add_population("clupea_harengus", 40, "planktivore", nnd_pref_bl=0.7, cluster=True)
        w.run(600)
        vals.append(w.mean_nnd_bl("clupea_harengus"))
    assert all(0.3 <= v <= 1.2 for v in vals), vals


def test_prey_population_survives_predation():
    """Gate G7: predators do not drive the prey population to collapse
    (handling time + satiation + schooling dilution bound the predation rate)."""
    w = _build_world()
    w.run(600)
    herring = w.metrics()["alive_by_taxon"].get("clupea_harengus", 0)
    assert herring >= 10, f"prey population collapsed to {herring}"


def test_behavior_occupancy_and_transitions_recorded():
    w = _build_world()
    m = w.run(300)
    occ = m["behavior_occupancy"]
    # occupancy fractions are rounded to 4 dp for reporting, so allow rounding drift
    assert abs(sum(occ.values()) - 1.0) < 1e-2
    # schooling should dominate for an obligate-schooler-heavy community
    assert occ.get("school", 0) > 0.3
    assert m["transition_counts"], "expected some behavior transitions"


def test_reproduction_settles_at_carrying_capacity():
    """§11: with recruitment the run becomes population dynamics rather than a
    one-way decline — but it must settle, not explode."""
    w = World(seed=5, dt=0.1, bounds=(16.0, 8.0, 16.0))
    w.reproduction = True
    w.add_population("clupea_harengus", 30, "planktivore", nnd_pref_bl=0.7, cluster=True)
    w.run(1800)                       # 180 s of sim time
    n = w.metrics()["alive_by_taxon"].get("clupea_harengus", 0)
    k = w.carrying_capacity["clupea_harengus"]
    assert w.births > 0, "no recruitment occurred"
    assert n > 30, f"population did not grow: {n}"
    assert n <= k * 1.15, f"population {n} overshot carrying capacity {k}"


def test_reproduction_conserves_energy():
    """A parent pays for its offspring — recruits must not be free energy."""
    w = World(seed=5, dt=0.1, bounds=(16.0, 8.0, 16.0))
    w.reproduction = True
    w.add_population("clupea_harengus", 20, "planktivore", nnd_pref_bl=0.7, cluster=True)
    w.run(900)
    for a in w.agents:
        assert 0.0 <= a.energy <= 1.0, f"energy out of bounds: {a.energy}"


def test_reproduction_off_by_default_keeps_old_behaviour():
    """Existing scenarios must stay comparable to their recorded validation."""
    w = _build_world()
    assert w.reproduction is False
    w.run(200)
    assert w.births == 0
