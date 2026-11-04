"""Numerical regression checks for the smooth vertical profile.

Run: python -m unittest discover -s initialisation -p 'test_*.py'
"""
import unittest

import numpy as np

from generate_initial_state import average_vertical_derivative, decay


class ExponentialProfileTests(unittest.TestCase):
    def test_user_scale_is_e_folding_depth_and_not_cutoff(self):
        for scale in [10.0, 500.0, 1000.0, 10000.0]:
            values = decay(np.array([0, scale, 2*scale, 4*scale]), scale)
            self.assertEqual(values[0], 1)
            self.assertAlmostEqual(values[1], 1/np.e)
            self.assertAlmostEqual(values[2]/values[1], 1/np.e)
            self.assertGreater(values[-1], 0)

    def test_cell_average_matches_independent_quadrature(self):
        # Including a collapsed cell: subtracting two exponentials loses digits here.
        top = np.array([0., 500., 1000., 2000.])
        thickness = np.array([1e-6, 30., 500., 200.])
        nodes, weights = np.polynomial.legendre.leggauss(32)
        for scale in [500., 1000., 2000.]:
            depth = top[:, None] + thickness[:, None]*(nodes+1)/2
            quadrature = np.sum(weights*np.exp(-depth/scale)/scale, axis=1)/2
            np.testing.assert_allclose(
                average_vertical_derivative(top, thickness, scale),
                quadrature, rtol=1e-13, atol=1e-18)

    def test_infinitesimal_cell_has_finite_analytic_derivative(self):
        value = average_vertical_derivative(1000., 1e-12, 1000.)
        self.assertTrue(np.isfinite(value))
        self.assertAlmostEqual(value, 1/(1000*np.e), places=15)

    def test_invalid_scale_and_thickness_rejected(self):
        for scale in [0., -1., np.nan, np.inf]:
            with self.assertRaisesRegex(ValueError, 'strictly positive'):
                decay(100., scale)
        for thickness in [0., -1.]:
            with self.assertRaisesRegex(ValueError, 'thickness must be positive'):
                average_vertical_derivative(0., thickness, 1000.)


if __name__ == '__main__':
    unittest.main()
