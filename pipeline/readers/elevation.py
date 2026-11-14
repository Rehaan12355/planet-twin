"""Elevation readers. Each returns a north-up lat-lon array in metres."""

from __future__ import annotations

import numpy as np

from ..sources import RAW

MOLA_VALID = (-8177, 21171)  # from the PDS label


def read_mola() -> np.ndarray:
    """MOLA MEGDR 16 ppd topography. 2880 x 5760, lon 0..360 E, 90 N at the top."""
    z = np.fromfile(RAW / "mars/megt90n000eb.img", dtype=">i2").reshape(2880, 5760)
    assert MOLA_VALID[0] <= z.min() and z.max() <= MOLA_VALID[1], (z.min(), z.max())
    return z.astype(np.float32)


def read_lola() -> np.ndarray:
    """LOLA LDEM_16 height above the 1737.4 km sphere. 2880 x 5760, lon 0..360 E."""
    dn = np.fromfile(RAW / "moon/ldem_16.img", dtype="<i2").reshape(2880, 5760)
    return dn.astype(np.float32) * 0.5


def read_etopo() -> np.ndarray:
    """ETOPO 2022 60 arc-second surface elevation, flipped north-up. lon -180..180."""
    import netCDF4

    with netCDF4.Dataset(RAW / "earth/ETOPO_2022_v1_60s_N90W180_surface.nc") as nc:
        lat = nc["lat"][:]
        z = np.asarray(nc["z"][:], dtype=np.float32)
    assert z.shape == (10800, 21600), z.shape
    return z[::-1] if lat[0] < lat[-1] else z
