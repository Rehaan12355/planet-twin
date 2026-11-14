"""Slope and relief from elevation grids.

Slope is measured on a fine grid of about 3.7 km on every world, then
summarised to the ~30 km cells: mean slope in degrees and local relief
(highest minus lowest elevation in the cell) as log10 of metres.
"""

from __future__ import annotations

import numpy as np


def slope_degrees(z: np.ndarray, radius_km: float) -> np.ndarray:
    """Slope of a global north-up lat-lon elevation grid, in degrees.

    The east-west pixel size shrinks with the cosine of latitude.
    Longitude wraps around; the top and bottom rows use one-sided differences.
    """
    rows, cols = z.shape
    step = np.pi / rows  # radians per pixel, same in both directions
    metres = radius_km * 1000.0 * step
    lat = np.pi / 2 - (np.arange(rows) + 0.5) * step
    coslat = np.maximum(np.cos(lat), 1e-6)[:, None]
    z = z.astype(np.float32)
    dzdx = (np.roll(z, -1, axis=1) - np.roll(z, 1, axis=1)) / (2 * metres * coslat)
    dzdy = np.gradient(z, metres, axis=0)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy))).astype(np.float32)


def _split_cells(a: np.ndarray, cell_rows: int, cell_cols: int):
    """Yield (cell row slice, block) where block is (n, fy, cell_cols, fx) half-pixels.

    The fine grid need not divide evenly into cells (Earth has 7.5 fine pixels
    per cell), so each fine pixel is split in two along both axes first.
    """
    rows, cols = a.shape
    fy, fx = 2 * rows // cell_rows, 2 * cols // cell_cols
    assert fy * cell_rows == 2 * rows and fx * cell_cols == 2 * cols
    band = fy if fy % 2 == 0 else 2 * fy  # half-rows per strip; keep it even
    for r0 in range(0, 2 * rows, band):
        n = band // fy
        fine = a[r0 // 2 : (r0 + band) // 2]
        block = np.repeat(np.repeat(fine, 2, axis=0), 2, axis=1).reshape(n, fy, cell_cols, fx)
        yield slice(r0 // fy, r0 // fy + n), block


def cell_mean(a: np.ndarray, cell_rows: int, cell_cols: int) -> np.ndarray:
    """Mean of a fine grid over each cell."""
    out = np.empty((cell_rows, cell_cols), np.float32)
    for cr, block in _split_cells(a, cell_rows, cell_cols):
        out[cr] = block.mean(axis=(1, 3))
    return out


def summarise(slope: np.ndarray, z: np.ndarray, cell_rows: int, cell_cols: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean slope (degrees) and local relief (log10 of metres) per cell."""
    relief = np.empty((cell_rows, cell_cols), np.float32)
    for cr, block in _split_cells(z, cell_rows, cell_cols):
        relief[cr] = block.max(axis=(1, 3)) - block.min(axis=(1, 3))
    return cell_mean(slope, cell_rows, cell_cols), np.log10(np.maximum(relief, 1.0)).astype(np.float32)
