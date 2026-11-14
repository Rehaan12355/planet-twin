"""Build the per-world feature files the web app loads.

Usage:
    python -m pipeline.build_features            # all three worlds
    python -m pipeline.build_features mars moon  # only some

Writes web/public/data/<world>.bin (little-endian Float32, rows x columns),
<world>.meta.json, earth.idx.bin (Uint32 flat cell index of each land row),
sites.json, places.json, checks.json and quick-look maps in docs/quicklooks/.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

from . import config, grid, terrain
from .sources import RAW

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data"
QUICKLOOKS = ROOT / "docs" / "quicklooks"

FEATURE_LABELS = {
    "mean_slope": ("Mean slope", "terrain"),
    "local_relief": ("Local relief", "terrain"),
    "mean_temp": ("Mean surface temperature", "temperature"),
    "diurnal_range": ("Day-night temperature range", "temperature"),
    "albedo": ("Albedo", "albedo"),
    "rain_mm": ("Yearly rain and snowfall", "dryness"),
    "ndvi": ("Plant cover (vegetation index)", "dryness"),
}
# Rain and plant cover are zero everywhere on Mars and the Moon, so they have no rank
# within those worlds and are left out of the relative (hometown) match.
PHYSICAL_ONLY = {"rain_mm", "ndvi"}
DRY_SOURCES = {
    "rain_mm": "No rain or snow falls here; set to 0",
    "ndvi": "Nothing grows here; set to 0",
}
SCORED = [f["name"] for f in config.FEATURES]


def build_mars() -> tuple[dict, dict, list]:
    from .readers import elevation, mars

    w = config.WORLDS["mars"]
    lat, lon = grid.cell_centres("mars")
    z = elevation.read_mola()
    slope, relief = terrain.summarise(terrain.slope_degrees(z, w["radius_km"]), z, w["rows"], w["cols"])
    cell_z = terrain.cell_mean(z, w["rows"], w["cols"])
    temp, swing, glat, glon, sols = mars.read_legacy_gcm()
    albedo = grid.block_reduce(mars.read_tes_albedo(), 4)
    cols = {
        "mean_slope": slope,
        "local_relief": relief,
        "mean_temp": grid.regrid_bilinear(temp, glat, glon, lat, lon),
        "diurnal_range": grid.regrid_bilinear(swing, glat, glon, lat, lon),
        "albedo": albedo,
        "rain_mm": np.zeros_like(albedo),
        "ndvi": np.zeros_like(albedo),
    }
    sources = {
        **DRY_SOURCES,
        "mean_slope": "MGS MOLA MEGDR topography, 16 pixels per degree (NASA PDS)",
        "local_relief": "MGS MOLA MEGDR topography, 16 pixels per degree (NASA PDS)",
        "mean_temp": f"NASA Ames Legacy Mars GCM surface temperature, {sols} sols spread over one Mars year, 5 x 6 degree model grid",
        "diurnal_range": f"NASA Ames Legacy Mars GCM surface temperature, {sols} sols spread over one Mars year, 5 x 6 degree model grid",
        "albedo": "MGS TES bolometric albedo, 7.4 km (USGS Astrogeology)",
    }
    olympus = grid.cell_index("mars", 18.65, 226.2)
    eq = cols["mean_temp"][170:190].mean()
    checks = [
        _check("MOLA elevations fall within the label's valid range", True,
               f"{z.min():.0f} to {z.max():.0f} m against -8177 to 21171 m"),
        _check("The Olympus Mons cell is among the highest on Mars",
               cell_z.flat[olympus] >= np.percentile(cell_z, 99.9),
               f"cell mean {cell_z.flat[olympus]:.0f} m; 99.9th percentile of all cells is {np.percentile(cell_z, 99.9):.0f} m"),
        _check("Mars is colder at the poles than at the equator",
               cols["mean_temp"][:10].mean() < eq and cols["mean_temp"][-10:].mean() < eq,
               f"north {cols['mean_temp'][:10].mean():.0f} K, equator {eq:.0f} K, south {cols['mean_temp'][-10:].mean():.0f} K"),
    ]
    return cols, sources, checks


def build_moon() -> tuple[dict, dict, list]:
    from .readers import elevation, moon

    w = config.WORLDS["moon"]
    z = grid.block_reduce(elevation.read_lola(), 2, np.mean)  # 16 ppd -> 8 ppd, about 3.8 km
    slope, relief = terrain.summarise(terrain.slope_degrees(z, w["radius_km"]), z, w["rows"], w["cols"])
    tmean, tmax, tmin = moon.read_diviner()
    cols = {
        "mean_slope": slope,
        "local_relief": relief,
        "mean_temp": grid.block_reduce(tmean, 2),
        "diurnal_range": grid.block_reduce(tmax - tmin, 2),
        "albedo": grid.block_reduce(moon.read_lola_albedo(), 4),
    }
    cols["rain_mm"] = np.zeros_like(cols["albedo"])
    cols["ndvi"] = np.zeros_like(cols["albedo"])
    sources = {
        **DRY_SOURCES,
        "mean_slope": "LRO LOLA gridded elevation LDEM_16, averaged to 8 pixels per degree (NASA PDS)",
        "local_relief": "LRO LOLA gridded elevation LDEM_16, averaged to 8 pixels per degree (NASA PDS)",
        "mean_temp": "LRO Diviner Global Cumulative Products, bolometric temperature by local time (NASA PDS)",
        "diurnal_range": "LRO Diviner Global Cumulative Products, bolometric temperature by local time (NASA PDS)",
        "albedo": "LRO LOLA normal albedo at 1064 nm, LDAM_4 (NASA PDS)",
    }
    equator = cols["diurnal_range"][88:92]
    checks = [
        _check("The lunar equator has a day-night range above 200 K", np.nanmean(equator) > 200,
               f"mean range within 2 degrees of the equator is {np.nanmean(equator):.0f} K"),
    ]
    return cols, sources, checks


def build_earth() -> tuple[dict, dict, list, np.ndarray]:
    from .readers import earth_climate, elevation, land

    w = config.WORLDS["earth"]
    lat, lon = grid.cell_centres("earth")
    z = grid.block_reduce(elevation.read_etopo(), 2, np.mean)  # 60 arc-seconds -> 2 arc-minutes, about 3.7 km
    mask = land.land_fraction(*z.shape)
    z = np.where(mask == 1, z, 0.0).astype(np.float32)  # sea surface, not sea floor
    slope, relief = terrain.summarise(terrain.slope_degrees(z, w["radius_km"]), z, w["rows"], w["cols"])
    is_land = terrain.cell_mean(mask.astype(np.float32), w["rows"], w["cols"]) >= 0.5

    temp, swing, mlat, mlon = earth_climate.read_temperature()
    rain, _, _ = earth_climate.read_rain()
    snow, _, _ = earth_climate.read_snow()
    alb, clat, clon = earth_climate.read_albedo()
    ndvi, months = earth_climate.read_ndvi()
    nlat = 90.0 - (np.arange(1800) + 0.5) * 0.1
    nlon = -180.0 + (np.arange(3600) + 0.5) * 0.1
    cols = {
        "mean_slope": slope,
        "local_relief": relief,
        "mean_temp": grid.regrid_bilinear(temp, mlat, mlon, lat, lon),
        "diurnal_range": grid.regrid_bilinear(swing, mlat, mlon, lat, lon),
        "albedo": grid.regrid_bilinear(alb, clat, clon, lat, lon),
        "rain_mm": grid.regrid_bilinear(rain, mlat, mlon, lat, lon),
        "ndvi": grid.regrid_bilinear(ndvi, nlat, nlon, lat, lon),
        "snow_frac": grid.regrid_bilinear(snow, mlat, mlon, lat, lon),
    }
    # MODIS reports no vegetation index over permanent ice and snow. Nothing grows there, so it is 0.
    cols["ndvi"] = np.where(np.isnan(cols["ndvi"]) & (cols["snow_frac"] >= 0.5), 0.0, cols["ndvi"]).astype(np.float32)
    sources = {
        "mean_slope": "ETOPO 2022, 60 arc-second, averaged to 2 arc-minutes (NOAA NCEI)",
        "local_relief": "ETOPO 2022, 60 arc-second, averaged to 2 arc-minutes (NOAA NCEI)",
        "mean_temp": "MERRA-2 skin temperature climatology, 0.5 x 0.625 degree (NASA POWER v10)",
        "diurnal_range": "MERRA-2 skin temperature, mean daily maximum minus mean daily minimum (NASA POWER v10)",
        "albedo": "CERES SYN1deg all-sky surface albedo climatology, 1 degree (NASA POWER v10)",
        "rain_mm": "MERRA-2 bias-corrected precipitation climatology (NASA POWER v10)",
        "ndvi": f"MODIS/Terra MOD13C2 NDVI, mean of {months} monthly composites, 0.1 degree (NASA)",
        "snow_frac": "MERRA-2 land snow-cover fraction climatology (NASA POWER v10)",
    }

    def at(name, la, lo):
        return float(cols[name].flat[grid.cell_index("earth", la, lo)])

    checks = [
        _check("A Himalaya cell has relief above 3000 m", 10 ** at("local_relief", 28.0, 86.9) > 3000,
               f"{10 ** at('local_relief', 28.0, 86.9):.0f} m near Everest"),
        _check("A central Sahara cell has mean slope under 1 degree", at("mean_slope", 23.5, 10.5) < 1,
               f"{at('mean_slope', 23.5, 10.5):.2f} degrees at 23.5 N, 10.5 E"),
        _check("Sahara albedo is higher than Amazon albedo", at("albedo", 23.5, 10.5) > at("albedo", -3.5, -62.5),
               f"Sahara {at('albedo', 23.5, 10.5):.2f}, Amazon {at('albedo', -3.5, -62.5):.2f}"),
    ]
    return cols, sources, checks, is_land


def _check(name: str, passed, detail: str) -> dict:
    print(f"  {'PASS' if passed else 'FAIL'}  {name}: {detail}")
    return {"name": name, "passed": bool(passed), "detail": detail}


def write_world(world: str, cols: dict, sources: dict, keep: np.ndarray | None = None) -> None:
    w = config.WORLDS[world]
    names = list(cols)
    table = np.stack([cols[n].astype(np.float32).ravel() for n in names], axis=1)
    weights = np.repeat(grid.area_weights(world), w["cols"])
    if keep is not None:
        idx = np.flatnonzero(keep.ravel()).astype("<u4")
        table, weights = table[idx], weights[idx]
        idx.tofile(OUT / f"{world}.idx.bin")
    table.astype("<f4").tofile(OUT / f"{world}.bin")
    meta = {
        "world": world,
        "radius_km": w["radius_km"],
        "cell_deg": w["cell_deg"],
        "cols": w["cols"],
        "rows": w["rows"],
        "lon0": grid.LON0[world],
        "columns": names,
        "n_rows": int(table.shape[0]),
        "indexed": keep is not None,
        "low_confidence_lat": config.LOW_CONFIDENCE_LAT,
        "features": [
            {"name": f["name"], "label": FEATURE_LABELS[f["name"]][0], "unit": f["unit"],
             "tolerance": f["tolerance"], "group": FEATURE_LABELS[f["name"]][1],
             "relative": f["name"] not in PHYSICAL_ONLY}
            for f in config.FEATURES
        ],
        "quantiles": {n: [round(q, 4) for q in grid.weighted_quantiles(table[:, i], weights)]
                      for i, n in enumerate(names) if n in SCORED},
        "sources": sources,
    }
    (OUT / f"{world}.meta.json").write_text(json.dumps(meta))
    size = (OUT / f"{world}.bin").stat().st_size
    missing = {n: f"{np.isnan(table[:, i]).mean():.1%}" for i, n in enumerate(names) if np.isnan(table[:, i]).any()}
    print(f"  wrote {world}.bin: {table.shape[0]:,} rows x {len(names)} columns, {size / 1e6:.1f} MB; missing {missing or 'none'}")


def quicklooks(world: str, cols: dict, keep: np.ndarray | None = None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    QUICKLOOKS.mkdir(parents=True, exist_ok=True)
    x0 = grid.LON0[world]
    for name, a in cols.items():
        a = np.where(keep, a, np.nan) if keep is not None else a
        fig, ax = plt.subplots(figsize=(10, 5), dpi=110)
        lo, hi = np.nanpercentile(a, [2, 98])
        im = ax.imshow(a, extent=(x0, x0 + 360, -90, 90), vmin=lo, vmax=hi, cmap="viridis", interpolation="nearest")
        ax.set(title=f"{world.title()}: {name}", xlabel="Longitude (degrees east)", ylabel="Latitude")
        fig.colorbar(im, ax=ax, shrink=0.8)
        fig.savefig(QUICKLOOKS / f"{world}_{name}.png", bbox_inches="tight")
        plt.close(fig)


def write_sites() -> None:
    def rows(name):
        with open(ROOT / "pipeline" / "sites" / name, newline="") as f:
            return list(csv.DictReader(f))

    targets = [{"world": r["world"], "site": r["site"], "lat": float(r["lat"]), "lon": float(r["lon_e"])}
               for r in rows("targets.csv")]
    analogs = [{"site": r["site"], "lat": float(r["lat"]), "lon": float(r["lon"])} for r in rows("known_analogs.csv")]
    (OUT / "sites.json").write_text(json.dumps({"targets": targets, "analogs": analogs}))


def write_places() -> None:
    """Bundle the Natural Earth populated places so city search needs no outside service."""
    import shapefile

    reader = shapefile.Reader(str(RAW / "earth/ne_10m_populated_places_simple.zip"))
    fields = [f[0] for f in reader.fields[1:]]
    name, country, pop, la, lo = (fields.index(k) for k in ("name", "adm0name", "pop_max", "latitude", "longitude"))
    seen, places = set(), []
    for rec in sorted(reader.records(), key=lambda r: -(r[pop] or 0)):
        key = (rec[name], rec[country])
        if not rec[name] or key in seen:
            continue
        seen.add(key)
        places.append([rec[name], rec[country], round(rec[la], 3), round(rec[lo], 3)])
    (OUT / "places.json").write_text(json.dumps(places, ensure_ascii=False, separators=(",", ":")))
    print(f"  wrote places.json: {len(places):,} places")


def main(worlds: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checks_path = OUT / "checks.json"
    checks = json.loads(checks_path.read_text()) if checks_path.exists() else {}
    for world in worlds:
        print(f"{world}:")
        if world == "earth":
            cols, sources, checks[world], is_land = build_earth()
            write_world(world, cols, sources, keep=is_land)
            quicklooks(world, cols, keep=is_land)
        else:
            cols, sources, checks[world] = build_mars() if world == "mars" else build_moon()
            write_world(world, cols, sources)
            quicklooks(world, cols)
    checks_path.write_text(json.dumps(checks, indent=1))
    write_sites()
    write_places()
    failed = [c["name"] for cs in checks.values() for c in cs if not c["passed"]]
    if failed:
        sys.exit(f"reader checks failed: {failed}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["mars", "moon", "earth"])
