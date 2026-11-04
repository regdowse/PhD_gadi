"""Three-panel daily velocity animation for this MOM6 experiment.

Only the surface and two central sections are loaded, not the complete 4-D fields.
No model files are changed. Rendering uses Matplotlib's inline JSHTML player.
"""
from __future__ import annotations

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def _central_face(field, axis, centre):
    """Select the exact face or interpolate between its two neighbours only."""
    coordinates = field[axis].values
    exact = np.flatnonzero(np.isclose(coordinates, centre, rtol=0, atol=1e-7))
    if exact.size:
        return field.isel({axis: int(exact[0])}, drop=True)
    upper = int(np.searchsorted(coordinates, centre))
    if upper == 0 or upper == coordinates.size:
        raise ValueError(f'Model centre is outside {axis}.')
    weight = (centre-coordinates[upper-1])/(coordinates[upper]-coordinates[upper-1])
    return ((1-weight)*field.isel({axis: upper-1}, drop=True)
            + weight*field.isel({axis: upper}, drop=True))


def prepare_velocity_panels(velocity, static, frame_stride=1):
    """Prepare surface speed, zonal v section, meridional u section in that order."""
    if not isinstance(frame_stride, int) or isinstance(frame_stride, bool) or frame_stride < 1:
        raise ValueError('frame_stride must be a positive integer.')
    expected = {'uo': {'time', 'z_l', 'yh', 'xq'},
                'vo': {'time', 'z_l', 'yq', 'xh'}}
    for name, dimensions in expected.items():
        if name not in velocity or set(velocity[name].dims) != dimensions:
            raise ValueError(f'Need depth-level {name} with dimensions {sorted(dimensions)}.')
        if velocity[name].attrs.get('units') not in ('m s-1', 'm/s', 'm s^-1'):
            raise ValueError(f'{name} must be in m/s.')
    for name in ['xh', 'yh', 'xq', 'yq']:
        np.testing.assert_allclose(velocity[name], static[name])
        if velocity[name].attrs.get('units') not in ('m', 'meter', 'meters'):
            raise ValueError(f'{name} must be in metres.')
    if velocity.sizes['time'] == 0:
        raise ValueError('No velocity records available.')
    if 'z_i' not in velocity or velocity.sizes['z_i'] != velocity.sizes['z_l']+1:
        raise ValueError('Need z_i interfaces for the depth-level velocity cells.')
    frames = np.arange(0, velocity.sizes['time'], frame_stride)
    xh, yh, xq, yq = [velocity[name].values for name in ['xh', 'yh', 'xq', 'yq']]
    cx = float((xq[0]+xq[-1])/2)
    cy = float((yq[0]+yq[-1])/2)
    u = velocity.uo.isel(time=frames)
    v = velocity.vo.isel(time=frames)
    # The daily diagnostic contains daily mean components; their norm is not
    # the daily mean of instantaneous speed. Uppermost z_l approximates surface.
    # Closed/dry faces have zero normal flow; include that zero when
    # interpolating to neighbouring wet tracer centres.
    u_top = u.isel(z_l=0, drop=True).where(static.wet_u > 0, 0).load()
    v_top = v.isel(z_l=0, drop=True).where(static.wet_v > 0, 0).load()
    if len(xq) != len(xh)+1 or len(yq) != len(yh)+1:
        raise ValueError('Expected closed symmetric C-grid with one extra face per direction.')
    wx = (xh-xq[:-1])/np.diff(xq)
    wy = (yh-yq[:-1])/np.diff(yq)
    if not (np.all((wx >= 0) & (wx <= 1)) and np.all((wy >= 0) & (wy <= 1))):
        raise ValueError('Tracer centres must lie between their adjacent velocity faces.')
    us = u_top.transpose('time', 'yh', 'xq').values
    vs = v_top.transpose('time', 'yq', 'xh').values
    # Explicit linear interpolation avoids requiring SciPy in the model environment.
    uc = (1-wx)[None,None,:]*us[:,:,:-1] + wx[None,None,:]*us[:,:,1:]
    vc = (1-wy)[None,:,None]*vs[:,:-1,:] + wy[None,:,None]*vs[:,1:,:]
    speed = xr.DataArray(np.where(static.wet.values[None] > 0, np.hypot(uc, vc), np.nan),
                         dims=('time','yh','xh'),
                         coords={'time': u.time, 'yh': yh, 'xh': xh})
    # Zonal cut: v(yq=middle); meridional cut: u(xq=middle).
    v_section = _central_face(v, 'yq', cy).transpose('time', 'z_l', 'xh').load()
    u_section = _central_face(u, 'xq', cx).transpose('time', 'z_l', 'yh').load()
    v_wet = _central_face(static.wet_v, 'yq', cy) > 0
    u_wet = _central_face(static.wet_u, 'xq', cx) > 0
    depth_zonal = _central_face(static.deptho, 'yh', cy)
    depth_meridional = _central_face(static.deptho, 'xh', cx)
    v_section = v_section.where(v_wet & (velocity.z_l < depth_zonal))
    u_section = u_section.where(u_wet & (velocity.z_l < depth_meridional))
    for name, field in [('surface speed', speed), ('zonal v section', v_section),
                        ('meridional u section', u_section)]:
        if not np.isfinite(field.values).any():
            raise ValueError(f'No finite data in {name}.')
    return {
        'speed': speed.values, 'v_section': v_section.values, 'u_section': u_section.values,
        'time': velocity.time.values[frames], 'xq': xq, 'yq': yq,
        'xh': xh, 'yh': yh, 'z_i': velocity.z_i.values,
        'depth_zonal': depth_zonal.values, 'depth_meridional': depth_meridional.values,
        'centre_x': cx, 'centre_y': cy, 'surface_depth': float(velocity.z_l[0]),
        'record_count': len(frames),
    }


def create_velocity_animation(panels, experiment_name='', interval_ms=250, maximum_depth_m=4000):
    """Create a fixed-scale 1x3 animation and return (figure, animation)."""
    if interval_ms <= 0 or maximum_depth_m <= 0:
        raise ValueError('Frame interval and maximum depth must be positive.')
    speed_max = max(float(np.nanmax(panels['speed'])), 1e-12)
    flow_max = max(float(np.nanmax(np.abs(panels['v_section']))),
                   float(np.nanmax(np.abs(panels['u_section']))), 1e-12)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), layout='constrained')
    for ax in axes:
        ax.set_facecolor('0.85')
    map_mesh = axes[0].pcolormesh(panels['xq'], panels['yq'],
        np.ma.masked_invalid(panels['speed'][0]), shading='flat',
        cmap='viridis', vmin=0, vmax=speed_max)
    zonal_mesh = axes[1].pcolormesh(panels['xq'], panels['z_i'],
        np.ma.masked_invalid(panels['v_section'][0]), shading='flat',
        cmap='RdBu_r', vmin=-flow_max, vmax=flow_max)
    meridional_mesh = axes[2].pcolormesh(panels['yq'], panels['z_i'],
        np.ma.masked_invalid(panels['u_section'][0]), shading='flat',
        cmap='RdBu_r', vmin=-flow_max, vmax=flow_max)
    axes[0].axhline(panels['centre_y'], color='orangered', linestyle='--',
                   linewidth=1, label='Zonal cut (v)')
    axes[0].axvline(panels['centre_x'], color='cyan', linestyle=':',
                   linewidth=1, label='Meridional cut (u)')
    axes[0].legend(loc='upper left', fontsize=8)
    axes[0].set(xlabel='x (m)', ylabel='y (m)',
                title=f"Surface speed (z = {panels['surface_depth']:g} m)")
    axes[0].set_aspect('equal')
    axes[1].set(xlabel='x (m)', ylabel='Depth (m)',
                title=f"Zonal section: meridional v\ny = {panels['centre_y']:,.0f} m")
    axes[2].set(xlabel='y (m)', ylabel='Depth (m)',
                title=f"Meridional section: zonal u\nx = {panels['centre_x']:,.0f} m")
    for ax, horizontal, bottom in [(axes[1], panels['xh'], panels['depth_zonal']),
                                  (axes[2], panels['yh'], panels['depth_meridional'])]:
        ax.fill_between(horizontal, bottom, maximum_depth_m, color='0.65', zorder=3)
        ax.plot(horizontal, bottom, color='0.35', linewidth=0.7, zorder=4)
        ax.set_ylim(maximum_depth_m, 0)
    fig.colorbar(map_mesh, ax=axes[0], label='Speed (m/s)', shrink=0.85)
    fig.colorbar(meridional_mesh, ax=axes[1:], label='Signed velocity (m/s)', shrink=0.85)
    title = fig.suptitle('')
    meshes = [map_mesh, zonal_mesh, meridional_mesh]
    fields = [panels['speed'], panels['v_section'], panels['u_section']]

    def update(frame):
        for mesh, field in zip(meshes, fields):
            mesh.set_array(np.ma.masked_invalid(field[frame]).ravel())
        title.set_text(f"{experiment_name} | daily mean time: {panels['time'][frame]} "
                       f"| frame {frame+1}/{panels['record_count']}")
        return (*meshes, title)

    update(0)
    animation = FuncAnimation(fig, update, frames=panels['record_count'],
                              interval=interval_ms, blit=False, repeat=True,
                              cache_frame_data=False)
    return fig, animation
