"""Independent closed answers for consumed-control quadrature diagnostics."""

import runpy
from types import SimpleNamespace
import unittest

import numpy as np


class DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functions = runpy.run_path(
            "scripts/diagnose_two_level_coverage.py", run_name="diagnosis_test"
        )

    def target(self, mean):
        # U=X1-X2 and V=X1+X2 are independent Gaussian variables.
        return SimpleNamespace(
            contrasts=np.array([[1.0, -1.0]]),
            noise=np.array([0.3]),
            probabilities=np.ones(1),
            means=np.array([mean]),
            covariances=np.array([np.eye(2)]),
        )

    def test_odd_sine_cancels_independently_of_student_endpoint(self):
        target = self.target([0.0, 0.0])
        value, error = self.functions["sine_moment"](target, 1.7)
        self.assertLess(abs(value), 1e-14)
        self.assertLess(error, 1e-12)
        self.assertLess(abs(self.functions["tensor_moment"](target, 1.7, 64)), 1e-14)

    def test_independent_gaussian_sine_and_symmetric_student_cdf_closed_answer(self):
        target = self.target([np.pi / 4, np.pi / 4])
        # E[sin V]=exp(-Var(V)/2), E[F(-U)]=.5 by symmetry.
        expected = (0.5 - 0.975) * np.exp(-1.0)
        value, error = self.functions["sine_moment"](target, 0.0)
        self.assertAlmostEqual(value, expected, places=12)
        self.assertLess(error, 1e-10)
        self.assertAlmostEqual(
            self.functions["tensor_moment"](target, 0.0, 64), expected, places=12
        )


if __name__ == "__main__":
    unittest.main()
