"""Grid helpers shared by every world.

Cell grids are simple cylindrical, north at the top. Row 0 touches 90 N.
Column 0 starts at lon0: -180 for Earth, 0 for Mars and the Moon (east positive).
"""

from __future__ import annotations

import numpy as np

from . import config

LON0 = {"earth": -180.0, "mars": 0.0, "moon": 0.0}


def cell_centres(world: str) -> tuple[np.ndarray, np.ndarray]:
    """Latitudes (rows) and longitudes (cols) of cell centres, in degrees."""
    w = config.WORLDS[world]
    lat = 90.0 - (np.arange(w["rows"]) + 0.5) * w["cell_deg"]
    lon = LON0[world] + (np.arange(w["cols"]) + 0.5) * w["cell_deg"]
    return lat, lon


def cell_index(world: str, lat: float, lon: float) -> int:
    """Flat index of the cell containing a point. Longitude may be in any convention."""
    w = config.WORLDS[world]
    row = min(int((90.0 - lat) / w["cell_deg"]), w["rows"] - 1)
    col = int(((lon - LON0[world]) % 360.0) / w["cell_deg"]) % w["cols"]
    return row * w["cols"] + col


def block_reduce(a: np.ndarray, factor: int, func=np.nanmean) -> np.ndarray:
    """Reduce a 2-D array by an integer factor with the given statistic."""
    rows, cols = a.shape[0] // factor, a.shape[1] // factor
    blocks = a[: rows * factor, : cols * factor].reshape(rows, factor, cols, factor)
    return func(func(blocks, axis=3), axis=1)


def regrid_bilinear(src: np.ndarray, src_lat: np.ndarray, src_lon: np.ndarray,
                    dst_lat: np.ndarray, dst_lon: np.ndarray) -> np.ndarray:
    """Bilinear resample of a coarse lat-lon grid onto cell centres.

    Longitude wraps; latitude clamps at the poles. Missing source values are
    left out of the blend; a cell is missing only when most of its weight is.
    """
    from scipy.ndimage import map_coordinates

    if src_lat[0] > src_lat[-1]:  # make latitude ascending
        src, src_lat = src[::-1], src_lat[::-1]
    dlat = src_lat[1] - src_lat[0]
    dlon = src_lon[1] - src_lon[0]
    y = np.clip((dst_lat - src_lat[0]) / dlat, 0, len(src_lat) - 1)
    x = ((dst_lon - src_lon[0]) % 360.0) / dlon
    yy, xx = np.meshgrid(y, x, indexing="ij")
    good = np.isfinite(src)
    weight = map_coordinates(good.astype(np.float32), [yy, xx], order=1, mode="grid-wrap")
    value = map_coordinates(np.where(good, src, 0).astype(np.float32), [yy, xx], order=1, mode="grid-wrap")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(weight > 0.5, value / weight, np.nan).astype(np.float32)


def weighted_quantiles(values: np.ndarray, weights: np.ndarray, n: int = 101) -> list[float]:
    """Area-weighted quantiles (0th to 100th percentile) of the finite values."""
    ok = np.isfinite(values)
    v, w = values[ok], weights[ok]
    order = np.argsort(v)
    v, w = v[order], w[order]
    cum = (np.cumsum(w) - 0.5 * w) / w.sum()
    return [float(x) for x in np.interp(np.linspace(0, 1, n), cum, v)]


def area_weights(world: str) -> np.ndarray:
    """Relative surface area of each cell row (cosine of latitude)."""
    lat, _ = cell_centres(world)
    return np.cos(np.radians(lat))
