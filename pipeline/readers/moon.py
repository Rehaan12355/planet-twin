"""Moon temperature and albedo readers."""

from __future__ import annotations

import glob

import numpy as np

from ..sources import RAW


def read_lola_albedo() -> np.ndarray:
    """LOLA 1064 nm normal albedo, 720 x 1440 (4 ppd), north-up, lon 0..360 E."""
    a = np.fromfile(RAW / "moon/ldam_4_float.img", dtype="<f4").reshape(720, 1440)
    a[(a <= 0) | (a > 1)] = np.nan
    return a


def read_diviner() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Diviner bolometric temperature: mean, maximum and minimum over the lunar day (K).

    Returns three 360 x 720 grids (0.5 degree bins), north-up, lon 0..360 E.
    Each table row is one latitude, longitude and local-time bin (0.25 h). Bins are
    first averaged per hour, gaps in local time are filled from neighbouring hours,
    and the mean is taken over the 24 hours so day and night weigh equally.
    """
    import pandas as pd

    hourly = np.full((360, 720, 24), np.nan, np.float32)
    for f in sorted(glob.glob(str(RAW / "moon/diviner_gcp/*.tab"))):
        df = pd.read_csv(f, usecols=[0, 1, 2, 10], names=["clon", "clat", "ltim", "tbol"], header=0,
                         skipinitialspace=True, dtype=np.float32)
        df = df[df.tbol > 0]
        row = np.floor((90.0 - df.clat.values) / 0.5).astype(int).clip(0, 359)
        col = np.floor((df.clon.values % 360.0) / 0.5).astype(int) % 720
        hour = np.floor(df.ltim.values).astype(int) % 24
        g = df.tbol.groupby([row, col, hour]).mean()
        r, c, h = (g.index.get_level_values(i).values for i in range(3))
        hourly[r, c, h] = g.values
    for _ in range(12):  # fill missing hours from their neighbours, wrapping at midnight
        gap = np.isnan(hourly)
        if not gap.any():
            break
        with np.errstate(invalid="ignore"):
            fill = np.nanmean(np.stack([np.roll(hourly, 1, axis=2), np.roll(hourly, -1, axis=2)]), axis=0)
        hourly[gap] = fill[gap]
    with np.errstate(invalid="ignore"):
        return np.nanmean(hourly, axis=2), np.nanmax(hourly, axis=2), np.nanmin(hourly, axis=2)
