"""Earth temperature, albedo, rainfall, snow and vegetation readers.

Each returns (values, latitudes, longitudes) on the source grid, north to south
or south to north as stored; grid.regrid_bilinear handles either.
"""

from __future__ import annotations

import glob

import numpy as np
import xarray as xr

from ..sources import RAW

KELVIN = 273.15


def _merra2() -> xr.Dataset:
    return xr.open_dataset(RAW / "earth/earth_merra2.nc")


def read_temperature() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Mean skin temperature (K) and mean day-night range (K) from MERRA-2.

    The range is the yearly mean of (average daily maximum - average daily minimum).
    The first 12 time steps are the months; step 13 is the dataset's own annual value.
    """
    ds = _merra2().isel(time=slice(0, 12))
    mean = ds.TS.mean("time").values + KELVIN
    swing = (ds.TS_MAX_AVG - ds.TS_MIN_AVG).mean("time").values
    return mean.astype(np.float32), swing.astype(np.float32), ds.lat.values, ds.lon.values


def read_rain() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Yearly precipitation in mm (sum of the twelve monthly totals)."""
    ds = _merra2().isel(time=slice(0, 12))
    return ds.PRECTOTCORR_SUM.sum("time").values.astype(np.float32), ds.lat.values, ds.lon.values


def read_snow() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Share of the year with snow on the ground, 0 to 1.

    MERRA-2 leaves the snow fraction empty over permanent land ice and open
    water. Those gaps are filled with 1 where the yearly mean skin temperature
    is below 263 K (ice sheets) and 0 elsewhere.
    """
    ds = _merra2().isel(time=slice(0, 12))
    snow = ds.FRSNO.mean("time").values
    cold = (ds.TS.mean("time").values + KELVIN) < 263.0
    snow = np.where(np.isnan(snow), cold.astype(np.float32), snow)
    return snow.astype(np.float32), ds.lat.values, ds.lon.values


def read_albedo() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Yearly mean all-sky surface albedo from CERES SYN1deg. Polar-night months are skipped."""
    ds = xr.open_dataset(RAW / "earth/earth_ceres.nc").isel(time=slice(0, 12))
    with np.errstate(invalid="ignore"):
        alb = np.nanmean(ds.ALLSKY_SRF_ALB.values, axis=0)
    return alb.astype(np.float32), ds.lat.values, ds.lon.values


def read_ndvi() -> tuple[np.ndarray, int]:
    """Mean MODIS NDVI over the archived monthly composites. 1800 x 3600, north-up, lon -180..180.

    Returns the grid and the number of months that went into it.
    """
    import rasterio

    files = sorted(glob.glob(str(RAW / "earth/ndvi/*.tif")))
    stack = []
    for f in files:
        with rasterio.open(f) as r:
            a = r.read(1)
        assert a.shape == (1800, 3600), (f, a.shape)
        stack.append(a)
    with np.errstate(invalid="ignore"):
        return np.nanmean(np.stack(stack), axis=0).astype(np.float32), len(files)
