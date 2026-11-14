import numpy as np

from pipeline import grid, terrain


def test_slope_of_a_north_south_ramp():
    # 1 degree of latitude is ~59.16 km on Mars; climb 1000 m per degree.
    rows, cols = 180 * 16, 360 * 16
    lat = 90 - (np.arange(rows) + 0.5) / 16
    z = np.repeat((lat * 1000.0)[:, None], cols, axis=1).astype(np.float32)
    s = terrain.slope_degrees(z, 3389.5)
    expected = np.degrees(np.arctan(1000.0 / (np.pi * 3389.5e3 / 180)))
    assert abs(s[rows // 2, 100] - expected) < 0.01


def test_east_west_slope_uses_cosine_of_latitude():
    rows, cols = 180 * 8, 360 * 8
    lon = (np.arange(cols) + 0.5) / 8
    z = np.repeat((np.sin(np.radians(lon)) * 5000.0)[None, :], rows, axis=0).astype(np.float32)
    s = terrain.slope_degrees(z, 1737.4)
    equator, sixty = s[rows // 2, 0], s[rows // 6, 0]  # lat ~0 and ~60 N, lon ~0
    assert abs(np.tan(np.radians(sixty)) / np.tan(np.radians(equator)) - 2.0) < 0.05


def test_summarise_handles_seven_and_a_half_pixels_per_cell():
    rows, cols = 180 * 30, 360 * 30  # Earth 2 arc-minute grid
    z = np.zeros((rows, cols), np.float32)
    z[0:7, 0:7] = 1000.0  # sits wholly inside cell (0, 0)
    slope = np.ones((rows, cols), np.float32)
    mean_slope, relief = terrain.summarise(slope, z, 720, 1440)
    assert mean_slope.shape == (720, 1440) and np.allclose(mean_slope, 1.0)
    assert abs(relief[0, 0] - 3.0) < 1e-6 and relief[5, 5] == 0.0


def test_cell_index_conventions():
    # Olympus Mons 18.65 N, 226.2 E on the 0.5 degree Mars grid.
    i = grid.cell_index("mars", 18.65, 226.2)
    assert divmod(i, 720) == (142, 452)
    assert grid.cell_index("mars", 18.65, 226.2 - 360) == i
    # Earth uses -180..180: Greenwich sits in the middle column.
    assert grid.cell_index("earth", 0.1, 0.1) % 1440 == 720


def test_bilinear_regrid_wraps_longitude():
    src_lat = np.arange(-90, 91, 30.0)
    src_lon = np.arange(-180, 180, 90.0)
    src = np.tile(src_lon, (len(src_lat), 1)).astype(np.float32)
    out = grid.regrid_bilinear(src, src_lat, src_lon, np.array([0.0]), np.array([-180.0, -135.0, 135.0]))
    assert np.allclose(out[0, :2], [-180.0, -135.0])
    assert -180.0 < out[0, 2] < 90.0  # blends 90 with the wrapped -180 column
