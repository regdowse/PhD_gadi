# Native-layer budget results: output000

PBS job 183255954 completed successfully (exit 0), integrating 31 model days.
The archive contains 31 daily means on ten native layers and 29 diagnostic
z-star cells, spanning nominal interfaces 0–4000 m. All requested nominal
centres are present, including the additional 3734.55 m centre.

The native-layer calculation excludes boundary corners and corners where any
adjacent layer is thinner than 1 mm. Valid fraction over the whole array,
including excluded boundary corners: 86.04%.

## Domain/time/layer RMS comparison

These summary RMS values weight valid grid points equally across all days
and layers. The separate statistics NetCDF contains area-weighted horizontal
RMS, signed mean and maximum absolute value for each day and layer.

| Contribution | RMS (s^-2) |
|---|---:|
| coriolis_advection | 3.5464e-13 |
| pressure_force | 1.9161e-17 |
| barotropic_correction | 1.7687e-17 |
| horizontal_friction | 1.3912e-13 |
| vertical_friction | 1.0989e-13 |
| diapycnal_exchange | 4.1167e-16 |
| net_tendency | 3.3927e-13 |
| sum_contributions | 3.3927e-13 |
| residual | 2.7189e-17 |

Residual RMS / net tendency RMS = **0.0080%**. This is an aggregate
measure, not a guarantee that every small term is resolved at every point.
Pressure and barotropic curls are close to this numerical residual scale;
interpret their very small differences cautiously. Friction statistics include
near-boundary effects; they should not be read as eddy-core-only statistics.

The relative-vorticity and KE-gradient components overlap with CA and are
excluded from the six-term sum. Bottom stress is included through vertical
friction and is not added again. PV source products use daily mean fields;
this residual validates the momentum-curl budget, not a closed PV budget.

## Products

- `layer_vorticity_budget.nc`: signed contributions, sum, residual, PV source
  estimates, online PV/RV, reconstructed RV and masks.
- `layer_budget_statistics.nc`: per-day, per-layer horizontal statistics.
- `budget_magnitudes.png`: RMS comparisons over time and layer.
- `budget_last_day_maps.png`: final-day layer-1 contributions on a common scale.
- `budget_summary.json`: machine-readable aggregate results.

Reproduce from the experiment root:

```bash
source env.sh
python analysis/layer_vorticity_budget.py --run archive/output000
```

Analytic tests of rotation, gradient cancellation, metric scaling and excluded
boundaries passed. Runtime checks verified daily intervals, record counts,
native/remapped layer counts and nominal interfaces. No MOM6 source was edited.
The missing initialization build metadata was restored and the initialization
generator subsequently ran successfully. The run used the preserved inputs.

SSH was saved natively; its unsupported remapped request and the unused static
geothermal field request were corrected in the control file for subsequent
runs. The archived control files preserve exactly what this run used.
