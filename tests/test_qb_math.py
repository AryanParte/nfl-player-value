"""Independent dense observation-space references, not NFL validation claims."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np

from nfl_value.qb_math import (
    RestrictedLikelihood,
    contrast,
    design,
    fit,
    identification,
    predict,
    row_features,
)
from test_baseline import play


def plan():
    return json.loads((Path(__file__).parents[1] / "config/qb-recovery-v1.json").read_text())


def rows():
    result = [play(week=w, i=i) for w in (1, 2, 3) for i in range(1, 21)]
    rng = np.random.default_rng(12)
    for row in result:
        row["context"].update(
            ydstogo=int(rng.integers(1, 35)),
            yardline_100=int(rng.integers(1, 100)),
            game_seconds_remaining=int(rng.integers(0, 3601)),
            score_differential=int(rng.integers(-28, 29)),
            qtr=int(rng.integers(1, 6)),
        )
        row["qb"] = row["actors"]["dropback"]
    return result


class QBMathTests(unittest.TestCase):
    def test_reml_and_posterior_equal_dense_marginal_gls(self):
        d = design(rows(), "joint", extra_qbs=["00-9999999"])
        y = np.random.default_rng(5).normal(size=len(d.x))
        ratios = np.array([3.0, 7.0, 11.0, 13.0])
        objective, gradient, mean, covariance, sigma2 = RestrictedLikelihood(d, y).solve(
            np.log(ratios)
        )
        f, z = d.x[:, : d.fixed_count], d.x[:, d.fixed_count :]
        penalties = np.zeros(len(d.names))
        for ratio, indices in zip(ratios, d.group_indices):
            penalties[indices] = ratio
        g = np.diag(1 / penalties[d.fixed_count :])
        v = np.eye(len(y)) + z @ g @ z.T
        vi = np.linalg.inv(v)
        ft = f.T @ vi @ f
        beta = np.linalg.solve(ft, f.T @ vi @ y)
        residual = y - f @ beta
        b = g @ z.T @ vi @ residual
        q = residual @ vi @ residual
        expected = (
            (len(y) - f.shape[1]) * np.log(q / (len(y) - f.shape[1]))
            + np.linalg.slogdet(v)[1]
            + np.linalg.slogdet(ft)[1]
        )
        self.assertAlmostEqual(objective, expected, places=9)
        np.testing.assert_allclose(mean, np.r_[beta, b], atol=1e-9)
        # Marginal conditional covariance including uncertain fixed effects.
        b_cov = g - g @ z.T @ vi @ z @ g + g @ z.T @ vi @ f @ np.linalg.inv(ft) @ f.T @ vi @ z @ g
        np.testing.assert_allclose(
            covariance[d.fixed_count :, d.fixed_count :], sigma2 * b_cov, atol=1e-10
        )
        cold = d.names.index("qb/00-9999999")
        self.assertAlmostEqual(mean[cold], 0)
        self.assertAlmostEqual(covariance[cold, cold], sigma2 / ratios[0])
        self.assertTrue(np.isfinite(gradient).all())

    def test_analytic_gradient_matches_independent_central_difference(self):
        d = design(rows(), "joint")
        ll = RestrictedLikelihood(d, np.random.default_rng(6).normal(size=len(d.x)))
        theta = np.log([20.0, 30.0, 40.0, 50.0])
        gradient = ll.solve(theta)[1]
        finite = []
        for j in range(len(theta)):
            shift = np.eye(len(theta))[j] * 1e-5
            finite.append((ll.solve(theta + shift)[0] - ll.solve(theta - shift)[0]) / 2e-5)
        np.testing.assert_allclose(gradient, finite, atol=2e-7)

    def test_no_target_conditioning_and_negative_outcome_conservation(self):
        sample = rows()
        changed = deepcopy(sample[0])
        changed.update(event_kind="sack", offense_epa=-100, pressure=1)
        changed["actors"]["target"] = None
        self.assertEqual(row_features(sample[0], ("qb",)), row_features(changed, ("qb",)))
        d = design(sample, "joint")
        model, cov = fit(d, [p["offense_epa"] for p in sample], plan(), fixed=True)
        output, _ = predict(model, [changed])
        item = output[0]
        self.assertAlmostEqual(sum(item["components"].values()) + item["residual"], -100)
        self.assertLess(item["residual"], 0)
        l = contrast(d.names, "00-0000001", 20, {"00-0000001": 0.5, "00-0000002": 0.5})
        self.assertAlmostEqual(float(l.sum()), 0)
        self.assertGreater(float(l @ cov @ l), 0)
        self.assertAlmostEqual(
            float(l @ np.array(model["coefficients"])), -float(-l @ np.array(model["coefficients"]))
        )

    def test_nullspace_detects_qb_team_allocation_and_cold_uncertainty(self):
        d = design(rows(), "joint", extra_qbs=["00-9999999"])
        l = np.array([contrast(d.names, "00-0000001", 20, {"00-0000001": 0.5, "00-9999999": 0.5})])
        self.assertEqual(identification(d, l)["nonestimable_contrasts"], 1)
        shift = np.zeros(len(d.names))
        shift[d.names.index("qb/00-0000001")] = 0.25
        shift[d.names.index("offense/BUF")] = -0.25
        np.testing.assert_allclose(d.x @ shift, 0, atol=1e-14)
        self.assertNotEqual(float((l @ shift)[0]), 0)

    def test_unseen_qb_and_game_cannot_expand_training_vocabulary(self):
        d = design(rows(), "joint")
        model, _ = fit(d, [p["offense_epa"] for p in rows()], plan(), fixed=True)
        held = play(week=4)
        held["qb"] = "00-9999999"
        before = deepcopy(model)
        output, unseen = predict(model, [held])
        self.assertEqual(unseen, {"qb": 1, "game": 1})
        self.assertEqual(output[0]["components"]["qb"], 0)
        self.assertEqual(output[0]["components"]["game"], 0)
        self.assertEqual(model, before)

    def test_invalid_contrasts_and_responses_fail(self):
        d = design(rows(), "joint")
        for weights in ({"00-0000001": 0.8}, {"00-0000001": 2, "00-0000002": -1}):
            with self.assertRaises(ValueError):
                contrast(d.names, "00-0000001", 1, weights)
        with self.assertRaises(ValueError):
            RestrictedLikelihood(d, [float("nan")] * len(d.x))
        with self.assertRaises(ValueError):
            contrast(d.names, "00-9999999", 1, {"00-0000001": 1})


if __name__ == "__main__":
    unittest.main()
