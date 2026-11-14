"""Shared constants: world radii, grids, features and tolerances."""

WORLDS = {
    "earth": {"radius_km": 6371.0, "cell_deg": 0.25, "cols": 1440, "rows": 720, "fine_ppd": 30},
    "mars": {"radius_km": 3389.5, "cell_deg": 0.5, "cols": 720, "rows": 360, "fine_ppd": 16},
    "moon": {"radius_km": 1737.4, "cell_deg": 1.0, "cols": 360, "rows": 180, "fine_ppd": 8},
}

# Cells poleward of this latitude are flagged low confidence.
LOW_CONFIDENCE_LAT = 85.0

# Tolerances are first guesses. Tune only against the validation test,
# and record any change in docs/methods.md.
FEATURES = [
    {"name": "mean_slope", "unit": "deg", "tolerance": 2.0},
    {"name": "local_relief", "unit": "log10 m", "tolerance": 0.25},
    {"name": "mean_temp", "unit": "K", "tolerance": 15.0},
    {"name": "diurnal_range", "unit": "K", "tolerance": 15.0},
    {"name": "albedo", "unit": "", "tolerance": 0.05},
]

PRESETS = {
    "balanced": {"terrain": 1.0, "temperature": 1.0, "albedo": 1.0},
    "terrain": {"terrain": 3.0, "temperature": 0.5, "albedo": 0.5},
    "thermal": {"terrain": 0.5, "temperature": 3.0, "albedo": 1.0},
}

# Relative (hometown) mode tolerance, in percentile points.
RELATIVE_TOLERANCE = 10.0

# Top matches must be at least this far apart.
MIN_MATCH_SEPARATION_KM = 300.0
