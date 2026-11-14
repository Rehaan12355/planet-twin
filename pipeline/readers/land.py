"""Land mask from Natural Earth polygons."""

from __future__ import annotations

import numpy as np

from ..sources import RAW


def land_fraction(rows: int, cols: int) -> np.ndarray:
    """Fraction-free land mask (1 land, 0 water) on a north-up grid, lon -180..180."""
    import shapefile  # pyshp
    from rasterio import features
    from rasterio.transform import from_origin

    reader = shapefile.Reader(str(RAW / "earth/ne_50m_land.zip"))
    shapes = [s.__geo_interface__ for s in reader.shapes()]
    transform = from_origin(-180.0, 90.0, 360.0 / cols, 180.0 / rows)
    return features.rasterize(shapes, out_shape=(rows, cols), transform=transform, dtype="uint8")
