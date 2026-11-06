# Layer vorticity diagnostic output

All evolving fields are daily means, written as float32. Model dynamics and
initial conditions are unchanged. No model source changes are required.

- `ocean_layer_daily.nc`: native ten-layer state, RV, layer PV, thickness,
  interface elevations, cell volume, SSH and thickness tendency.
- `ocean_budget_daily.nc`: native momentum contributions, total velocity
  tendencies, diapycnal velocity and two-dimensional bottom stress.
- `ocean_daily.nc`: MOM6 online z-star remapping of the state and geometry.
- `ocean_budget_z_daily.nc`: MOM6 online z-star remapping of budget fields.
- `ocean_static.nc`: existing grid metrics, masks, bathymetry and Coriolis.

The former monthly and rho2 output requests are replaced by this daily design.
Surface wind-stress, surface mass-flux and mass-transport requests are omitted.
The `ocean_daily` filename and its thetao/volcello/uo/vo/zos fields are retained
for existing analysis consumers; vertical coordinates now have 29 cells.

## Vertical coordinate

`DIAG_COORD_DEF_Z="PARAM"` and `DIAG_COORD_RES_Z` specify cell thicknesses
in MOM_input. The table below records nominal interfaces and centres. These
are z-star cell averages, not exact point samples or strictly fixed geometric
positions; sea-level stretching is accepted for this experiment. Native RV/PV
cannot be remapped online by this MOM6 version and remain native-only.
Their depth sampling is deferred to offline analysis.

| Cell | Upper interface (m) | Centre (m) | Lower interface (m) |
|---|---|---|---|
| 1 | 0.00 | 1.78 | 3.56 |
| 2 | 3.56 | 5.88 | 8.20 |
| 3 | 8.20 | 10.73 | 13.26 |
| 4 | 13.26 | 16.38 | 19.50 |
| 5 | 19.50 | 22.93 | 26.36 |
| 6 | 26.36 | 30.44 | 34.52 |
| 7 | 34.52 | 39.05 | 43.58 |
| 8 | 43.58 | 48.90 | 54.22 |
| 9 | 54.22 | 60.17 | 66.12 |
| 10 | 66.12 | 73.13 | 80.14 |
| 11 | 80.14 | 88.12 | 96.10 |
| 12 | 96.10 | 105.62 | 115.14 |
| 13 | 115.14 | 126.29 | 137.44 |
| 14 | 137.44 | 151.07 | 164.70 |
| 15 | 164.70 | 181.26 | 197.82 |
| 16 | 197.82 | 218.75 | 239.68 |
| 17 | 239.68 | 266.21 | 292.74 |
| 18 | 292.74 | 327.44 | 362.14 |
| 19 | 362.14 | 407.92 | 453.70 |
| 20 | 453.70 | 515.42 | 577.14 |
| 21 | 577.14 | 660.81 | 744.48 |
| 22 | 744.48 | 858.92 | 973.36 |
| 23 | 973.36 | 1128.90 | 1284.44 |
| 24 | 1284.44 | 1492.97 | 1701.50 |
| 25 | 1701.50 | 1971.21 | 2240.92 |
| 26 | 2240.92 | 2568.68 | 2896.44 |
| 27 | 2896.44 | 3252.72 | 3609.00 |
| 28 | 3609.00 | 3734.55 | 3860.10 |
| 29 | 3860.10 | 3930.05 | 4000.00 |

## Budget interpretation

Use native-layer curls for the primary budget. `CAu/CAv` contain combined
Coriolis and advection; `rvxv/rvxu` (zonal/meridional) and `gKEu/gKEv`
are overlapping components, not additional independent sources. The remainder
CA minus those components is useful for diagnosing the planetary contribution.
`PFu/PFv` are pressure-force accelerations; `u_BT_accel/v_BT_accel` are
barotropic anomaly corrections, not purely pressure-force diagnostics.
`diffu/diffv` are horizontal viscous accelerations. `du_dt_visc/dv_dt_visc`
include the vertical-friction solve and bottom drag; do not add bottom stress
again. `dudt_dia/dvdt_dia` measure the velocity changes from cross-layer
momentum exchange. `dudt/dvdt` provide the net model velocity tendencies.

`wd` is cross-interface diapycnal velocity, not physical vertical velocity.
In this layer implementation its interior positive direction is downward;
net exchange thickness source is wd(top) minus wd(bottom). Save `h`, `e`
and `dhdt` to interpret thickness changes and exclude collapsed layers offline.
PV is model layer PV in m^-1 s^-1; RV is in s^-1. Momentum accelerations
are in m s^-2 and their horizontal curls in s^-2.

Offline curls, PV/RV sampling, residuals and optional Ertel PV are not computed
by these configuration edits. Native curl and curl after depth remapping are
different operations. Daily-mean products are accepted approximations.
Runtime diagnostic availability and generated NetCDF coordinates, masks and
averaging remain to be checked later; no integration was launched here.

## Running the native-layer budget analysis

After Payu archives the run:

```bash
source env.sh
python analysis/layer_vorticity_budget.py --run archive/output000
```

Results are written to `analysis/budget/`: the full native-layer curl budget,
area-weighted statistics, a JSON summary, an RMS comparison plot and last-day
maps using a common colour scale. The script uses the Cartesian circulation
metrics in `ocean_geometry.nc`, excludes boundary corners, and masks corners
where any adjacent layer is thinner than 1 mm. It reports both the online
net-tendency curl and a finite difference of daily mean RV. PV source products
use daily mean thickness/velocity fields and are approximate; no exact PV
closure or Ertel-PV calculation is claimed. The generated fields retain all
individual signed contributions for comparing cancellation.

`build_versions.json` is required by the initialization generator and must be
retained. It has been restored from the parent experiment using the same build.
The initial launch used the preserved initial-state NetCDF files after the
regeneration command failed on that missing metadata.
