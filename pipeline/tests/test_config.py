from pipeline import config


def test_cell_widths_are_about_30_km():
    import math

    for world in config.WORLDS.values():
        width = 2 * math.pi * world["radius_km"] * world["cell_deg"] / 360
        assert 27 < width < 31
        assert world["cols"] * world["cell_deg"] == 360
        assert world["rows"] * world["cell_deg"] == 180
