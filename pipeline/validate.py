"""Validation: does the engine rank famous analog sites highly without being told about them?

Usage:
    python -m pipeline.validate

Writes web/public/data/validation.json and prints a summary. Results are
reported as they come out; nothing here tunes the score.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from . import config, grid

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data"
GROUPS = {"mean_slope": "terrain", "local_relief": "terrain", "mean_temp": "temperature",
          "diurnal_range": "temperature", "albedo": "albedo", "rain_mm": "dryness", "ndvi": "dryness"}
PRESET_LABELS = {"balanced": "Balanced", "terrain": "Terrain and mobility", "thermal": "Thermal hardware"}
CHANCE_PERCENT = 10


class World:
    def __init__(self, name: str):
        self.name = name
        self.meta = json.loads((OUT / f"{name}.meta.json").read_text())
        self.table = np.fromfile(OUT / f"{name}.bin", dtype="<f4").reshape(self.meta["n_rows"], -1)
        self.idx = np.fromfile(OUT / f"{name}.idx.bin", dtype="<u4") if self.meta["indexed"] else None
        names = [f["name"] for f in self.meta["features"]]
        self.features = self.table[:, [self.meta["columns"].index(n) for n in names]]
        self.tolerance = np.array([f["tolerance"] for f in self.meta["features"]], np.float32)
        self.groups = [GROUPS[n] for n in names]
        cells = self.idx if self.idx is not None else np.arange(self.meta["n_rows"])
        lat, lon = grid.cell_centres(name)
        self.lat = lat[cells // self.meta["cols"]]
        self.lon = lon[cells % self.meta["cols"]]
        self.area = np.cos(np.radians(self.lat))

    def row(self, lat: float, lon: float, reach: int = 0) -> int:
        """Row of the cell at a point, or of the nearest cell within `reach` cells; -1 if none."""
        best, best_d = -1, 1e9
        step = self.meta["cell_deg"]
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                cell = grid.cell_index(self.name, float(np.clip(lat + dy * step, -89.9, 89.9)), lon + dx * step)
                r = cell if self.idx is None else int(np.searchsorted(self.idx, cell))
                if self.idx is not None and (r >= len(self.idx) or self.idx[r] != cell):
                    continue
                if dx * dx + dy * dy < best_d:
                    best, best_d = r, dx * dx + dy * dy
        return best


def score(world: World, target: np.ndarray, weights: dict, tolerance: np.ndarray | None = None) -> np.ndarray:
    """The score from the handoff: 100 * sum(w * exp(-0.5 * (d / tol)^2)) / sum(w), skipping missing features."""
    w = np.array([weights[g] for g in world.groups], np.float32)
    tolerance = world.tolerance if tolerance is None else tolerance
    d = (world.features - target[None, :]) / tolerance[None, :]
    ok = np.isfinite(d)
    m = np.where(ok, np.exp(-0.5 * np.square(np.where(ok, d, 0))), 0) * w
    wsum = (ok * w).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(wsum > 0, 100 * m.sum(axis=1) / wsum, np.nan)


def top_matches(world: World, scores: np.ndarray, count: int = 5, min_km: float = config.MIN_MATCH_SEPARATION_KM) -> list[int]:
    order = np.argsort(-np.nan_to_num(scores, nan=-1))[:20000]
    picked: list[int] = []
    for r in order:
        if all(_km(world, r, p) >= min_km for p in picked):
            picked.append(int(r))
            if len(picked) == count:
                break
    return picked


def _km(world: World, a: int, b: int) -> float:
    la1, la2 = np.radians(world.lat[a]), np.radians(world.lat[b])
    dlon = np.radians(world.lon[a] - world.lon[b])
    h = np.sin((la1 - la2) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin(dlon / 2) ** 2
    return float(2 * world.meta["radius_km"] * np.arcsin(min(1.0, np.sqrt(h))))


def main() -> None:
    earth, mars = World("earth"), World("mars")
    sites = json.loads((OUT / "sites.json").read_text())
    targets = [s for s in sites["targets"] if s["world"] == "mars"]
    analogs = sites["analogs"]
    analog_rows = [earth.row(a["lat"], a["lon"], reach=2) for a in analogs]
    total_area = earth.area.sum()

    # 1. Blind test: where does each known analog rank among all Earth land cells?
    def top_percent_of_every_cell(s: np.ndarray) -> np.ndarray:
        """Share of land area (percent) scoring strictly higher than each cell."""
        filled = np.nan_to_num(s, nan=-1.0)
        order = np.argsort(-filled, kind="stable")
        sorted_scores = filled[order]
        area_before = np.concatenate([[0.0], np.cumsum(earth.area[order])[:-1]])
        first_of_tie = np.searchsorted(-sorted_scores, -sorted_scores, side="left")
        out = np.empty(len(s))
        out[order] = 100 * area_before[first_of_tie] / total_area
        return np.where(np.isfinite(s), out, np.nan)

    rng = np.random.default_rng(0)
    random_rows = rng.choice(len(earth.area), 5000, replace=False, p=earth.area / total_area)
    valid_analogs = [r for r in analog_rows if r >= 0]

    def blind_test(preset_weights: dict, tolerance: np.ndarray | None = None):
        """Rank every known analog for every target under each preset."""
        matrices, summary, follow = {}, [], {}
        for pid, weights in preset_weights.items():
            ranks = np.stack([
                top_percent_of_every_cell(score(earth, mars.features[mars.row(t["lat"], t["lon"])], weights, tolerance))
                for t in targets
            ], axis=1)  # land cell x target
            matrix = [[None if r < 0 or np.isnan(ranks[r, j]) else round(float(ranks[r, j]), 2)
                       for j in range(len(targets))] for r in analog_rows]
            flat = [v for row in matrix for v in row if v is not None]
            matrices[pid] = matrix
            summary.append({
                "id": pid, "label": PRESET_LABELS[pid], "pairs": len(flat),
                "share_top10": round(100 * float(np.mean([v <= CHANCE_PERCENT for v in flat])), 1),
                "median_top_percent": round(float(np.median(flat)), 1),
            })
            # Is each analog a top-10% match for at least one target? Random land sets the bar.
            best_analog = np.nanmin(ranks[valid_analogs], axis=1)
            best_random = np.nanmin(ranks[random_rows], axis=1)
            follow[pid] = {
                "analogs_with_a_top10_target": int((best_analog <= CHANCE_PERCENT).sum()),
                "analogs": len(valid_analogs),
                "random_share_with_a_top10_target": round(100 * float((best_random <= CHANCE_PERCENT).mean()), 1),
                "random_cells": len(random_rows),
            }
        return matrices, summary, follow

    top_percent, presets, follow_up = blind_test(config.PRESETS)

    # The first version of the engine scored five measurements, without rainfall and plant
    # cover. Its blind test is re-run here (dryness weight 0) so both results stay on record.
    five_only = {pid: {**w, "dryness": 0.0} for pid, w in config.PRESETS.items()}
    _, first_presets, first_follow = blind_test(five_only)

    # The one tolerance revisit the plan allowed, tried on that first version. At 15 K both
    # temperature rows are near zero for most of Earth against any Mars target. Doubling them
    # to 30 K did not improve the headline number, so the original tolerances were kept.
    wide = earth.tolerance.copy()
    wide[[2, 3]] = 30.0
    _, trial_presets, _ = blind_test(five_only, wide)
    first_version = {
        "presets": first_presets,
        "follow_up": first_follow,
        "tolerance_trial": {
            "change": "Mean temperature and day-night range tolerances doubled from 15 K to 30 K",
            "presets": [{"label": p["label"], "share_top10": p["share_top10"]} for p in trial_presets],
            "kept": False,
        },
    }

    # 2. Self-match: an Earth cell searched against Earth must come back first with a score of 100.
    complete = np.flatnonzero(np.isfinite(earth.features).all(axis=1))
    sample = rng.choice(complete, 200, replace=False)
    ok = 0
    for r in sample:
        s = score(earth, earth.features[r], config.PRESETS["balanced"])
        ok += bool(abs(s[r] - 100) < 1e-3 and np.nanmax(s) <= s[r] + 1e-3)
    self_match = {"name": "An Earth cell searched against Earth returns itself with a score of 100",
                  "passed": ok == len(sample), "detail": f"{ok} of {len(sample)} randomly chosen land cells did"}

    # 3. Stability: moving the target one cell should keep the top five in the same regions.
    kept, compared = 0, 0
    for t in targets:
        base = top_matches(earth, score(earth, mars.features[mars.row(t["lat"], t["lon"])], config.PRESETS["balanced"]))
        for dlat, dlon in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)):
            moved = top_matches(earth, score(earth, mars.features[mars.row(t["lat"] + dlat, t["lon"] + dlon)],
                                             config.PRESETS["balanced"]))
            kept += sum(any(_km(earth, m, b) <= 600 for b in base) for m in moved)
            compared += len(moved)
    share = 100 * kept / compared
    stability = {"name": "Moving the target by one cell keeps the top five matches in the same regions",
                 "passed": share >= 60,
                 "detail": f"{share:.0f}% of the top-five matches stayed within 600 km of an original match "
                           f"({len(targets)} Mars targets, four one-cell moves each, Balanced preset)"}

    checks = json.loads((OUT / "checks.json").read_text())
    result = {
        "generated": date.today().isoformat(),
        "earth_land_cells": earth.meta["n_rows"],
        "chance_percent": CHANCE_PERCENT,
        "presets": presets,
        "targets": [t["site"] for t in targets],
        "analogs": [{**a, "on_land": r >= 0} for a, r in zip(analogs, analog_rows)],
        "top_percent": top_percent,
        "follow_up": follow_up,
        "first_version": first_version,
        "self_match": self_match,
        "stability": stability,
        "reader_checks": [c for world in ("earth", "mars", "moon") for c in checks.get(world, [])],
        "notes": [
            "Famous analog sites were chosen for many reasons this engine cannot see: minerals, water chemistry, "
            "microbes, road access. A site picked for its rocks can rank low here and still be a good analog.",
            "The score uses seven measurements on cells about 30 km wide. It says nothing about a single "
            "outcrop, crater or lava tube inside a cell.",
            "Ranks count land area, so the large polar cells of the grid do not inflate the result.",
            "Rainfall and plant cover were added to the score after the first blind test failed. Their tolerances "
            "are standard thresholds (250 mm a year for a desert, a vegetation index of 0.2 for barren land) and "
            "were set before this result was computed. Because the change came after seeing a result, treat the "
            "second result as weaker evidence than a test planned in advance.",
        ],
    }
    (OUT / "validation.json").write_text(json.dumps(result))
    for p in presets:
        print(f"{p['label']:22s} {p['share_top10']:5.1f}% of known analogs in the top 10% "
              f"(chance 10%), median top {p['median_top_percent']:.0f}%, {p['pairs']} pairs")
    for pid, f in follow_up.items():
        print(f"  {pid}: {f['analogs_with_a_top10_target']}/{f['analogs']} analogs are top-10% for at least one target "
              f"(random land: {f['random_share_with_a_top10_target']}%)")
    print("  first version (five measurements):", ", ".join(f"{p['label']} {p['share_top10']}%" for p in first_presets))
    print("  first version, 30 K trial:", ", ".join(f"{p['label']} {p['share_top10']}%" for p in trial_presets))
    for c in (self_match, stability):
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['name']}: {c['detail']}")


if __name__ == "__main__":
    main()
