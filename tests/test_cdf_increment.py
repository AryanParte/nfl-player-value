"""High-precision references for the cancellation failure, not score tuning."""

from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.integrate import quad
from scipy.special import ndtr

from nfl_value.cdf_increment import centered_probit, normal_cdf_increment
from nfl_value.control_variates import METHOD, training_points
from nfl_value.endpoint_controls import EndpointControls, fit_endpoint_basis
from nfl_value.mode_preflight import arms, validate_plan
from nfl_value.tail_controls import tail_proposal


def decimal_increment(c, d):
    # Integrate the Hermite expansion of the density, using 80-digit Decimal
    # arithmetic. Independent of the production quadrature/log-CDF branches.
    with localcontext() as ctx:
        ctx.prec = 80
        c, d = Decimal(str(c)), Decimal(str(d))
        pi = Decimal(
            "3.141592653589793238462643383279502884197169399375105820974944592307816406286"
        )
        previous, current, total = Decimal(0), Decimal(1), Decimal(0)
        power, factorial = d, Decimal(1)
        for n in range(50):
            total += (-1) ** n * current * power / factorial
            previous, current = current, c * current - n * previous
            power *= d
            factorial *= n + 2
        return float((-c * c / 2).exp() / (2 * pi).sqrt() * total)


class CdfIncrementTests(unittest.TestCase):
    def test_signed_sub_ulp_increments_against_80_digit_series(self):
        for c in [-20, -8, -5.612, 0, 5.612, 8, 20]:
            for d in [-1e-18, 1e-18, -1e-10, 1e-10, -1e-3, 1e-3]:
                actual = float(normal_cdf_increment(c, d))
                expected = decimal_increment(c, d)
                self.assertLess(abs((actual - expected) / expected), 1e-13, (c, d))
        self.assertEqual(float(normal_cdf_increment(6, 0)), 0)
        self.assertGreater(float(normal_cdf_increment(6, 1e-18)), 0)
        for c, d in [(np.inf, 1), (1, np.nan)]:
            with self.assertRaises(ValueError):
                normal_cdf_increment(c, d)

    def test_branch_boundary_tails_and_sign_against_independent_quadrature(self):
        cases = [(0, 0.12), (5.612, -0.022), (-5.612, 0.022), (9, -15), (-9, 15), (2, 1), (-3, -2)]
        for c in [-20, -6, 0, 6, 20]:
            edge = 0.25 / (np.sqrt((1 + abs(c)) ** 2 + 0.5) + (1 + abs(c)))
            cases += [
                (c, sign * edge * scale) for sign in (-1, 1) for scale in (1 - 1e-7, 1 + 1e-7)
            ]
        for c, d in cases:
            reference = quad(
                lambda u: d * np.exp(-0.5 * (c + d * u) ** 2) / np.sqrt(2 * np.pi),
                0,
                1,
                epsabs=1e-100,
                epsrel=3e-13,
            )[0]
            actual = float(normal_cdf_increment(c, d))
            self.assertLess(abs((actual - reference) / reference), 5e-13, (c, d))

    def test_normalized_near_constant_control_reproduces_and_repairs_failure(self):
        nodes, weights = hermgauss(96)
        z = np.sqrt(2) * nodes[:, None]
        b, a = np.array([5.612]), np.array([[3e-9]])
        scale = a[0, 0] * np.exp(-(b[0] ** 2) / 2) / np.sqrt(2 * np.pi)
        legacy = (ndtr(b + z @ a.T) - ndtr(b / np.sqrt(1 + (a * a).sum(axis=1))))[:, 0] / scale
        repaired = centered_probit(b, a, z)[:, 0] / scale
        self.assertGreater(abs(weights @ legacy / np.sqrt(np.pi)), 0.2)
        self.assertLess(abs(weights @ repaired / np.sqrt(np.pi)), 1e-12)
        np.testing.assert_array_equal(centered_probit(b, np.zeros_like(a), z), 0)

    def test_constant_training_responses_have_exact_zero_slopes_and_features(self):
        p = json.loads(Path("config/endpoint-control-preflight-v2.json").read_text())
        q = tail_proposal()
        x, w = training_points(q, [90214], 256)
        logq = q.logpdf(x, METHOD)
        y = np.tile([1, -2, -3, 0, 0.25, 1, 0.75], (256, 1))
        basis, evidence = fit_endpoint_basis(q, x, w, logq, y, p["endpoint_control"])
        np.testing.assert_array_equal(basis.directions[:, :, 1:], 0)
        polynomial_width = basis.width - len(basis.parts) * 4
        np.testing.assert_array_equal(basis.features(x, logq)[:, polynomial_width:], 0)
        restored = EndpointControls(q, evidence["endpoint_basis"]["directions"], stable=True)
        np.testing.assert_array_equal(restored.features(x, logq), basis.features(x, logq))
        validate_plan(p)
        self.assertEqual(sum(len(ids) for _, ids in arms(p)) * p["trials"], 896)
        p["endpoint_control"]["arithmetic"] = "subtract_near_one"
        with self.assertRaises(ValueError):
            validate_plan(p)


if __name__ == "__main__":
    unittest.main()
