"""Mars albedo and temperature readers."""

from __future__ import annotations

import glob

import numpy as np

from ..sources import RAW


def read_tes_albedo() -> np.ndarray:
    """TES bolometric albedo, 1440 x 2880 (8 ppd), north-up, shifted to lon 0..360 E.

    The USGS mosaic is centred on longitude 0, so its halves are swapped here.
    """
    import rasterio

    with rasterio.open(RAW / "mars/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif") as r:
        a = r.read(1).astype(np.float32)
        nodata = r.nodata
    assert a.shape == (1440, 2880), a.shape
    if nodata is not None:
        a[a == nodata] = np.nan
    return np.roll(a, a.shape[1] // 2, axis=1)


def read_legacy_gcm() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Mean surface temperature and mean day-night range (K) from the NASA Ames Legacy Mars GCM.

    Each file holds ten sols at 16 times of day. The range is the mean over sols
    of (warmest time of day - coldest time of day). Returns the two grids, their
    latitudes and longitudes, and the number of sols used.
    """
    import netCDF4

    total = swing = None
    sols = 0
    for f in sorted(glob.glob(str(RAW / "mars/legacygcm/LegacyGCM_*.nc"))):
        with netCDF4.Dataset(f) as nc:
            t = np.asarray(nc["tsurf"][:], dtype=np.float64)  # (sol, time of day, lat, lon)
            lat = np.asarray(nc["latitude"][:])
            lon = np.asarray(nc["longitude"][:])
        assert t.ndim == 4, t.shape
        mean = t.mean(axis=1).sum(axis=0)
        rng = (t.max(axis=1) - t.min(axis=1)).sum(axis=0)
        total = mean if total is None else total + mean
        swing = rng if swing is None else swing + rng
        sols += t.shape[0]
    return (total / sols).astype(np.float32), (swing / sols).astype(np.float32), lat, lon, sols
