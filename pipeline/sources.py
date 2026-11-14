"""Every data source: URLs, access check and download.

Usage:
    python -m pipeline.sources check      # request each URL, print status and size
    python -m pipeline.sources download   # fetch everything into data/raw/
    python -m pipeline.sources manifest   # write data/raw/manifest.json from files on disk
    python -m pipeline.sources docs       # write DATA_SOURCES.md
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import certifi

# python.org builds of Python do not read the macOS keychain.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import requests  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "planet-twin/0.1 (NASA Space Apps 2026 project)"}

PDS = "https://pds-geosciences.wustl.edu"
POWER = "https://nasa-power.s3.us-west-2.amazonaws.com"
NAS = "https://data.nas.nasa.gov/legacygcm/legacygcm/ACTIVECLDS_NCDF"
WAYBACK = "https://web.archive.org/web/{ts}id_/https://neo.gsfc.nasa.gov/archive/geotiff.float/MOD_NDVI_M/{name}"
TREK = "https://trek.nasa.gov/tiles"

DIVINER_BANDS = [
    "90s80s", "80s70s", "70s60s", "60s50s", "50s40s", "40s30s", "30s20s", "20s10s", "10s00s",
    "00n10n", "10n20n", "20n30n", "30n40n", "40n50n", "50n60n", "60n70n", "70n80n", "80n90n",
]

# Twelve of the 67 ten-sol files, evenly spaced through one Mars year.
LEGACY_GCM_FILES = [
    "LegacyGCM_Ls000_Ls004.nc", "LegacyGCM_Ls029_Ls033.nc", "LegacyGCM_Ls057_Ls061.nc",
    "LegacyGCM_Ls084_Ls088.nc", "LegacyGCM_Ls111_Ls115.nc", "LegacyGCM_Ls140_Ls145.nc",
    "LegacyGCM_Ls173_Ls178.nc", "LegacyGCM_Ls209_Ls214.nc", "LegacyGCM_Ls247_Ls253.nc",
    "LegacyGCM_Ls286_Ls291.nc", "LegacyGCM_Ls322_Ls327.nc", "LegacyGCM_Ls355_Ls000.nc",
]

# One archived MOD13C2 monthly composite per calendar month (Wayback timestamp, file).
NDVI_FILES = [
    ("20250416221001", "MOD13C2.A2023001.061.2023034191717.tif"),
    ("20250416123035", "MOD13C2.A2021032.061.2021068110257.tif"),
    ("20250416221043", "MOD13C2.A2023060.061.2023100032443.tif"),
    ("20250416221115", "MOD13C2.A2023091.061.2023130015805.tif"),
    ("20250419144633", "MOD13C2.A2018121.061.2021349073612.tif"),
    ("20250416220816", "MOD13C2.A2022152.061.2022201123617.tif"),
    ("20250419195922", "MOD13C2.A2023182.061.2023226010223.tif"),
    ("20250416221141", "MOD13C2.A2023213.061.2023258020153.tif"),
    ("20250416220852", "MOD13C2.A2022244.061.2022297185735.tif"),
    ("20250416221202", "MOD13C2.A2023274.061.2023306003339.tif"),
    ("20250416221219", "MOD13C2.A2023305.061.2023345100120.tif"),
    ("20250416220743", "MOD13C2.A2021335.061.2022005004102.tif"),
]

GIBS_BLUE_MARBLE = (
    "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap"
    "&VERSION=1.3.0&LAYERS=BlueMarble_ShadedRelief_Bathymetry&STYLES=&FORMAT=image/jpeg"
    "&CRS=EPSG:4326&BBOX=-90,-180,90,180&WIDTH=4096&HEIGHT=2048"
)

MARS_TILE_LAYER = "Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m"
TILE_ZOOM = 3  # 16 x 8 tiles of 256 px = 4096 x 2048


@dataclass
class Source:
    key: str
    world: str
    title: str
    used_for: str
    agency: str
    nasa: bool
    licence: str
    files: list[tuple[str, str]] = field(default_factory=list)  # (url, path under data/raw)
    zarr: tuple[str, list[str]] | None = None  # (store url, variables)
    landing: str = ""
    note: str = ""


def _tiles(layer: str, folder: str) -> list[tuple[str, str]]:
    out = []
    for row in range(2**TILE_ZOOM):
        for col in range(2 ** (TILE_ZOOM + 1)):
            url = f"{TREK}/{layer}/1.0.0/default/default028mm/{TILE_ZOOM}/{row}/{col}.jpg"
            out.append((url, f"{folder}/{TILE_ZOOM}_{row}_{col}.jpg"))
    return out


SOURCES: list[Source] = [
    # ---- Earth
    Source(
        "earth_elevation", "earth", "ETOPO 2022 global relief, 60 arc-second, surface elevation",
        "Slope, relief", "NOAA NCEI", False, "Public domain (US Government)",
        files=[(
            "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_surface_elev_netcdf/"
            "ETOPO_2022_v1_60s_N90W180_surface.nc",
            "earth/ETOPO_2022_v1_60s_N90W180_surface.nc",
        )],
        landing="https://www.ncei.noaa.gov/products/etopo-global-relief-model",
    ),
    Source(
        "earth_merra2", "earth", "NASA POWER v10 climatology of MERRA-2 (0.5 x 0.625 degree)",
        "Mean surface temperature, day-night range, rainfall, snow cover",
        "NASA LaRC POWER / NASA GMAO MERRA-2", True, "NASA open data (CC0-style, see POWER LICENSE.txt)",
        zarr=(
            f"{POWER}/merra2/temporal/power_merra2_climatology_temporal_utc.zarr",
            ["TS", "TS_MAX_AVG", "TS_MIN_AVG", "PRECTOTCORR_SUM", "FRSNO"],
        ),
        landing="https://power.larc.nasa.gov",
        note="Replaces the MODIS NEO archive, which NASA decommissioned in September 2026.",
    ),
    Source(
        "earth_ceres", "earth", "NASA POWER v10 climatology of CERES SYN1deg (1 degree)",
        "Albedo", "NASA LaRC POWER / NASA CERES", True, "NASA open data (see POWER LICENSE.txt)",
        zarr=(
            f"{POWER}/syn1deg/temporal/power_syn1deg_climatology_temporal_utc.zarr",
            ["ALLSKY_SRF_ALB"],
        ),
        landing="https://power.larc.nasa.gov",
        note="Replaces MODIS albedo from the decommissioned NEO archive.",
    ),
    Source(
        "earth_ndvi", "earth", "MODIS/Terra MOD13C2 monthly NDVI, 0.1 degree (NEO float GeoTIFF)",
        "Barren-land filter, passport", "NASA (MODIS, via NASA Earth Observations)", True,
        "NASA open data",
        files=[(WAYBACK.format(ts=ts, name=name), f"earth/ndvi/{name}") for ts, name in NDVI_FILES],
        landing="https://science.nasa.gov/earth/nasa-earth-observations-neo/",
        note="NEO was decommissioned in September 2026. These are Internet Archive copies of the "
             "original NASA files, one per calendar month.",
    ),
    Source(
        "earth_land", "earth", "Natural Earth 1:50m land polygons", "Land mask",
        "Natural Earth", False, "Public domain",
        files=[("https://naciscdn.org/naturalearth/50m/physical/ne_50m_land.zip", "earth/ne_50m_land.zip")],
        landing="https://www.naturalearthdata.com",
    ),
    Source(
        "earth_places", "earth", "Natural Earth 1:10m populated places", "Hometown search",
        "Natural Earth", False, "Public domain",
        files=[(
            "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places_simple.zip",
            "earth/ne_10m_populated_places_simple.zip",
        )],
        landing="https://www.naturalearthdata.com",
    ),
    Source(
        "earth_texture", "earth", "Blue Marble: Shaded Relief and Bathymetry (NASA GIBS)",
        "Globe texture (display only)", "NASA GIBS / NASA Earth Observatory", True, "NASA open data",
        files=[(GIBS_BLUE_MARBLE, "textures/earth_blue_marble_4096.jpg")],
        landing="https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api",
    ),
    # ---- Mars
    Source(
        "mars_elevation", "mars", "MGS MOLA MEGDR topography, 16 pixels per degree (megt90n000eb)",
        "Slope, relief", "NASA PDS Geosciences Node", True, "Public domain (NASA PDS)",
        files=[
            (f"{PDS}/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/megt90n000eb.img", "mars/megt90n000eb.img"),
            (f"{PDS}/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/megt90n000eb.lbl", "mars/megt90n000eb.lbl"),
        ],
        landing="https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
    ),
    Source(
        "mars_albedo", "mars", "MGS TES bolometric albedo global mosaic, 7.4 km",
        "Albedo", "USGS Astrogeology / NASA MGS TES", True, "Public domain",
        files=[(
            "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif",
            "mars/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif",
        )],
        landing="https://astrogeology.usgs.gov/search/map/mars_mgs_tes_albedo_global_mosaic_7410m",
    ),
    Source(
        "mars_temperature", "mars",
        "NASA Ames Legacy Mars Global Climate Model reference simulation (active clouds), 5 x 6 degree",
        "Mean surface temperature, day-night range", "NASA Ames Mars Climate Modeling Center", True,
        "Public domain (NASA)",
        files=[(f"{NAS}/{name}", f"mars/legacygcm/{name}") for name in LEGACY_GCM_FILES],
        landing="https://data.nas.nasa.gov/mcmcref/legacygcm/",
        note="Model output, not an observation. Chosen over OpenMARS (CC BY-NC-ND, which does not "
             "allow sharing derived maps). 12 of 67 ten-sol files, evenly spaced over the Mars year.",
    ),
    Source(
        "mars_texture", "mars", "Viking MDIM 2.1 colour mosaic (NASA Solar System Treks tiles)",
        "Globe texture (display only)", "NASA Solar System Treks / USGS Astrogeology", True, "Public domain",
        files=_tiles(MARS_TILE_LAYER, "textures/mars_tiles"),
        landing="https://trek.nasa.gov/mars/",
    ),
    # ---- Moon
    Source(
        "moon_elevation", "moon", "LRO LOLA gridded elevation, 16 pixels per degree (LDEM_16)",
        "Slope, relief", "NASA PDS Geosciences Node", True, "Public domain (NASA PDS)",
        files=[
            (f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img", "moon/ldem_16.img"),
            (f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.lbl", "moon/ldem_16.lbl"),
        ],
        landing="https://pds-geosciences.wustl.edu/missions/lro/lola.htm",
    ),
    Source(
        "moon_temperature", "moon", "LRO Diviner Global Cumulative Products, 0.5 degree by local time",
        "Mean surface temperature, day-night range", "NASA PDS Geosciences Node (UCLA Diviner team)", True,
        "Public domain (NASA PDS)",
        files=[
            (
                f"{PDS}/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/global_cumul_avg_cyl_{band}_002.tab",
                f"moon/diviner_gcp/global_cumul_avg_cyl_{band}_002.tab",
            )
            for band in DIVINER_BANDS
        ],
        landing="https://pds-geosciences.wustl.edu/missions/lro/diviner.htm",
    ),
    Source(
        "moon_albedo", "moon", "LRO LOLA 1064 nm normal albedo, 4 pixels per degree (LDAM_4)",
        "Albedo", "NASA PDS Geosciences Node", True, "Public domain (NASA PDS)",
        files=[
            (f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/float_img/ldam_4_float.img", "moon/ldam_4_float.img"),
            (f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/float_img/ldam_4_float.lbl", "moon/ldam_4_float.lbl"),
        ],
        landing="https://pds-geosciences.wustl.edu/missions/lro/lola.htm",
        note="Normal albedo at one laser wavelength (1064 nm), not broadband. Stated on the methods page.",
    ),
    Source(
        "moon_texture", "moon", "LROC WAC colour map (NASA SVS CGI Moon Kit), 4k",
        "Globe texture (display only)", "NASA Scientific Visualization Studio", True, "Public domain (NASA)",
        files=[(
            "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_4k.tif",
            "textures/lroc_color_poles_4k.tif",
        )],
        landing="https://svs.gsfc.nasa.gov/4720",
    ),
]


def _get(url: str, **kw) -> requests.Response:
    last: Exception | None = None
    for attempt in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=(20, 120), **kw)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code}")
            r.close()
        except requests.RequestException as e:  # network hiccup, retry
            last = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def probe(url: str) -> tuple[bool, str]:
    """Return (ok, size text) for a URL without downloading the body."""
    try:
        r = _get(url, stream=True)
        size = r.headers.get("Content-Length")
        r.close()
        return True, f"{int(size):,} bytes" if size else "size not reported"
    except RuntimeError as e:
        return False, str(e)


def check() -> int:
    failed = 0
    for s in SOURCES:
        if s.zarr:
            targets = [s.zarr[0] + "/.zmetadata"]
        elif len(s.files) > 20:  # tile sets: first, middle and last tile
            targets = [s.files[0][0], s.files[len(s.files) // 2][0], s.files[-1][0]]
        else:
            targets = [u for u, _ in s.files]
        with ThreadPoolExecutor(6) as pool:
            results = list(pool.map(probe, targets))
        ok = all(r[0] for r in results)
        failed += not ok
        total = sum(int(r[1].split()[0].replace(",", "")) for r in results if r[0] and r[1][0].isdigit())
        detail = f"{len(targets)} url(s), {total:,} bytes reported" if ok else "; ".join(r[1] for r in results if not r[0])
        print(f"{'OK  ' if ok else 'FAIL'} {s.key:18s} {detail}")
    print("all sources OK" if not failed else f"{failed} source(s) FAILED")
    return 1 if failed else 0


def _download_file(item: tuple[str, str]) -> str:
    """Fetch one file with curl, which these servers serve far faster than Python's HTTP stack."""
    import subprocess

    url, rel = item
    dest = RAW / rel
    if dest.exists() and dest.stat().st_size > 0:
        return f"have {rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    cmd = ["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "5", "--retry-all-errors",
           "--retry-delay", "5", "--connect-timeout", "30", "--user-agent", UA["User-Agent"],
           "--output", str(tmp), url]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        return f"FAIL {rel}: {run.stderr.strip() or 'empty file'}"
    tmp.rename(dest)
    return f"got  {rel} ({dest.stat().st_size:,} bytes)"


def _download_zarr(s: Source) -> str:
    import xarray as xr

    dest = RAW / "earth" / f"{s.key}.nc"
    if dest.exists():
        return f"have {dest.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    store, variables = s.zarr
    ds = xr.open_zarr(store, consolidated=True)[variables].load()
    ds.attrs = {"source": store, "title": s.title}
    ds.to_netcdf(dest)
    return f"got  earth/{dest.name} ({dest.stat().st_size:,} bytes)"


def download(only: list[str] | None = None) -> int:
    failed = 0
    for s in SOURCES:
        if only and s.key not in only:
            continue
        if s.zarr:
            try:
                results = [_download_zarr(s)]
            except Exception as e:  # report and carry on with the other sources
                results = [f"FAIL {s.key}: {e}"]
        else:
            workers = 8 if len(s.files) > 20 else 3
            with ThreadPoolExecutor(workers) as pool:
                results = list(pool.map(_download_file, s.files))
        bad = [r for r in results if r.startswith("FAIL")]
        failed += len(bad)
        print(f"{s.key}: {len(results) - len(bad)}/{len(results)} files", flush=True)
        for r in bad:
            print("  " + r, flush=True)
    write_manifest()
    return 1 if failed else 0


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest() -> None:
    """Record size, checksum and download date of every raw file."""
    path = RAW / "manifest.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    out = {}
    for s in SOURCES:
        rels = [f"earth/{s.key}.nc"] if s.zarr else [rel for _, rel in s.files]
        urls = [s.zarr[0]] if s.zarr else [u for u, _ in s.files]
        for url, rel in zip(urls, rels):
            p = RAW / rel
            if not p.exists():
                continue
            prev = old.get(rel, {})
            size = p.stat().st_size
            if prev.get("bytes") == size:
                out[rel] = prev
            else:
                out[rel] = {
                    "source": s.key, "url": url, "bytes": size, "sha256": _sha256(p),
                    "downloaded": date.fromtimestamp(p.stat().st_mtime).isoformat(),
                }
    path.write_text(json.dumps(out, indent=1))
    print(f"manifest: {len(out)} files, {sum(v['bytes'] for v in out.values()) / 1e9:.2f} GB")


def write_docs() -> None:
    """Write DATA_SOURCES.md from the source list and the download manifest."""
    manifest = json.loads((RAW / "manifest.json").read_text())

    def table(nasa: bool) -> str:
        lines = ["| Dataset | World | Used for | Provider | Files | Size | Downloaded | Licence |",
                 "|---|---|---|---|---|---|---|---|"]
        for s in SOURCES:
            if s.nasa != nasa:
                continue
            mine = [v for v in manifest.values() if v["source"] == s.key]
            size = sum(v["bytes"] for v in mine)
            when = max((v["downloaded"] for v in mine), default="not downloaded")
            size_text = f"{size / 1e6:,.1f} MB" if size < 1e9 else f"{size / 1e9:.2f} GB"
            lines.append(f"| [{s.title}]({s.landing}) | {s.world.title()} | {s.used_for} | {s.agency} | "
                         f"{len(mine)} | {size_text} | {when} | {s.licence} |")
        return "\n".join(lines)

    notes = "\n".join(f"- **{s.title}:** {s.note}" for s in SOURCES if s.note)
    urls = "\n".join(
        f"- `{s.key}`: {s.zarr[0] if s.zarr else s.files[0][0]}"
        + ("" if s.zarr or len(s.files) == 1 else f" (first of {len(s.files)} files; full list in `pipeline/sources.py`)")
        for s in SOURCES)
    total = sum(v["bytes"] for v in manifest.values()) / 1e9
    text = f"""# Data sources

Every dataset used by Planet Twin. This file is written by `python -m pipeline.sources docs`
from `pipeline/sources.py` and the download manifest (`data/raw/manifest.json`, which also holds
a SHA-256 checksum for every file). Total download: {total:.2f} GB in {len(manifest)} files.

## NASA data

{table(True)}

## Other data

{table(False)}

## Changes from the original plan, and why

{notes}
- **Earth temperature, albedo, rainfall and snow** were planned from MODIS and IMERG layers in the NASA Earth
  Observations (NEO) archive. NASA decommissioned NEO in September 2026 and its archive now redirects to a
  notice page. The replacement is NASA POWER, which serves NASA's MERRA-2 reanalysis and CERES products with
  no login. These grids are coarser (about 55 km for temperature, 110 km for albedo) than the 30 km cells.
- **No dataset needed an Earthdata login**, and none was worked around.

## Download addresses

{urls}
"""
    (RAW.parent.parent / "DATA_SOURCES.md").write_text(text)
    print("wrote DATA_SOURCES.md")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        sys.exit(check())
    if cmd == "download":
        sys.exit(download(sys.argv[2:] or None))
    if cmd == "manifest":
        write_manifest()
    elif cmd == "docs":
        write_docs()
    else:
        sys.exit(f"unknown command {cmd}")
