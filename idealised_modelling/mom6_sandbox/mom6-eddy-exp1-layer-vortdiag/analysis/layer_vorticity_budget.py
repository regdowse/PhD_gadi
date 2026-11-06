"""Native-layer daily-mean momentum-curl budget on this Cartesian C-grid.

Run: python analysis/layer_vorticity_budget.py --run archive/output000
No depth remapping is performed: all horizontal derivatives hold layer index fixed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import xarray as xr

PAIRS = {
    'coriolis_advection': ('CAu', 'CAv'),
    'relative_vorticity_acceleration': ('rvxv', 'rvxu'),
    'kinetic_energy_gradient': ('gKEu', 'gKEv'),
    'pressure_force': ('PFu', 'PFv'),
    'barotropic_correction': ('u_BT_accel', 'v_BT_accel'),
    'horizontal_friction': ('diffu', 'diffv'),
    'vertical_friction': ('du_dt_visc', 'dv_dt_visc'),
    'diapycnal_exchange': ('dudt_dia', 'dvdt_dia'),
    'net_tendency': ('dudt', 'dvdt'),
}
INDEPENDENT = ['coriolis_advection', 'pressure_force', 'barotropic_correction',
               'horizontal_friction', 'vertical_friction', 'diapycnal_exchange']


def curl(u, v, dx_u, dy_v, area_q):
    """Circulation/area at interior corners; solid boundary corners excluded."""
    out = np.full(u.shape[:-2] + area_q.shape, np.nan, dtype=np.float64)
    out[..., 1:-1, 1:-1] = (
        np.diff(v * dy_v, axis=-1)[..., 1:-1, :]
        - np.diff(u * dx_u, axis=-2)[..., :, 1:-1]
    ) / area_q[1:-1, 1:-1]
    return out


def corner_mean(a):
    out = np.full(a.shape[:-2] + (a.shape[-2]+1, a.shape[-1]+1), np.nan)
    out[..., 1:-1, 1:-1] = (a[..., :-1, :-1] + a[..., 1:, :-1]
                           + a[..., :-1, 1:] + a[..., 1:, 1:]) / 4
    return out


def field(ds, name, y, x):
    return ds[name].transpose('time', 'zl', y, x).values.astype(np.float64)


def calculate(run: Path, destination: Path):
    state = xr.open_dataset(run/'ocean_layer_daily.nc', decode_times=False).load()
    budget = xr.open_dataset(run/'ocean_budget_daily.nc', decode_times=False).load()
    geom = xr.open_dataset(run/'ocean_geometry.nc', decode_times=False).load()
    if state.sizes['time'] < 2:
        raise ValueError('At least two completed daily records are required.')
    np.testing.assert_array_equal(state.time, budget.time)
    dx_u, dy_v, area = (geom[n].values for n in ['dxCu', 'dyCv', 'Aq'])
    dx, dy = float(np.median(geom.dxT)), float(np.median(geom.dyT))
    # This experiment is Cartesian. Refuse silently applying Cartesian PV
    # reconstructions to a different grid; curl itself retains circulation metrics.
    np.testing.assert_allclose(geom.dxT, dx)
    np.testing.assert_allclose(geom.dyT, dy)
    h = field(state, 'h', 'yh', 'xh')
    hq = corner_mean(h)
    valid = np.isfinite(hq) & (hq > 1e-3)
    for a in [h[..., :-1, :-1], h[..., 1:, :-1], h[..., :-1, 1:], h[..., 1:, 1:]]:
        valid[..., 1:-1, 1:-1] &= a > 1e-3
    wet = geom.wet.values > 0
    valid[..., 1:-1, 1:-1] &= (wet[:-1, :-1] & wet[1:, :-1]
                                                & wet[:-1, 1:] & wet[1:, 1:])
    coords = {n: state[n] for n in ['time', 'zl', 'yq', 'xq']}
    out = xr.Dataset(coords=coords)
    dims = ('time', 'zl', 'yq', 'xq')
    def add(name, values, units, description):
        out[name] = (dims, np.where(valid, values, np.nan),
                     {'units': units, 'long_name': description})
    for name, (un, vn) in PAIRS.items():
        add(name, curl(field(budget, un, 'yh', 'xq'), field(budget, vn, 'yq', 'xh'),
                        dx_u, dy_v, area), 's-2', f'Native-layer curl of {un}, {vn}')
    out['sum_contributions'] = sum(out[n] for n in INDEPENDENT)
    out.sum_contributions.attrs = {'units': 's-2', 'long_name': 'Sum of six independent momentum-curl contributions'}
    out['residual'] = out.net_tendency - out.sum_contributions
    out.residual.attrs = {'units': 's-2', 'long_name': 'Net tendency minus sum; includes numerical and diagnostic sampling mismatch'}
    out['planetary_acceleration'] = (out.coriolis_advection
        - out.relative_vorticity_acceleration - out.kinetic_energy_gradient)
    out.planetary_acceleration.attrs = {'units': 's-2', 'long_name': 'CA curl minus relative-vorticity and KE-gradient curls; diagnostic remainder'}
    u, v = field(state, 'uo', 'yh', 'xq'), field(state, 'vo', 'yq', 'xh')
    rv = field(state, 'RV', 'yq', 'xq')
    add('RV', rv, 's-1', 'MOM6 online daily mean layer relative vorticity')
    add('PV', field(state, 'PV', 'yq', 'xq'), 'm-1 s-1', 'MOM6 online daily mean layer PV')
    add('RV_from_mean_velocity', curl(u, v, dx_u, dy_v, area), 's-1', 'Layer curl of daily mean velocity')
    # wd is defined at tracer-point interfaces, positive downward in this layer driver.
    wd = budget.wd.transpose('time', 'zi', 'yh', 'xh').values
    source = corner_mean(wd[:, :-1] - wd[:, 1:])
    add('diapycnal_thickness_source', source, 'm s-1', 'wd(top) minus wd(bottom), interpolated to corners')
    add('corner_thickness', hq, 'm', 'Arithmetic four-cell mean thickness on the Cartesian grid')
    f = geom.f.values
    # Mean-PV reconstructed from mean fields differs from the online mean PV.
    qmean = (f + rv) / np.where(valid, hq, np.nan)
    add('PV_from_mean_fields', qmean, 'm-1 s-1', '(f + daily mean RV) / daily mean corner thickness')
    add('PV_exchange_thickness', -qmean*source/hq, 'm-1 s-2', 'Approximate -q S/h from daily mean fields')
    for name in ['pressure_force', 'barotropic_correction', 'horizontal_friction', 'vertical_friction', 'diapycnal_exchange']:
        add('PV_'+name, out[name].values/hq, 'm-1 s-2', f'{name} vorticity contribution divided by mean thickness')
    # A derivative of daily mean RV is a separate cross-check, not the online net tendency.
    units = state.time.attrs.get('units', '')
    factor = {'days':86400., 'hours':3600., 'seconds':1.}.get(units.split()[0])
    if factor is None: raise ValueError(f'Unsupported time units: {units}')
    add('RV_mean_time_derivative', np.gradient(rv, state.time.values*factor, axis=0),
        's-2', 'Finite difference of daily mean RV; one-sided at first/last record')
    out['valid_layer_corner'] = (dims, valid.astype('i1'))
    for name in ['time_bnds', 'average_T1', 'average_T2', 'average_DT']:
        if name in state: out[name] = state[name]
    out.attrs.update(
        title='Native-layer MOM6 daily vorticity budget', source_run=str(run.resolve()),
        independent_contributions=', '.join(INDEPENDENT),
        conventions='curl = d(v)/dx - d(u)/dy at fixed layer index; boundaries excluded',
        limitations='Daily means; split-step diagnostic mismatch retained in residual. PV products use mean fields. No physical-depth transformation.',
        minimum_thickness_m=1e-3)
    destination.mkdir(parents=True, exist_ok=True)
    out.to_netcdf(destination/'layer_vorticity_budget.nc', encoding={
        n:{'zlib':True, 'complevel':2, 'dtype':'float32'}
        for n in out.data_vars if out[n].dtype.kind=='f' and n not in ['time_bnds','average_T1','average_T2','average_DT']})
    weights = xr.DataArray(area, dims=('yq','xq'), coords={n:out[n] for n in ['yq','xq']})
    measures = xr.Dataset()
    names = list(PAIRS)+['sum_contributions','residual','planetary_acceleration']
    for name in names:
        a=out[name]
        measures[name+'_rms'] = np.sqrt((a*a).weighted(weights).mean(('yq','xq')))
        measures[name+'_mean'] = a.weighted(weights).mean(('yq','xq'))
        measures[name+'_max_abs'] = abs(a).max(('yq','xq'))
    measures.to_netcdf(destination/'layer_budget_statistics.nc')
    report={'source_run':str(run.resolve()), 'days':state.sizes['time'], 'layers':state.sizes['zl'],
            'valid_fraction':float(valid.mean()), 'independent_terms':INDEPENDENT,
            'rms_s_2':{n:float(np.sqrt(np.nanmean(out[n].values**2))) for n in names},
            'RV_velocity_rms_difference_s_1':float(np.sqrt(np.nanmean((out.RV-out.RV_from_mean_velocity).values**2))),
            'caution':'Residual is reported, not assigned to a physical process. Thin layers and boundary corners excluded.'}
    (destination/'budget_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    plot(out, measures, destination)
    print(json.dumps(report,indent=2))
    return out


def plot(out, stats, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    for name in INDEPENDENT+['net_tendency','residual']:
        a=stats[name+'_rms']
        axes[0].plot(out.time,a.mean('zl'),label=name)
        axes[1].plot(a.mean('time'),np.arange(out.sizes['zl'])+1,label=name)
    axes[0].set(xlabel='Model time (days)',ylabel='Mean over layers of spatial RMS (s$^{-2}$)',yscale='log')
    axes[1].set(xlabel='Time mean spatial RMS (s$^{-2}$)',ylabel='Layer index',xscale='log')
    axes[1].invert_yaxis(); axes[1].legend(fontsize=7)
    fig.savefig(destination/'budget_magnitudes.png',dpi=160); plt.close(fig)
    k=int(np.nanargmax(np.nanmean(out.RV.isel(time=-1).values**2,axis=(-2,-1))))
    names=INDEPENDENT+['net_tendency','residual']
    vmax=max(float(abs(out[n].isel(time=-1,zl=k)).max()) for n in names)
    fig,axes=plt.subplots(2,4,figsize=(15,7),constrained_layout=True)
    for ax,n in zip(axes.flat,names):
        a=out[n].isel(time=-1,zl=k)
        im=ax.pcolormesh(out.xq/1000,out.yq/1000,a,shading='auto',cmap='RdBu_r',vmin=-vmax,vmax=vmax)
        ax.set(title=n,xlabel='x (km)',ylabel='y (km)',aspect='equal')
    fig.colorbar(im,ax=axes.ravel().tolist(),label='s$^{-2}$')
    fig.suptitle(f'Layer {k+1}, last daily mean; common colour scale')
    fig.savefig(destination/'budget_last_day_maps.png',dpi=160); plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'budget')
    args=parser.parse_args()
    calculate(args.run,args.output)
