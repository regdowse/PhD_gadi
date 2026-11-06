"""Geometry checks for the 2500 m south-shallow, north-deep revision."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
from generate_initial_state import load_config, build_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('topography', ROOT/'input/generate_topography.py')
topography = importlib.util.module_from_spec(spec)
spec.loader.exec_module(topography)


class ShallowSlopeTests(unittest.TestCase):
    def test_pivot_orientation_and_eddy_scale_relief(self):
        ds = topography.build_topography()
        h = ds.topog.values
        # Basin centre falls between four tracer cells.
        self.assertAlmostEqual(float(h[49:51,49:51].mean()), 2500)
        self.assertAlmostEqual(float(h[39:41,49:51].mean()-h[59:61,49:51].mean()), -80)
        self.assertTrue(np.all(np.diff(h[14:86,50]) > 0))
        self.assertLess(float(h.max()), 2700)
        self.assertTrue(np.isfinite(h).all())

    def test_shelves_retain_shape_and_wet_mask_without_deep_trough(self):
        ds = topography.build_topography()
        flat = topography.build_topography(slope=0)
        old = topography.build_topography(slope=0, pivot_depth=4000)
        X,Y = np.meshgrid(ds.x,ds.y)
        shelves = np.minimum.reduce([X,500000-X,Y,500000-Y]) <= 45000
        np.testing.assert_array_equal(ds.topog.values[shelves],flat.topog.values[shelves])
        np.testing.assert_allclose(flat.topog,old.topog*2500/4000)
        np.testing.assert_array_equal(ds.topog>0,old.topog>0)
        self.assertLessEqual(float(flat.topog.max()),2500)

    def test_current_initial_state_uses_requested_beta_and_depth(self):
        cfg = load_config(ROOT/'initialisation/config.yaml')
        np.testing.assert_array_equal(cfg['background']['interface_depths_m'],
                                     [0,100,200,300,400,500,900,1300,1700,2100,2500])
        ds = build_state(cfg)
        self.assertEqual(ds.attrs['beta_m_1_s_1'],2.66e-11)
        report = validate_state(ds,cfg)
        self.assertEqual(report['unstable_columns'],0)
        self.assertEqual(report['bottom_error_m'],0)
        self.assertLess(report['geostrophic_interior_relative_rms'],0.05)
        ds.close()


if __name__ == '__main__':
    unittest.main()
