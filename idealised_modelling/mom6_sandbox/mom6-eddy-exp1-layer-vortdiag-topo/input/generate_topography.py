#!/usr/bin/env python3
"""South-shallow, north-deep basin; retain the coastline and shelf width."""
from pathlib import Path
import numpy as np
import xarray as xr


def build_topography(slope=8e-4, pivot_depth=2500.0):
    """Positive-down depths; positive slope deepens northward; 45 km shelves, 25 km blend."""
    spacing = 5000.0
    length = 500000.0
    x = (np.arange(100) + 0.5) * spacing
    y = x.copy()
    X, Y = np.meshgrid(x, y)
    edge = np.minimum.reduce([X, length-X, Y, length-Y])
    t = np.clip(edge / 45000.0, 0, 1)
    baseline = pivot_depth * (3*t**2 - 2*t**3)
    # Quintic smoothstep has zero first and second derivatives at each join.
    t = np.clip((edge - 45000.0) / 25000.0, 0, 1)
    window = t**3 * (10 - 15*t + 6*t**2)
    anomaly = slope * (Y - length/2) * window
    depth = baseline + anomaly
    return xr.Dataset({
        'topog': (('y', 'x'), depth, {'units': 'm', 'positive': 'down'}),
    }, coords={'x': ('x', x, {'units': 'm'}), 'y': ('y', y, {'units': 'm'})}, attrs={
        'description': 'South shallow / north deep; shelves reshaped to the interior pivot depth',
        'interior_dH_dy': float(slope), 'pivot_depth_m': float(pivot_depth),
        'pivot_y_m': length/2, 'shelf_width_m': 45000.0,
        'blend_width_m': 25000.0,
    })


def generate_topography(directory=None):
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent
    ds = build_topography()
    ds.to_netcdf(directory / 'topog.nc', encoding={name: {'_FillValue': None} for name in ds.variables})
    return ds


if __name__ == '__main__':
    ds = generate_topography()
    print('Wrote', Path(__file__).resolve().parent / 'topog.nc')
    print('Depth range (m):', float(ds.topog.min()), float(ds.topog.max()))
