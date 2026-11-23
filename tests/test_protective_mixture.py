"""Independent density, signed-integral and matched-study protection contracts."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.integrate import quad
from scipy.stats import norm

from nfl_value.coarse_control_study import archive
from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD, GaussianControls, fit_control, training_points
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_preflight import (
    arms,
    experiment_kind,
    mode_geometry,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.mode_proposal import Work, make_proposal
from nfl_value.protective_mixture import fit_protective_mixture, protect, restore_protective_mixture
from nfl_value.replicated_reference import SamplingProposal
from nfl_value.tail_controls import tail_proposal
from nfl_value.two_level_reference import sampling_hash


def plan():
    return json.loads(Path("config/protective-mixture-preflight-v1.json").read_text())


def small_plan():
    return {
        **plan(),
        "em_nodes": 128,
        "em_steps": 2,
        "mass_pilot_nodes": 128,
        "training_nodes": 256,
        "replicates": 8,
        "nodes_per_replicate": 64,
        "correction_nodes_per_replicate": 16,
        "trials": 1,
    }


def simple_pair():
    initial = SamplingProposal(np.zeros(1), np.eye(1), np.zeros(1), np.eye(1), {})
    mode = make_proposal(initial, [[-0.5]] * 3, [np.eye(1)] * 3, [0.2, 0.3, 0.5], {})
    tail = make_proposal(initial, [[0.5]] * 3, [np.eye(1)] * 3, [0.4, 0.3, 0.3], {})
    return mode, tail


class ProtectiveMixtureTests(unittest.TestCase):
    def test_full_density_and_bound_against_independent_gaussian_sums(self):
        mode, tail = simple_pair()
        q = protect(mode, tail, 0.5)
        x = np.linspace(-30, 30, 101)
        expected = 0.45 * norm.pdf(x, -0.5) + 0.45 * norm.pdf(x, 0.5) + 0.1 * norm.pdf(x)
        np.testing.assert_allclose(np.exp(q.logpdf(x[:, None], METHOD)), expected, rtol=1e-12)
        self.assertEqual(len(q.components(METHOD)), 8)
        self.assertAlmostEqual(sum(p[0] for p in q.components(METHOD)), 1)
        self.assertEqual([q.components(METHOD)[j][0] for j in (3, 7)], [0.05, 0.05])
        for component in (mode, tail):
            self.assertLessEqual(
                np.max(component.logpdf(x[:, None], METHOD) - q.logpdf(x[:, None], METHOD)),
                np.log(2) + 1e-13,
            )
        for bad in (0, 1, -0.1, np.nan):
            with self.assertRaises(ValueError):
                protect(mode, tail, bad)
        with self.assertRaises(ValueError):
            q.components("paired")

    def test_second_moment_bound_for_signed_integrand_independent_quadrature(self):
        # Independent scalar formulas; the second moment is not the variance.
        m = lambda x: 0.9 * norm.pdf(x, -0.5) + 0.1 * norm.pdf(x)
        t = lambda x: 0.9 * norm.pdf(x, 0.5) + 0.1 * norm.pdf(x)
        g = lambda x: norm.pdf(x) * (-2 + 3 * x)
        second = [
            quad(lambda x: g(x) ** 2 / q(x), -12, 12, epsabs=1e-10)[0]
            for q in (m, t, lambda x: (m(x) + t(x)) / 2)
        ]
        self.assertLessEqual(second[2], 2 * min(second[:2]))
        self.assertAlmostEqual(quad(g, -12, 12)[0], -2, places=12)

    def test_zero_mean_controls_and_signed_integral_with_duplicate_columns(self):
        q = protect(*simple_pair(), 0.5)
        z, weights = hermgauss(80)
        points, quadrature = [], []
        for mass, mean, covariance, _ in q.components(METHOD):
            points.extend(mean + np.sqrt(2 * covariance[0, 0]) * z[:, None])
            quadrature.extend(mass * weights / np.sqrt(np.pi))
        points, quadrature = np.array(points), np.array(quadrature)
        logq = q.logpdf(points, METHOD)
        basis = GaussianControls(q)
        features = basis.features(points, logq)
        np.testing.assert_allclose(quadrature @ features, 0, atol=1e-12)
        np.testing.assert_array_equal(features[:, 9:12], features[:, 21:24])

        def signed(x, log_density):
            scalar = x[:, 0]
            return (
                np.exp(norm.logpdf(scalar) - log_density)
                * (-2 + 3 * scalar - 0.5 * (scalar**2 - 1))
            )[:, None]

        fitted = fit_control(signed, q, entropy=[91831], nodes=256, relative_ridge=1e-6)
        self.assertLess(fitted.diagnostics["numerical_rank"], basis.width)
        self.assertTrue(np.isfinite(fitted.coefficients).all())
        estimate = quadrature @ (signed(points, logq) - fitted.adjustment(points, logq))
        np.testing.assert_allclose(estimate, [-2], atol=1e-11)
        training, w = training_points(q, [91832], 256)
        self.assertEqual(training.shape, (256, 1))
        self.assertAlmostEqual(w.sum(), 1)
        for j, (mass, *_rest) in enumerate(q.components(METHOD)):
            self.assertAlmostEqual(w[j * 32 : (j + 1) * 32].sum(), mass)

    def test_fitter_preserves_work_and_rejects_corrupt_child_or_mixture(self):
        p, initial, calls = small_plan(), tail_proposal(), []

        def density(x):
            calls.append(len(x))
            return normal_logpdf(x, [-1, 0.5, 0, 0], np.eye(4))

        work = Work(p)
        q = fit_protective_mixture(density, initial, entropy=[91833, 0, 1, 0], plan=p, work=work)
        self.assertEqual(sum(calls), work.total)
        self.assertEqual(work.record(), q.diagnostics["fit_work"])
        self.assertEqual(
            sampling_hash(q), sampling_hash(restore_protective_mixture(q.diagnostics, initial, p))
        )
        for mutate in (
            lambda g: g.update(mode_mass=0.75),
            lambda g: g.update(sampling_sha256="0" * 64),
            lambda g: g.update(geometry_uses_evaluation=True),
            lambda g: g["tail_geometry"]["stages"][0]["log_density"].__setitem__(0, 99),
            lambda g: g["tail_geometry"]["mode_geometry"]["component_means"][0].__setitem__(0, 99),
            lambda g: g["fit_work"].update(total=0),
        ):
            corrupt = deepcopy(q.diagnostics)
            mutate(corrupt)
            with self.assertRaises(ValueError):
                restore_protective_mixture(corrupt, initial, p)

    def test_three_matched_fits_have_independent_evaluation_and_signed_raw(self):
        p, initial = small_plan(), tail_proposal()

        class Toy:
            def logpdf(self, x):
                return normal_logpdf(x, [-1, 0, 0, 0], np.eye(4))

            def integrand(self, truth):
                return lambda x, logq: (
                    np.exp(self.logpdf(x) - logq)[:, None]
                    * np.column_stack(
                        [
                            np.ones(len(x)),
                            x[:, 0],
                            x[:, 1],
                            np.full((len(x), 2), 0.025),
                            np.full((len(x), 2), 0.975),
                            np.full((len(x), 2), 0.9),
                        ]
                    )
                )

        records = {}
        for arm, domain in (("candidate", 0), ("baseline", 2), ("tail", 3)):
            record = trial(Toy(), initial, {}, p, [p["base_seed"], domain, 3, 0], arm)
            self.assertIn("coarse", record)
            self.assertLess(np.array(record["coarse"])[:, 1].mean(), 0)
            case = dict(
                arm=arm,
                target=3,
                truth={},
                initial_sampling_sha256=sampling_hash(initial),
                records=[dict(trial=0, **record)],
                decision=summarize([record], p),
            )
            validate_case(case, initial, {}, p)
            corrupt = deepcopy(case)
            corrupt["records"][0]["fit"]["training_entropy"] = [1]
            with self.assertRaises(ValueError):
                validate_case(corrupt, initial, {}, p)
            records[arm] = record
        self.assertEqual(
            mode_geometry(records["candidate"]["geometry"]), records["baseline"]["geometry"]
        )
        self.assertEqual(
            records["candidate"]["geometry"]["tail_geometry"], records["tail"]["geometry"]
        )
        self.assertEqual(len({tuple(r["fit"]["training_entropy"]) for r in records.values()}), 3)
        self.assertEqual(records["candidate"]["fit"]["feature_count"], 120)

    def test_frozen_scope_and_nfl_gate(self):
        p = plan()
        validate_plan(p)
        self.assertEqual(sum(len(ids) for _, ids in arms(p)) * p["trials"], 576)
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(json_bytes(dict(plan=p, experiment=experiment_kind(p))), manifest=True)
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()
        p["protective_mode_mass"] = 0.75
        with self.assertRaisesRegex(ValueError, "frozen design"):
            validate_plan(p)


if __name__ == "__main__":
    unittest.main()
