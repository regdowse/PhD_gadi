"""Numerical regression checks for the smooth vertical profile.

Run: python -m unittest discover -s initialisation -p 'test_*.py'
"""
import unittest

import numpy as np

from generate_initial_state import average_vertical_derivative, decay, layer_profile, isopycnal_geometry


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


class IsopycnalTests(unittest.TestCase):
    def setUp(self):
        self.bg = {
            'interface_depths_m': [0, 100, 200, 300, 400, 500, 1200, 1900, 2600, 3300, 4000],
            'layer_temperatures_degC': list(range(24, 4, -2)),
        }

    def test_resolution_and_invalid_profiles(self):
        zi, temperatures = layer_profile(self.bg, 10, 4000)
        np.testing.assert_equal(np.diff(zi)[:5], 100)
        np.testing.assert_equal(np.diff(zi)[5:], 700)
        for changes in [{'layer_temperatures_degC': [20]*10},
                        {'interface_depths_m': [0, 4000]},
                        {'layer_temperatures_degC': [float('nan')]*10}]:
            with self.assertRaises(ValueError):
                layer_profile(dict(self.bg, **changes), 10, 4000)

    def test_displacement_satisfies_discrete_thermal_wind(self):
        zi, temperatures = layer_profile(self.bg, 10, 4000)
        psi = np.array([[16000., 0.]])
        eta, ssh, factors = isopycnal_geometry(
            np.full_like(psi, 4000), psi, zi, temperatures, -1e-4, 9.8, .2/1035, 500, 1e-6)
        reduced_gravity = 9.8*.2/1035*(-np.diff(temperatures))
        montgomery = 9.8*ssh + np.concatenate([
            np.zeros_like(ssh)[None],
            np.cumsum(reduced_gravity[:, None, None]*(eta[1:-1]+zi[1:-1, None, None]), axis=0)])
        np.testing.assert_allclose(montgomery, -1e-4*psi*factors[:, None, None], atol=1e-14)
        np.testing.assert_allclose(eta[:, 0, 1], -zi)

    def test_shallow_columns_close_and_layers_stay_positive(self):
        zi, temperatures = layer_profile(self.bg, 10, 4000)
        depth = np.array([[35., 500., 4000.]])
        eta, ssh, _ = isopycnal_geometry(depth, np.zeros_like(depth), zi, temperatures,
                                        -1e-4, 9.8, .2/1035, 500, 1e-6)
        np.testing.assert_allclose(eta[0], ssh)
        np.testing.assert_allclose(eta[-1], -depth)
        self.assertTrue(np.all(eta[:-1]-eta[1:] >= 1e-6))

    def test_sloping_bottom_preserves_interior_interfaces(self):
        zi, temperatures = layer_profile(self.bg, 10, 4200)
        depth = np.array([[3850., 4000., 4150.]])
        eta, ssh, _ = isopycnal_geometry(
            depth, np.zeros_like(depth), zi, temperatures,
            -1e-4, 9.8, .2/1035, 500, 1e-6)
        np.testing.assert_allclose(eta[-1], -depth)
        np.testing.assert_allclose((eta[:-1]-eta[1:]).sum(axis=0), depth+ssh)
        np.testing.assert_allclose(eta[1:-1], np.broadcast_to(-zi[1:-1, None, None], eta[1:-1].shape))
        with self.assertRaises(ValueError):
            layer_profile(self.bg, 10, 3900)

    def test_crossing_interfaces_rejected(self):
        zi, temperatures = layer_profile(self.bg, 10, 4000)
        with self.assertRaisesRegex(ValueError, 'interfaces cross'):
            isopycnal_geometry(np.array([[4000.]]), np.array([[1e8]]), zi, temperatures,
                               -1e-4, 9.8, .2/1035, 500, 1e-6)


if __name__ == '__main__':
    unittest.main()
