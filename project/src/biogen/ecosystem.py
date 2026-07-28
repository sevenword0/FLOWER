"""Virtual ecosystem (프롬프트 §11, Stage 7, A13).

Agents read environment fields and each other, select behavior, drive their
locomotion oscillator, and move. Interactions are bidirectional: planktivores
deplete a finite resource field that regrows logistically; predators consume
prey; schoolers self-organize. Nothing has infinite energy or infinite resources
(Gate G7). The whole simulation is deterministic given a seed (trajectory
regression, Gate G6/G8).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import numpy as np

from .preset_compiler import compile_preset, get_param
from .locomotion import LocomotionController
from .behavior import BehaviorController
from .sensory import SensoryModel


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])


@dataclass
class Agent:
    aid: int
    taxon_id: str
    role: str                       # planktivore | mesopredator | ambush_predator
    resolved: dict
    loco: LocomotionController
    behavior: BehaviorController
    sensory: SensoryModel
    pos: np.ndarray
    heading: np.ndarray
    energy: float = 1.0
    alive: bool = True
    turn_rate: float = 2.0          # rad/s max
    body_length_m: float = 0.2
    nnd_pref_bl: float = 0.7        # schooling nearest-neighbour preference
    strike_range_bl: float = 1.5
    handling_time_s: float = 20.0   # digestion/handling refractory after a kill
    strike_cooldown: float = 0.0    # remaining refractory time
    hunt_hunger_threshold: float = 0.3
    last_behavior: str = "idle"
    # recruitment state (§11 번식)
    age: float = 0.0
    spawn_cooldown: float = 0.0
    base_scale: float = 1.0
    ref_length_m: float = 0.2


@dataclass
class World:
    bounds: Tuple[float, float, float] = (30.0, 12.0, 30.0)
    turbidity: float = 0.1
    dt: float = 0.1
    seed: int = 7
    grid: Tuple[int, int, int] = (12, 4, 12)
    agents: List[Agent] = field(default_factory=list)
    resource: Optional[np.ndarray] = None
    resource_regrow: float = 0.05
    resource_cap: float = 1.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(7))
    time: float = 0.0
    # metrics
    behavior_counts: Dict[str, int] = field(default_factory=dict)
    transitions: Dict[str, int] = field(default_factory=dict)
    predation_events: int = 0
    births: int = 0
    # --- recruitment (§11). Without it a run is only an observation window. ---
    reproduction: bool = False       # opt-in: existing scenarios stay comparable
    maturity_age_s: float = 25.0
    spawn_energy: float = 0.72       # surplus required; spawning costs the parent
    spawn_rate_hz: float = 0.05
    spawn_refractory_s: float = 30.0
    growth_rate: float = 0.02
    carrying_capacity: Dict[str, int] = field(default_factory=dict)
    _next_id: int = 0

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        if self.resource is None:
            self.resource = np.full(self.grid, self.resource_cap * 0.8, dtype=float)

    # --- population ---------------------------------------------------------
    def add_population(self, taxon_id: str, count: int, role: str,
                       nnd_pref_bl: float = 0.7, cluster: bool = False) -> None:
        # Obligate schoolers must be introduced as a cohesive shoal, not a
        # dispersed cloud, or no school can nucleate (agents start beyond each
        # other's vision range). Cluster radius scales with the preferred NND so
        # the initial density is biologically plausible (Pitcher & Partridge).
        cluster_center = None
        cluster_radius = 0.0
        if cluster:
            resolved0 = compile_preset(taxon_id, seed=1)
            L0 = float(get_param(resolved0, "morphometrics.reference_length_m", 0.2))
            cluster_radius = nnd_pref_bl * L0 * (count ** (1.0 / 3.0)) * 1.2
            cluster_center = np.array([
                self.rng.uniform(cluster_radius, self.bounds[0] - cluster_radius),
                self.rng.uniform(0.35 * self.bounds[1], 0.65 * self.bounds[1]),
                self.rng.uniform(cluster_radius, self.bounds[2] - cluster_radius),
            ])
        for _ in range(count):
            seed = int(self.rng.integers(0, 2**31 - 1))
            resolved = compile_preset(taxon_id, seed=seed)
            L = float(get_param(resolved, "morphometrics.reference_length_m", 0.2))
            if cluster_center is not None:
                pos = cluster_center + self.rng.normal(scale=cluster_radius / 2.0, size=3)
                pos = np.clip(pos, 0.1, np.array(self.bounds) - 0.1)
            else:
                pos = np.array([
                    self.rng.uniform(0, self.bounds[0]),
                    self.rng.uniform(0.2 * self.bounds[1], 0.8 * self.bounds[1]),
                    self.rng.uniform(0, self.bounds[2]),
                ])
            heading = _normalize(self.rng.normal(size=3))
            agent = Agent(
                aid=self._next_id, taxon_id=taxon_id, role=role, resolved=resolved,
                loco=LocomotionController.from_preset(resolved),
                behavior=BehaviorController.from_preset(resolved, seed=seed),
                sensory=SensoryModel.from_preset(resolved),
                pos=pos, heading=heading, body_length_m=L,
                turn_rate=float(get_param(resolved, "locomotion.turn_rate_rad_s", 2.0)),
                nnd_pref_bl=nnd_pref_bl,
                strike_range_bl=float(get_param(resolved, "ecology.strike_range_bl", 1.5)),
                handling_time_s=float(get_param(resolved, "ecology.handling_time_s", 20.0)),
                base_scale=1.0, ref_length_m=L,
            )
            self._next_id += 1
            self.agents.append(agent)
        self.carrying_capacity.setdefault(taxon_id, int(round(count * 1.6)))

    # --- resource grid helpers ---------------------------------------------
    def _cell(self, pos: np.ndarray) -> Tuple[int, int, int]:
        gx = min(self.grid[0] - 1, max(0, int(pos[0] / self.bounds[0] * self.grid[0])))
        gy = min(self.grid[1] - 1, max(0, int(pos[1] / self.bounds[1] * self.grid[1])))
        gz = min(self.grid[2] - 1, max(0, int(pos[2] / self.bounds[2] * self.grid[2])))
        return gx, gy, gz

    # --- per-step perception ------------------------------------------------
    def _perceive(self, a: Agent) -> dict:
        prey_pos = None
        pred_pos = None
        neighbors: List[np.ndarray] = []     # local (spacing/alignment) set
        neigh_head: List[np.ndarray] = []
        school_pos: List[np.ndarray] = []    # extended shoal-membership set
        best_prey_d = 1e9
        best_pred_d = 1e9
        prey_near = 0            # prey-type agents near this predator (dilution)
        # Shoal membership is omnidirectional (vision + lateral line + the whole
        # school as a visual field), so fish keep contact with mates behind them.
        # This is a much larger, cone-free range than predator/prey detection.
        L = a.body_length_m
        local_r = a.nnd_pref_bl * L * 4.0
        # Shoal membership must span the domain so a school scattered by a
        # predator pass re-forms into ONE shoal instead of fragmenting into
        # persistent sub-centroids (herring re-aggregate within seconds).
        cohesion_r = max(a.sensory.vision_range_m, float(np.linalg.norm(self.bounds)))
        for b in self.agents:
            if b is a or not b.alive:
                continue
            d = float(np.linalg.norm(b.pos - a.pos))
            if b.taxon_id == a.taxon_id and a.behavior.is_schooler:
                if d < cohesion_r:
                    school_pos.append(b.pos)
                if d < local_r:
                    neighbors.append(b.pos)
                    neigh_head.append(b.heading)
            # predator/prey use the directional sensory model (vision cone)
            if not a.sensory.detects(a.pos, a.heading, b.pos, self.turbidity):
                continue
            if _is_prey_of(a, b):
                if d < best_prey_d:
                    best_prey_d, prey_pos = d, b.pos
                if d < 6.0 * L:
                    prey_near += 1
            if _is_prey_of(b, a) and d < best_pred_d:
                best_pred_d, pred_pos = d, b.pos

        gx, gy, gz = self._cell(a.pos)
        local_resource = float(self.resource[gx, gy, gz])
        feats = {
            "hunger": a.behavior.drives["hunger"],
            "prey_visible": 1.0 if prey_pos is not None else 0.0,
            "prey_adjacent": 1.0 if (prey_pos is not None and best_prey_d < a.strike_range_bl * a.body_length_m) else 0.0,
            "predator_visible": 1.0 if pred_pos is not None else 0.0,
            "neighbor_count": float(len(neighbors)),
            "neighbor_count_prey": float(prey_near),
            "resource_local": local_resource,
            "effort": 0.0,
            "is_schooler": 1.0 if a.behavior.is_schooler else 0.0,
        }
        return {
            "features": feats, "prey_pos": prey_pos, "pred_pos": pred_pos,
            "neighbors": neighbors, "neigh_head": neigh_head, "school_pos": school_pos,
            "prey_d": best_prey_d, "local_resource": local_resource,
            "cell": (gx, gy, gz),
        }

    # --- steering families --------------------------------------------------
    def _desired_heading(self, a: Agent, cmd: dict, perc: dict) -> np.ndarray:
        steer = cmd["steer"]
        if steer == "flee" and perc["pred_pos"] is not None:
            return _normalize(a.pos - perc["pred_pos"])
        if steer == "seek" and perc["prey_pos"] is not None:
            return _normalize(perc["prey_pos"] - a.pos)
        if steer == "school" and perc["school_pos"]:
            return self._boids(a, perc)
        if steer == "hold":
            return a.heading
        # wander: small deterministic perturbation
        jitter = self.rng.normal(scale=0.25, size=3)
        return _normalize(a.heading + jitter)

    def _boids(self, a: Agent, perc: dict) -> np.ndarray:
        """Reynolds boids with a stable equilibrium spacing:
          * cohesion pulls toward the shoal centroid (extended, cone-free set) so
            members never permanently lose the group;
          * separation is proximity-weighted (strong as d -> 0) and NOT normalized,
            so the group cannot collapse onto a point;
          * alignment matches local heading.
        Equilibrium NND is where cohesion ~ separation, tuned to the preferred
        spacing and validated against observed schooling NND (P0026)."""
        pref = a.nnd_pref_bl * a.body_length_m
        school = perc["school_pos"]
        center = np.mean(school, axis=0)
        to_center = center - a.pos
        dc = float(np.linalg.norm(to_center))
        # unit inward pull; never zero unless exactly at the centroid
        cohesion = (to_center / dc) if dc > 1e-6 else np.zeros(3)

        # Proximity-weighted repulsion normalized so it equals ~1 at the preferred
        # spacing, grows sharply below it (anti-collapse), fades above it. Total
        # capped so a dense neighbourhood cannot eject a fish from the shoal.
        sep = np.zeros(3)
        for n in perc["neighbors"]:
            diff = a.pos - n
            d = float(np.linalg.norm(diff))
            if d < 1.8 * pref and d > 1e-6:
                sep += (diff / d) * min((pref / d) ** 2, 6.0)
        sn = float(np.linalg.norm(sep))
        if sn > 3.0:
            sep = sep / sn * 3.0

        align = np.zeros(3)
        if perc["neigh_head"]:
            align = _normalize(np.mean(perc["neigh_head"], axis=0))

        w_align = float(get_param(a.resolved, "behavior.school_alignment", 0.85))
        # cohesion strengthens with distance so an outlier is pulled back harder
        w_cohesion = 1.4 + min(dc / (8.0 * pref), 1.5)
        v = w_cohesion * cohesion + 1.0 * sep + w_align * align
        return _normalize(v) if np.linalg.norm(v) > 1e-9 else a.heading

    # --- main step ----------------------------------------------------------
    def step(self) -> None:
        dt = self.dt
        # regrow resource (logistic), bounded (Gate G7: no infinite resource)
        r = self.resource
        r += self.resource_regrow * r * (1.0 - r / self.resource_cap) * dt
        np.clip(r, 0.0, self.resource_cap, out=r)

        for a in self.agents:
            if not a.alive:
                continue
            if a.strike_cooldown > 0.0:
                a.strike_cooldown = max(0.0, a.strike_cooldown - dt)
            perc = self._perceive(a)
            cmd = a.behavior.select(dt, perc["features"])

            # record behavior occupancy + transitions
            self.behavior_counts[cmd["behavior_id"]] = self.behavior_counts.get(cmd["behavior_id"], 0) + 1
            if cmd["behavior_id"] != a.last_behavior:
                key = f"{a.last_behavior}->{cmd['behavior_id']}"
                self.transitions[key] = self.transitions.get(key, 0) + 1
                a.last_behavior = cmd["behavior_id"]

            desired = self._desired_heading(a, cmd, perc)
            a.heading = self._rotate_toward(a.heading, desired, a.turn_rate * dt)

            kin = a.loco.step(dt, cmd["throttle"])
            speed = kin["speed_ms"]
            a.pos = a.pos + a.heading * speed * dt
            self._reflect_bounds(a)

            # energetics (Gate G7: bounded)
            cost = (0.002 + 0.02 * cmd["throttle"]) * dt
            a.energy = max(0.0, a.energy - cost)

            # feeding — planktivores filter-feed passively while schooling
            # (herring feed within the shoal), so intake also discharges hunger.
            if a.role == "planktivore":
                gx, gy, gz = perc["cell"]
                take = min(self.resource[gx, gy, gz], 0.3 * dt)
                self.resource[gx, gy, gz] -= take
                a.energy = min(1.0, a.energy + take * 0.8)
                a.behavior.drives["hunger"] = max(0.0, a.behavior.drives["hunger"] - take * 2.0)
            elif perc["features"]["prey_adjacent"] > 0.5 and perc["prey_pos"] is not None:
                self._attempt_predation(a, perc)

            if a.energy <= 0.0:
                a.alive = False  # starvation prevents unbounded population
            a.age += dt
            if a.spawn_cooldown > 0.0:
                a.spawn_cooldown = max(0.0, a.spawn_cooldown - dt)

        if self.reproduction:
            self._reproduce()
        self.time += dt

    def _reproduce(self) -> None:
        """Energy-gated recruitment with a logistic density brake.

        Spawning requires maturity, surplus energy and a refractory period, and
        its probability falls to zero as a population approaches its carrying
        capacity — so the population settles instead of exploding. The parent
        pays the offspring's energy, so nothing is created from nothing (G7).
        """
        counts: Dict[str, int] = {}
        for a in self.agents:
            if a.alive:
                counts[a.taxon_id] = counts.get(a.taxon_id, 0) + 1

        born = []
        for a in self.agents:
            if not a.alive or a.spawn_cooldown > 0.0:
                continue
            if a.age < self.maturity_age_s or a.energy < self.spawn_energy:
                continue
            k = self.carrying_capacity.get(a.taxon_id, 60)
            room = max(0.0, 1.0 - counts.get(a.taxon_id, 0) / max(k, 1))
            if room <= 0.0:
                continue
            if self.rng.random() > self.spawn_rate_hz * room * self.dt:
                continue

            cost = 0.35
            a.energy -= cost
            a.spawn_cooldown = self.spawn_refractory_s
            r = self.rng
            child = Agent(
                aid=self._next_id, taxon_id=a.taxon_id, role=a.role,
                resolved=a.resolved,
                loco=LocomotionController.from_preset(a.resolved),
                behavior=BehaviorController.from_preset(a.resolved, seed=self._next_id),
                sensory=a.sensory,
                pos=np.clip(a.pos + (r.random(3) - 0.5) * 0.4,
                            0.1, np.array(self.bounds) - 0.1),
                heading=_normalize(r.normal(size=3)),
                energy=cost * 0.8,
                turn_rate=a.turn_rate,
                # recruits enter small and grow toward the adult reference size
                body_length_m=a.ref_length_m * 0.55,
                nnd_pref_bl=a.nnd_pref_bl,
                strike_range_bl=a.strike_range_bl,
                handling_time_s=a.handling_time_s,
                base_scale=1.0, ref_length_m=a.ref_length_m,
                spawn_cooldown=self.spawn_refractory_s,
            )
            self._next_id += 1
            born.append(child)
            self.births += 1

        self.agents.extend(born)
        for a in self.agents:
            if a.alive and a.body_length_m < a.ref_length_m:
                a.body_length_m = min(a.ref_length_m,
                                      a.body_length_m + self.growth_rate
                                      * a.ref_length_m * self.dt)

    def _attempt_predation(self, a: Agent, perc: dict) -> None:
        # A predator hunts only when hungry and not in a handling/digestion
        # refractory period; otherwise it ignores adjacent prey. This caps the
        # predation rate and keeps the prey population from collapsing (Gate G7).
        if a.strike_cooldown > 0.0 or a.behavior.drives["hunger"] < a.hunt_hunger_threshold:
            return
        base_success = float(get_param(a.resolved, "ecology.strike_success_prob", 0.3))
        for b in self.agents:
            if b.alive and _is_prey_of(a, b):
                if float(np.linalg.norm(b.pos - a.pos)) < a.strike_range_bl * a.body_length_m:
                    # Confusion/dilution effect: a prey embedded in a dense school
                    # is harder to single out (Landeau & Terborgh 1986).
                    dilution = 1.0 / (1.0 + 0.15 * perc["features"].get("neighbor_count_prey", 0.0))
                    if self.rng.random() < base_success * dilution:
                        b.alive = False
                        a.energy = min(1.0, a.energy + 0.5)
                        a.behavior.drives["hunger"] = max(0.0, a.behavior.drives["hunger"] - 0.8)
                        self.predation_events += 1
                    a.strike_cooldown = a.handling_time_s  # refractory after any strike attempt
                    return
                    return

    def _rotate_toward(self, cur: np.ndarray, target: np.ndarray, max_ang: float) -> np.ndarray:
        cur = _normalize(cur)
        target = _normalize(target)
        cosang = float(np.clip(np.dot(cur, target), -1.0, 1.0))
        ang = math.acos(cosang)
        if ang <= max_ang or ang < 1e-6:
            return target
        t = max_ang / ang
        return _normalize(cur * (1 - t) + target * t)

    def _reflect_bounds(self, a: Agent) -> None:
        for i in range(3):
            if a.pos[i] < 0:
                a.pos[i] = -a.pos[i]
                a.heading[i] = abs(a.heading[i])
            elif a.pos[i] > self.bounds[i]:
                a.pos[i] = 2 * self.bounds[i] - a.pos[i]
                a.heading[i] = -abs(a.heading[i])

    # --- metrics ------------------------------------------------------------
    def run(self, steps: int) -> dict:
        for _ in range(steps):
            self.step()
        return self.metrics()

    def mean_nnd_bl(self, taxon_id: str, in_school_only: bool = True) -> Optional[float]:
        """Mean nearest-neighbour distance in body lengths. Field studies measure
        NND *within the school* (Pitcher & Partridge 1983), i.e. among individuals
        currently schooling — not individuals scattered while fleeing a predator.
        `in_school_only` restricts to agents in the schooling state accordingly."""
        def keep(a: Agent) -> bool:
            if not (a.alive and a.taxon_id == taxon_id):
                return False
            if in_school_only and a.behavior.is_schooler:
                return a.last_behavior == "school"
            return True
        members = [a for a in self.agents if keep(a)]
        if len(members) < 2:
            return None
        pts = np.array([a.pos for a in members])
        L = float(np.mean([a.body_length_m for a in members]))
        dmat = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
        np.fill_diagonal(dmat, np.inf)
        nnd = dmat.min(axis=1)
        return float(np.mean(nnd) / L)

    def metrics(self) -> dict:
        alive = [a for a in self.agents if a.alive]
        total_beh = sum(self.behavior_counts.values()) or 1
        occupancy = {k: round(v / total_beh, 4) for k, v in sorted(self.behavior_counts.items())}
        by_taxon: Dict[str, int] = {}
        for a in alive:
            by_taxon[a.taxon_id] = by_taxon.get(a.taxon_id, 0) + 1
        return {
            "time_s": round(self.time, 3),
            "alive": len(alive),
            "alive_by_taxon": by_taxon,
            "behavior_occupancy": occupancy,
            "transition_counts": dict(sorted(self.transitions.items())),
            "predation_events": self.predation_events,
            "mean_energy": round(float(np.mean([a.energy for a in alive])), 4) if alive else 0.0,
            "resource_mean": round(float(self.resource.mean()), 4),
        }


# Trophic relationships derived from preset ecology role, not hard-coded species.
_PREY_TABLE = {
    "mesopredator": {"planktivore"},
    "ambush_predator": {"planktivore", "mesopredator"},
    "planktivore": set(),
    "grazer": set(),
}


def _is_prey_of(pred: Agent, prey: Agent) -> bool:
    if pred.taxon_id == prey.taxon_id:
        return False
    return prey.role in _PREY_TABLE.get(pred.role, set())
