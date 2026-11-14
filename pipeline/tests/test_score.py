import numpy as np

from pipeline import config, grid, validate


class FakeWorld:
    groups = ["terrain", "terrain", "temperature", "temperature", "albedo"]
    tolerance = np.array([f["tolerance"] for f in config.FEATURES], np.float32)

    def __init__(self, features):
        self.features = np.array(features, np.float32)


def test_identical_cell_scores_100():
    w = FakeWorld([[3.0, 2.5, 210.0, 60.0, 0.25], [9.0, 3.5, 290.0, 12.0, 0.1]])
    s = validate.score(w, w.features[0], config.PRESETS["balanced"])
    assert abs(s[0] - 100) < 1e-4 and s[1] < 10


def test_one_tolerance_off_on_every_feature_scores_61():
    target = np.array([3.0, 2.5, 210.0, 60.0, 0.25], np.float32)
    w = FakeWorld([target + FakeWorld.tolerance])
    assert abs(validate.score(w, target, config.PRESETS["balanced"])[0] - 100 * np.exp(-0.5)) < 1e-3


def test_missing_feature_is_skipped_not_scored_as_zero():
    target = np.array([3.0, 2.5, 210.0, 60.0, 0.25], np.float32)
    w = FakeWorld([[3.0, 2.5, 210.0, 60.0, np.nan]])
    assert abs(validate.score(w, target, config.PRESETS["balanced"])[0] - 100) < 1e-4
    target[4] = np.nan  # missing on the target side behaves the same way
    assert abs(validate.score(FakeWorld([[3.0, 2.5, 210.0, 60.0, 0.9]]), target, config.PRESETS["balanced"])[0] - 100) < 1e-4


def test_presets_change_the_ranking():
    target = np.array([3.0, 2.5, 210.0, 60.0, 0.25], np.float32)
    w = FakeWorld([[3.0, 2.5, 250.0, 20.0, 0.25],   # right terrain, wrong temperature
                   [9.0, 3.4, 210.0, 60.0, 0.25]])  # right temperature, wrong terrain
    terrain = validate.score(w, target, config.PRESETS["terrain"])
    thermal = validate.score(w, target, config.PRESETS["thermal"])
    assert terrain[0] > terrain[1] and thermal[1] > thermal[0]


def test_weighted_quantiles_follow_area():
    q = grid.weighted_quantiles(np.array([0.0, 10.0]), np.array([3.0, 1.0]), n=5)
    assert q[0] == 0.0 and q[-1] == 10.0 and q[2] < 5.0
