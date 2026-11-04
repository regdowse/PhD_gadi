#!/usr/bin/env python3
"""Generate a Gaussian C-grid MOM6 initial state; no model run is launched.

Dependencies: numpy, xarray, netCDF4, PyYAML; matplotlib for plot_state().
The YAML is authoritative for eddy/background choices; model parameters and
recorded runtime defaults supply the grid/EOS constants and are checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import warnings

import numpy as np
import xarray as xr
import yaml


def read_parameters(*files):
    """Read scalar MOM parameter assignments in override order."""
    result = {}
    for file in files:
        for line in Path(file).read_text().splitlines():
            match = re.match(r'^\s*([A-Za-z_0-9]+)\s*=\s*(.*?)\s*(?:!.*)?$', line)
            if not match:
                continue
            key, value = match.groups()
            if value.startswith('"'):
                result[key] = value.split('"')[1]
            elif value.lower() in ('true', 'false'):
                result[key] = value.lower() == 'true'
            else:
                try:
                    result[key] = float(value.replace('D', 'E').replace('d', 'e'))
                except ValueError:
                    result[key] = value
    return result


def load_config(path):
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    cfg['_config_file'] = str(path)
    cfg['_yaml'] = path.read_text()
    cfg['paths'] = {key: (path.parent / value).resolve()
                    for key, value in cfg['paths'].items()}
    return cfg


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def load_model(cfg):
    """Load verified metre grid, reference interfaces, masks and EOS constants."""
    paths = cfg['paths']
    root = paths['model_directory']
    params = read_parameters(root / 'docs/MOM_parameter_doc.all',
                             root / 'MOM_input', root / 'MOM_override')
    required = ['G_EARTH', 'RHO_0', 'DRHO_DT', 'DRHO_DS', 'DRHO_DP',
                'RHO_T0_S0', 'F_0', 'BETA', 'BETA_LAT_REF', 'ANGSTROM']
    require(all(key in params for key in required),
            f'Missing model constants; need recorded parameter documentation: {required}')
    require(params['GRID_CONFIG'] == 'cartesian' and params['AXIS_UNITS'] in ('m', 'meters'),
            'Only the configured Cartesian metre grid is supported.')
    require(params['EQN_OF_STATE'] == 'LINEAR' and params['DRHO_DT'] < 0,
            'This generator requires the verified linear EOS with negative DRHO_DT.')
    require(params['DRHO_DP'] == 0, 'Pressure-dependent density is not implemented.')
    require(params['ROTATION'] == 'betaplane', 'Expected verified beta-plane Coriolis convention.')
    # Deliberately reject periodic changes rather than silently creating an unwrapped eddy.
    require(not params['REENTRANT_X'] and not params['REENTRANT_Y'],
            'This generator implements the current closed boundaries, not periodic images.')
    require('SURFACE_HEIGHT_IC_FILE' not in read_parameters(root / 'MOM_input', root / 'MOM_override'),
            'Remove separate SURFACE_HEIGHT_IC_FILE: eta already includes SSH.')
    with xr.open_dataset(paths['grid'], decode_times=False) as source:
        grid = source.load()
    with xr.open_dataset(paths['vertical_grid'], decode_times=False) as source:
        zi = source.Interface.values.astype(float)
    with xr.open_dataset(paths['topography'], decode_times=False) as source:
        topog = source.topog.values
        tx, ty = source.x.values, source.y.values
    nx, ny, nk = (int(params[key]) for key in ('NIGLOBAL', 'NJGLOBAL', 'NK'))
    require(dict(grid.sizes).get('xh') == nx and grid.sizes['yh'] == ny,
            'Saved horizontal grid does not match current model sizes.')
    require(len(zi) == nk + 1 and zi[0] == 0 and np.all(np.diff(zi) > 0),
            'Reference interfaces must increase from zero and match NK.')
    require(np.isclose(zi[-1], params['MAXIMUM_DEPTH']), 'Reference bottom depth has changed.')
    # Guard against a stale vertical output after changes to the ALE definition.
    recorded = read_parameters(paths['vertical_grid'].parent / 'MOM_parameter_doc.all')
    for key in ['ALE_COORDINATE_CONFIG', 'REGRIDDING_COORDINATE_MODE']:
        require(recorded.get(key) == params.get(key), f'Saved vertical grid is stale: {key}')
    for key, origin, length, n in [('xh', 'WESTLON', 'LENLON', nx),
                                  ('yh', 'SOUTHLAT', 'LENLAT', ny)]:
        expected = params[origin] + (np.arange(n) + 0.5) * params[length] / n
        np.testing.assert_allclose(grid[key].values, expected, rtol=0, atol=1e-6)
        np.testing.assert_allclose(grid[key[0]+'q'].values,
                                   params[origin] + np.arange(n+1)*params[length]/n)
        require(grid[key].attrs.get('units') in ('m', 'meter', 'meters'), 'Saved grid is not in metres.')
    np.testing.assert_allclose(tx, grid.xh)
    np.testing.assert_allclose(ty, grid.yh)
    np.testing.assert_allclose(topog, grid.deptho, atol=1e-3, rtol=1e-7)
    np.testing.assert_allclose(grid.dxt, params['LENLON']/nx)
    np.testing.assert_allclose(grid.dyt, params['LENLAT']/ny)
    f_expected = params['F_0'] + params['BETA'] * (grid.yq.values - params['BETA_LAT_REF'])
    # The saved grid supplies verified geometry, not exp1's changed rotation.
    # MOM_shared_initialization.F90 set_rotation_beta_plane uses this formula
    # for metre axes. Recompute it from this experiment's current parameters.
    grid['Coriolis'] = (grid.Coriolis.dims,
                        np.broadcast_to(f_expected[:, None], grid.Coriolis.shape).copy(),
                        {'units':'s-1', 'long_name':'Coriolis from current beta-plane settings'})
    for key, model_key in [('temperature_top_degC', 'T_TOP'), ('temperature_range_degC', 'T_RANGE'),
                            ('salinity_top_ppt', 'S_TOP'), ('salinity_range_ppt', 'S_RANGE')]:
        require(np.isclose(cfg['background'][key], params[model_key]),
                f'Background {key} differs from retained model setting {model_key}.')
    require(cfg['background']['profile'] == 'nominal_layer_linear', 'Unknown background profile.')
    require(cfg['background']['salinity_range_ppt'] == 0, 'Constant salinity is required for this balance.')
    versions = json.loads((root / 'build_versions.json').read_text())
    return grid, zi, params, versions


def gaussian(x, y, cx, cy, rc, psi0):
    return psi0 * np.exp(-((x-cx)**2 + (y-cy)**2) / rc**2)


def decay(depth, e_folding_depth):
    """Infinitely differentiable exp(-d/H); d is depth below the local surface."""
    require(np.isfinite(e_folding_depth) and e_folding_depth > 0,
            'e_folding_depth_m must be finite and strictly positive.')
    return np.exp(-np.asarray(depth) / e_folding_depth)


def average_vertical_derivative(top_depth, thickness, e_folding_depth):
    """Layer-average dF/dz, stable even for tiny collapsed-bottom layers.

    F(d)=exp(-d/H), z positive upward. This equals
    (F(d_top)-F(d_bottom))/thickness without subtracting nearly equal values.
    """
    require(np.all(np.asarray(thickness) > 0), 'Layer thickness must be positive.')
    return (decay(top_depth, e_folding_depth)
            * (-np.expm1(-np.asarray(thickness)/e_folding_depth)) / thickness)


def column_geometry(depth, ssh, zi, minimum):
    """Clip reference z interfaces, reserve positive collapsed layers, add SSH once."""
    eta = np.empty((len(zi),) + depth.shape)
    eta[-1] = -depth
    for k in range(len(zi)-2, 0, -1):
        eta[k] = np.maximum(-zi[k], eta[k+1] + minimum)
    eta[0] = 0
    require(np.all(depth > (len(zi)-1)*minimum), 'Water column too shallow for positive layers.')
    # Z-star dilation fixes the bottom and places the top exactly at SSH.
    eta += ssh[None] * (1 + eta / depth[None])
    return eta


def face_mean(array, axis):
    """Average neighbouring tracer columns; closed outer faces copy the nearest column."""
    first = np.take(array, [0], axis=axis)
    last = np.take(array, [-1], axis=axis)
    a = np.take(array, np.arange(array.shape[axis]-1), axis=axis)
    b = np.take(array, np.arange(1, array.shape[axis]), axis=axis)
    return np.concatenate([first, (a+b)/2, last], axis=axis)


def build_state(cfg):
    grid, zi, p, versions = load_model(cfg)
    eddy, num, bg = cfg['eddy'], cfg['numerics'], cfg['background']
    require(eddy['centre'] == 'domain_midpoint' and eddy['aspect_ratio'] == 1
            and eddy['vertical_tilt'] == 0 and eddy['rotation'] == 'cyclonic',
            'Only the agreed circular, untilted, cyclonic midpoint eddy is implemented.')
    require(num['geometry'] == 'clipped_zstar' and num['depth_reference'] == 'local_free_surface',
            'Unsupported geometry/depth convention.')
    require(num['coriolis_strategy'] == 'centre_f_approximation', 'Unsupported Coriolis strategy.')
    require(num['instability_action'] in ('warn', 'error'), 'instability_action must be warn or error.')
    require('decay_depth_m' not in eddy,
            'Replace legacy decay_depth_m with vertical_profile: exponential and e_folding_depth_m.')
    require(eddy.get('vertical_profile') == 'exponential', 'vertical_profile must be exponential.')
    require(all(np.isfinite(eddy[key]) and eddy[key] > 0 for key in
                ['maximum_speed_radius_m', 'surface_speed_m_s', 'e_folding_depth_m']),
            'Eddy radius, speed and e-folding depth must be finite and positive.')
    cx = p['WESTLON'] + p['LENLON']/2
    cy = p['SOUTHLAT'] + p['LENLAT']/2
    f = p['F_0'] + p['BETA']*(cy-p['BETA_LAT_REF'])
    require(f != 0, 'Cyclonic sign/geostrophic initialization is undefined at f=0.')
    require(np.all(grid.Coriolis.values*f > 0), 'Coriolis changes sign across this domain.')
    rc = np.sqrt(2)*eddy['maximum_speed_radius_m']
    psi0 = -np.sign(f)*eddy['surface_speed_m_s']*rc*np.exp(0.5)/np.sqrt(2)
    e_depth = eddy['e_folding_depth_m']
    x, y, xq, yq = [grid[name].values for name in ('xh', 'yh', 'xq', 'yq')]
    X, Y = np.meshgrid(x, y)
    psi = gaussian(X, Y, cx, cy, rc, psi0)
    wet = grid.wet.values > 0
    depth = grid.deptho.values.astype(float)
    ssh = np.where(wet, f*psi/p['G_EARTH'], 0)
    minimum = num['minimum_layer_m']
    require(minimum >= max(p['MIN_THICKNESS'], 2*p['ANGSTROM']), 'Minimum layer thickness is too small.')
    # Dry-column geometry is zeroed after using a safe placeholder depth.
    eta = column_geometry(np.where(wet, depth, zi[-1]), ssh, zi, minimum)
    eta[:, ~wet] = 0
    h = eta[:-1]-eta[1:]
    z = (eta[:-1]+eta[1:])/2
    d = ssh[None]-z
    di = ssh[None]-eta
    safe_h = np.where(wet[None], h, 1)
    # Integrate the exponential derivative exactly over each physical layer.
    derivative = psi[None]*average_vertical_derivative(di[:-1], safe_h, e_depth)
    alpha = -p['DRHO_DT']/p['RHO_0']  # DRHO_DT is dimensional; not alpha itself.
    temp_anomaly = f/(p['G_EARTH']*alpha)*derivative
    nominal_z = (zi[:-1]+zi[1:])/2
    layer_fraction = (np.arange(len(zi)-1)+0.5)/(len(zi)-1)
    t_nominal = bg['temperature_top_degC']-bg['temperature_range_degC']*layer_fraction
    s_nominal = bg['salinity_top_ppt']-bg['salinity_range_ppt']*layer_fraction
    # Background is a function of depth below mean sea level, horizontally uniform at fixed z.
    t_bg = np.interp(-z, nominal_z, t_nominal)
    salt = np.interp(-z, nominal_z, s_nominal)
    temp = t_bg + temp_anomaly
    # Average neighbouring interfaces to get physical face-layer midpoints.
    eta_u, eta_v = face_mean(eta, 2), face_mean(eta, 1)
    ssh_u, ssh_v = face_mean(ssh, 1), face_mean(ssh, 0)
    du = ssh_u[None]-(eta_u[:-1]+eta_u[1:])/2
    dv = ssh_v[None]-(eta_v[:-1]+eta_v[1:])/2
    Xu, Yu = np.meshgrid(xq, y)
    Xv, Yv = np.meshgrid(x, yq)
    ps_u = gaussian(Xu, Yu, cx, cy, rc, psi0)
    ps_v = gaussian(Xv, Yv, cx, cy, rc, psi0)
    u_surface = 2*(Yu-cy)/rc**2*ps_u
    v_surface = -2*(Xv-cx)/rc**2*ps_v
    # No flow on closed outer faces or through land; no velocity in blocked bottom layers.
    bottom_u = np.minimum(np.pad(depth, ((0,0),(1,0)), mode='edge'),
                          np.pad(depth, ((0,0),(0,1)), mode='edge'))
    bottom_v = np.minimum(np.pad(depth, ((1,0),(0,0)), mode='edge'),
                          np.pad(depth, ((0,1),(0,0)), mode='edge'))
    active_u = (grid.wet_u.values[None] > 0) & ((eta_u[:-1]+eta_u[1:])/2 > -bottom_u[None])
    active_v = (grid.wet_v.values[None] > 0) & ((eta_v[:-1]+eta_v[1:])/2 > -bottom_v[None])
    active_u[:, :, [0, -1]] = False
    active_v[:, [0, -1], :] = False
    u = np.where(active_u, u_surface[None]*decay(du, e_depth), 0)
    v = np.where(active_v, v_surface[None]*decay(dv, e_depth), 0)
    coords = {
        'xh': ('xh', x, {'units':'m', 'cartesian_axis':'X', 'axis':'X'}),
        'yh': ('yh', y, {'units':'m', 'cartesian_axis':'Y', 'axis':'Y'}),
        'xq': ('xq', xq, {'units':'m', 'cartesian_axis':'X', 'axis':'X'}),
        'yq': ('yq', yq, {'units':'m', 'cartesian_axis':'Y', 'axis':'Y'}),
        'zl': ('zl', nominal_z, {'units':'m', 'cartesian_axis':'Z', 'axis':'Z', 'positive':'down'}),
        'zi': ('zi', zi, {'units':'m', 'cartesian_axis':'Z', 'axis':'Z', 'positive':'down'}),
    }
    def tracer(a, units, name):
        return (('zl','yh','xh'), np.where(wet[None], a, 0), {'units':units, 'long_name':name})
    ds = xr.Dataset({
        'temp': tracer(temp, 'degC', 'Initial potential temperature'),
        'salt': tracer(salt, 'ppt', 'Initial salinity'),
        'u': (('zl','yh','xq'), u, {'units':'m s-1'}),
        'v': (('zl','yq','xh'), v, {'units':'m s-1'}),
        'eta': (('zi','yh','xh'), eta, {'units':'m', 'positive':'up', 'long_name':'Interface height relative to mean sea level'}),
        'ssh': (('yh','xh'), ssh, {'units':'m', 'positive':'up'}),
        'depth': (('yh','xh'), depth, {'units':'m', 'positive':'down'}),
        'wet': (('yh','xh'), wet.astype('i1')),
        'temp_anomaly': tracer(temp_anomaly, 'degC', 'Eddy layer-average temperature anomaly'),
        'u_surface': (('yh','xq'), np.where(grid.wet_u > 0, u_surface, 0), {'units':'m s-1'}),
        'v_surface': (('yq','xh'), np.where(grid.wet_v > 0, v_surface, 0), {'units':'m s-1'}),
        'active_u': (('zl','yh','xq'), active_u.astype('i1')),
        'active_v': (('zl','yq','xh'), active_v.astype('i1')),
        'depth_u': (('zl','yh','xq'), du, {'units':'m', 'positive':'down'}),
        'depth_v': (('zl','yq','xh'), dv, {'units':'m', 'positive':'down'}),
    }, coords=coords, attrs={
        'title':'Gaussian cyclonic eddy initial conditions for MOM6',
        'MOM6_source_commit':versions['MOM6'], 'build_versions':json.dumps(versions),
        'configuration_yaml':cfg['_yaml'],
        'grid_source':str(cfg['paths']['grid']), 'vertical_source':str(cfg['paths']['vertical_grid']),
        'config_sha256':hashlib.sha256(cfg['_yaml'].encode()).hexdigest(),
        'centre_x_m':cx, 'centre_y_m':cy, 'Rc_m':rc, 'psi0_m2_s':float(psi0),
        'reference_f_s_1':float(f), 'rho0_kg_m3':p['RHO_0'], 'g_m_s2':p['G_EARTH'],
        'drho_dt_kg_m3_K':p['DRHO_DT'], 'drho_ds_kg_m3_ppt':p['DRHO_DS'],
        'drho_dp_s2_m2':p['DRHO_DP'], 'rho_T0_S0_kg_m3':p['RHO_T0_S0'],
        'vertical_profile':'exponential', 'e_folding_depth_m':e_depth, 'target_speed_m_s':eddy['surface_speed_m_s'],
        'maximum_speed_radius_m':eddy['maximum_speed_radius_m'],
        'beta_m_1_s_1':p['BETA'], 'beta_reference_y_m':p['BETA_LAT_REF'], 'F_0_s_1':p['F_0'],
        'minimum_layer_m':minimum,
        'balance':'Approximate hydrostatic/geostrophic initialization; not a steady nonlinear vortex. '
                  'Constant centre f used; any beta variation is diagnosed. Depth below local free surface. '
                  'Infinitely differentiable exponential vertical profile; layer-average thermal anomaly, no finite cutoff. '
                  'Small free-surface-slope and finite-grid errors; closed-wall Gaussian tails masked. '
                  'No separate surface-height initialization: eta includes SSH once.',
        'background':'MOM layer-index linear T/S sampled at nominal depths, interpolated at physical MSL depth; endpoint values held outside nominal centres.',
    })
    return ds


def validate_state(ds, cfg):
    """Validate the saved snapshot and quantify approximate balance, not solver equilibrium."""
    a = ds.attrs
    wet = ds.wet.values > 0
    eta = ds.eta.values
    h = eta[:-1]-eta[1:]
    require(ds.temp.dims == ('zl','yh','xh') and ds.u.dims == ('zl','yh','xq')
            and ds.v.dims == ('zl','yq','xh') and ds.eta.dims == ('zi','yh','xh'), 'Invalid C-grid dimensions.')
    require('time' not in ds.dims and 'Time' not in ds.dims, 'Expected one snapshot without time dimension.')
    for name in ['temp', 'salt', 'u', 'v', 'eta', 'ssh']:
        require(np.isfinite(ds[name]).all(), f'Nonfinite values in {name}.')
    require(np.all(h[:, wet] > 0), 'Nonpositive wet-cell thickness.')
    np.testing.assert_allclose(eta[0], ds.ssh, atol=1e-12)
    np.testing.assert_allclose(eta[-1, wet], -ds.depth.values[wet], atol=1e-9)
    np.testing.assert_allclose(h.sum(axis=0)[wet], (ds.depth+ds.ssh).values[wet], atol=1e-9)
    require(np.max(np.abs(ds.u.values[:, :, [0,-1]])) == 0 and
            np.max(np.abs(ds.v.values[:, [0,-1], :])) == 0, 'Flow through closed outer boundaries.')
    e_depth = a['e_folding_depth_m']
    require(a['vertical_profile'] == 'exponential', 'Expected exponential vertical profile.')
    max_decay_error = 0.0
    below = 0.0
    for vel, dep, surf in [('u','depth_u','u_surface'), ('v','depth_v','v_surface')]:
        z = ds[dep].values
        values = ds[vel].values
        active = ds[f'active_{vel}'].values > 0
        expected = np.where(active, ds[surf].values[None] * decay(z, e_depth), 0)
        max_decay_error = max(max_decay_error, float(np.max(np.abs(values-expected))))
        np.testing.assert_allclose(values, expected, rtol=1e-12, atol=1e-15)
        below = max(below, float(np.max(np.abs(values[z >= e_depth]), initial=0)))
    require(max_decay_error < 1e-12, 'Exponential velocity profile check failed.')
    # Potential density: pressure-independent EOS verified in load_model().
    rho = a['rho_T0_S0_kg_m3'] + a['drho_dt_kg_m3_K']*ds.temp.values + a['drho_ds_kg_m3_ppt']*ds.salt.values
    delta_rho = np.diff(rho, axis=0)
    depth_mid = ds.ssh.values[None]-(eta[:-1]+eta[1:])/2
    real_pair = (h[:-1] > 10*a['minimum_layer_m']) & (h[1:] > 10*a['minimum_layer_m']) & wet[None]
    unstable = real_pair & (delta_rho < -cfg['numerics']['stability_tolerance_kg_m3'])
    n2 = a['g_m_s2']/a['rho0_kg_m3']*delta_rho/np.maximum(np.diff(depth_mid, axis=0), 1e-12)
    # Compare pressure gradients derived from the layer-average density anomaly with
    # Coriolis acceleration. This is a centred interior diagnostic, not MOM6's full PGF.
    rho_prime = a['drho_dt_kg_m3_K']*ds.temp_anomaly.values
    phi_interface = a['g_m_s2']*ds.ssh.values[None] + np.concatenate(
        [np.zeros_like(h[:1]), np.cumsum(a['g_m_s2']/a['rho0_kg_m3']*rho_prime*h, axis=0)], axis=0)
    phi = (phi_interface[:-1]+phi_interface[1:])/2
    dx, dy = float(np.diff(ds.xh)[0]), float(np.diff(ds.yh)[0])
    phi_x = np.gradient(phi, dx, axis=2)
    phi_y = np.gradient(phi, dy, axis=1)
    zmid = (eta[:-1]+eta[1:])/2
    # Convert along-layer derivatives to fixed-z gradients.
    phi_z = -a['g_m_s2']/a['rho0_kg_m3']*rho_prime
    phi_x -= phi_z*np.gradient(zmid, dx, axis=2)
    phi_y -= phi_z*np.gradient(zmid, dy, axis=1)
    uc = (ds.u.values[:,:,:-1]+ds.u.values[:,:,1:])/2
    vc = (ds.v.values[:,:-1,:]+ds.v.values[:,1:,:])/2
    f_actual = a['F_0_s_1']+a['beta_m_1_s_1']*(ds.yh.values-a['beta_reference_y_m'])
    f_actual = f_actual[None,:,None]
    radius = np.hypot(ds.xh.values[None,:]-a['centre_x_m'], ds.yh.values[:,None]-a['centre_y_m'])
    # Full interior column down to 3 e-folding depths, excluding collapsed bottom layers.
    interior = (radius < 2*a['maximum_speed_radius_m']) & (ds.depth.values > min(e_depth, 0.5*float(ds.zi.max())))
    select = (interior[None] & (depth_mid > 5) & (depth_mid < 3*e_depth)
              & (h > 10*a['minimum_layer_m']))
    residual = np.hypot(phi_x-f_actual*vc, phi_y+f_actual*uc)
    acceleration = np.hypot(f_actual*uc, f_actual*vc)
    require(np.any(select), 'No interior stencil available for geostrophic residual.')
    rms = float(np.sqrt(np.mean(residual[select]**2)))
    relative = rms/float(np.sqrt(np.mean(acceleration[select]**2)))
    # Reconstruct horizontal velocity at tracer centres to assess radial peak and rotation.
    us = (ds.u_surface.values[:,:-1]+ds.u_surface.values[:,1:])/2
    vs = (ds.v_surface.values[:-1,:]+ds.v_surface.values[1:,:])/2
    speed = np.hypot(us, vs)
    j, i = np.unravel_index(np.argmax(speed), speed.shape)
    zeta = np.gradient(vs, dx, axis=1)-np.gradient(us, dy, axis=0)
    core = radius < a['maximum_speed_radius_m']/2
    require(float(np.mean(zeta[core]))*a['reference_f_s_1'] > 0, 'Eddy rotation is not cyclonic.')
    require(abs(speed[j,i]-a['target_speed_m_s']) < 0.02*a['target_speed_m_s'], 'Peak speed outside 2% grid-sampling tolerance.')
    require(abs(radius[j,i]-a['maximum_speed_radius_m']) <= 2*max(dx,dy), 'Peak radius outside grid-sampling tolerance.')
    phi_expected = a['reference_f_s_1']*gaussian(ds.xh.values[None,:], ds.yh.values[:,None],
        a['centre_x_m'], a['centre_y_m'], a['Rc_m'], a['psi0_m2_s'])*decay(ds.ssh.values[None]-eta, e_depth)
    hydro_error = float(np.max(np.abs((phi_interface-phi_expected)[:,wet])))
    report = {
        'dimensions':dict(ds.sizes), 'psi0_m2_s':a['psi0_m2_s'],
        'reference_f_s_1':a['reference_f_s_1'], 'minimum_thickness_m':float(h[:,wet].min()),
        'surface_error_m':float(np.max(np.abs(eta[0]-ds.ssh.values))),
        'bottom_error_m':float(np.max(np.abs(eta[-1,wet]+ds.depth.values[wet]))),
        'peak_surface_speed_m_s':float(speed[j,i]), 'peak_surface_radius_m':float(radius[j,i]),
        'top_layer_peak_speed_m_s':float(np.hypot(uc[0],vc[0]).max()),
        'vertical_profile':'exponential', 'e_folding_depth_m':e_depth,
        'exponential_decay_max_error_m_s':max_decay_error,
        'speed_fraction_at_e_folding_depth':float(decay(e_depth, e_depth)),
        'max_speed_deeper_than_e_folding_depth_m_s':below,
        'unstable_vertical_pairs':int(unstable.sum()),
        'unstable_columns':int(np.any(unstable,axis=0).sum()),
        'minimum_density_increment_kg_m3':float(delta_rho[real_pair].min()),
        'minimum_N2_s_2':float(n2[real_pair].min()),
        'geostrophic_interior_rms_m_s2':rms, 'geostrophic_interior_relative_rms':relative,
        'hydrostatic_column_max_error_m2_s2':hydro_error,
        'fractional_f_variation':float((f_actual.max()-f_actual.min())/abs(a['reference_f_s_1'])),
        'Rossby_number_U_over_fR':float(a['target_speed_m_s']/abs(a['reference_f_s_1'])/a['maximum_speed_radius_m']),
    }
    if report['unstable_vertical_pairs']:
        message = (f"Static instability: {report['unstable_vertical_pairs']} vertical pairs in "
                   f"{report['unstable_columns']} columns; min N2={report['minimum_N2_s_2']:.3g} s^-2. "
                   'The requested exponential profile and background have been retained.')
        if cfg['numerics']['instability_action'] == 'error':
            raise ValueError(message)
        warnings.warn(message, stacklevel=2)
    if report['fractional_f_variation'] > 0:
        warnings.warn('Spatially varying f: this uses centre-f approximate balance; see residual.', stacklevel=2)
    require(hydro_error < 1e-8, 'Hydrostatic column consistency check failed.')
    require(relative < 0.05, 'Interior geostrophic residual exceeds 5%; inspect configuration.')
    return report


def generate(config_path):
    """Generate, write, reopen and validate; return output path and report."""
    cfg = load_config(config_path)
    ds = build_state(cfg)
    report = validate_state(ds, cfg)
    ds.attrs['validation_json'] = json.dumps(report)
    path = cfg['paths']['output']
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = {name: {'zlib':True, 'complevel':cfg['numerics']['compression_level'], '_FillValue':None}
                for name in ds.data_vars}
    # FMS 2021.01 rejects NF_BYTE during metadata scanning, even for unused masks.
    for name in ['wet', 'active_u', 'active_v']:
        encoding[name]['dtype'] = 'int32'
    for name in ds.coords:
        encoding[name] = {'_FillValue':None}
    ds.to_netcdf(path, engine='netcdf4', encoding=encoding)
    ds.close()
    with xr.open_dataset(path, decode_times=False) as saved:
        for name, variable in saved.variables.items():
            require(variable.dtype in (np.dtype('float32'), np.dtype('float64'),
                                       np.dtype('int16'), np.dtype('int32')),
                    f'{name}: unsupported FMS NetCDF type {variable.dtype}')
        reopened = validate_state(saved, cfg)
    require(report == reopened, 'Validation changed after NetCDF round trip.')
    return path, report


def plot_state(ds):
    """Compact notebook diagnostics; all generator physics stays in this module."""
    import matplotlib.pyplot as plt
    a = ds.attrs
    i = int(np.argmin(abs(ds.xh.values-a['centre_x_m'])))
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    ds.ssh.plot(ax=axes[0,0], x='xh', y='yh', cmap='RdBu_r')
    axes[0,0].set_title('Initial SSH (m)')
    us = (ds.u_surface.values[:,:-1]+ds.u_surface.values[:,1:])/2
    vs = (ds.v_surface.values[:-1,:]+ds.v_surface.values[1:,:])/2
    axes[0,1].pcolormesh(ds.xh,ds.yh,np.hypot(us,vs),shading='auto',cmap='viridis')
    skip = (slice(None,None,5), slice(None,None,5))
    X,Y = np.meshgrid(ds.xh,ds.yh)
    arrows = axes[0,1].quiver(X[skip], Y[skip], us[skip], vs[skip],
                              angles='xy', scale_units='xy', scale=1e-5, pivot='mid')
    axes[0,1].quiverkey(arrows, 0.85, 1.06, 0.2, '0.2 m/s', labelpos='E')
    axes[0,1].set_title('Surface velocity (arrows; colour in m/s)')
    fig.colorbar(axes[0,1].collections[0], ax=axes[0,1],label='Speed (m/s)')
    for ax in axes[0]:
        ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.set_aspect('equal')
    depth = ds.ssh.values[None]-(ds.eta.values[:-1]+ds.eta.values[1:])/2
    section = ds.temp.values[:,:,i]
    image = axes[1,0].pcolormesh(np.broadcast_to(ds.yh.values,section.shape),depth[:,:,i],section,shading='nearest',cmap='RdYlBu_r')
    axes[1,0].invert_yaxis()
    axes[1,0].set_xlabel('y (m)'); axes[1,0].set_ylabel('Depth below local surface (m)')
    axes[1,0].set_title(f'Temperature at x={float(ds.xh[i]):g} m')
    fig.colorbar(image,ax=axes[1,0],label='Temperature (degC)')
    # Pick a v face nearest the maximum-speed ring east of the centre.
    iq = int(np.argmin(abs(ds.xh.values-(a['centre_x_m']+a['maximum_speed_radius_m']))))
    jq = int(np.argmin(abs(ds.yq.values-a['centre_y_m'])))
    d = ds.depth_v.values[:,jq,iq]
    speed = abs(ds.v.values[:,jq,iq])
    surface = abs(float(ds.v_surface[jq,iq]))
    axes[1,1].plot(speed,d,'o',markersize=3,label='File face values')
    fine = np.linspace(0, float(d.max()), 300)
    axes[1,1].plot(surface*decay(fine,a['e_folding_depth_m']),fine,label='Requested exponential profile')
    axes[1,1].axhline(a['e_folding_depth_m'],color='grey',linestyle='--',label='E-folding depth')
    axes[1,1].set_ylim(float(d.max()),0)
    axes[1,1].set_xlabel('|v| (m/s)'); axes[1,1].set_ylabel('Depth below local surface (m)')
    axes[1,1].set_title('Decay at face near maximum-speed radius'); axes[1,1].legend()
    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.yaml'))
    args = parser.parse_args()
    path, report = generate(args.config)
    print('Wrote', path)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
