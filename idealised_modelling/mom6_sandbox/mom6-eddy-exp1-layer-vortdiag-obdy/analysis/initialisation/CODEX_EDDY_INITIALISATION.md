# Task: initialise an idealised Gaussian eddy in MOM6

Work in `regdowse/PhD_gadi`, under
`idealised_modelling/mom6_sandbox/mom6-idealised-eddy/`.
Inspect the latest repository files and applicable instructions first. Implement
the following; do not submit a payu job.

## Deliverables

Create `initialisation/` containing:

- `config.yaml`: all eddy parameters, background T/S settings, grid/input paths,
  output path, and numerical choices, with units and short comments.
- `generate_initial_state.py`: reusable functions plus a CLI that reads the YAML
  and writes the NetCDF. Resolve relative paths against the config location,
  independently of the shell working directory.
- `setup.ipynb`: explain the configuration, call the Python implementation,
  generate the file, and plot/validate its contents. Do not duplicate generator
  logic in notebook cells. Keep generated notebook output modest.

Save the generated file at `input/initial_state.nc`, alongside the existing
forcing, SST and topography NetCDF files. Update `MOM_input` to read it.

## Agreed first-test parameters

- Centre: physical midpoint of the actual model domain.
- Circular eddy, aspect ratio 1, no vertical tilt.
- Cyclonic rotation: choose the sign using the model's signed Coriolis parameter.
- Diameter of maximum surface speed: 100 km (radius 50 km).
- Maximum surface speed: 0.20 m/s.
- Velocity amplitude decreases linearly with depth to zero at 1,000 m and remains
  zero below. Preserve this requested profile unless the user agrees otherwise.

Use the preprint's convention, in physical metres:

```text
psi = psi0 * F(d) * exp(-r^2 / Rc^2)
F(d) = max(1 - d/1000, 0)                 # d positive downward
Rc = sqrt(2) * 50,000 m
abs(psi0) = 0.20 * Rc * exp(0.5)/sqrt(2) # approximately 16,487 m^2/s
u = -dpsi/dy; v = dpsi/dx
```

A Gaussian has no finite outer edge. The 100 km diameter is explicitly the
maximum-speed diameter, not a cutoff. For this streamfunction convention,
cyclonic rotation requires `sign(psi0) = -sign(f)`.

## Model consistency

Inspect current `MOM_input`, `MOM_override`, `input.nml`, `config.yaml`, the input
generation notebook, and the recorded MOM6 source version. Obtain the actual
horizontal grid, staggering, periodicity, bathymetry, vertical interfaces,
Coriolis settings and linear-EOS coefficients. Do not assume uniform vertical
spacing, invent EOS coefficients, or copy stale ANU-TUB dimensions. Prefer actual
model grid/initial-state output when available; otherwise reproduce the configured
grid faithfully. Report missing required inputs clearly.

Construct SSH, T/S and velocity consistently using hydrostatic/geostrophic
balance. For constant f, z positive upward, and constant salinity:

```text
Phi' = f * psi
SSH = f * psi(surface) / g
rho' = -(rho0*f/g) * dpsi/dz
T' = f/(g*alpha_T) * dpsi/dz
```

Use the model's actual EOS definition (including whether its coefficient is
alpha_T or d(rho)/dT). If f varies spatially, do not silently apply constant-f
formulas as exact balance; explain and implement an appropriate approximation.
Use a background T/S profile consistent with the experiment and check static
stability. Linear velocity decay introduces a jump in the thermal anomaly at
1,000 m; flag instability rather than silently smoothing the requested profile.
Describe geostrophic initialization as approximate, not a steady nonlinear vortex.

Evaluate velocity at the model's staggered u/v locations and physical layer
depths. Match wet masks, bottom partial cells and boundary/periodic conventions.
Supply layer geometry consistent with SSH and the local bottom. Avoid adding SSH
twice. Write one snapshot, preferably without a time dimension, with units and
provenance/configuration metadata.

Expected variables (use verified model dimensions):

| Variable | Conceptual dimensions | Meaning |
|---|---|---|
| temp, salt | zl, yh, xh | Potential temperature and salinity |
| u | zl, yh, xq | Zonal velocity, m/s |
| v | zl, yq, xh | Meridional velocity, m/s |
| eta | zi, yh, xh | Interface heights, m, positive upward |
| ssh | yh, xh | Surface height, m, for inspection |

## Connect to MOM6

Verify these names against the recorded source version, then replace conflicting
existing settings in `MOM_input` (check later overrides too):

```text
THICKNESS_CONFIG = "file"
THICKNESS_FILE = "initial_state.nc"
INTERFACE_IC_VAR = "eta"
TS_CONFIG = "file"
TS_FILE = "initial_state.nc"
TEMP_IC_VAR = "temp"
SALT_IC_VAR = "salt"
VELOCITY_CONFIG = "file"
VELOCITY_FILE = "initial_state.nc"
U_IC_VAR = "u"
V_IC_VAR = "v"
```

Verify payu stages the file through its existing `input` path. Explain that these
settings require a fresh start: an existing restart takes precedence. Preserve
existing archives and restarts; do not delete them or launch a simulation.

## Verification and handoff

Run the generator and reopen the NetCDF. Validate dimensions, finite wet-cell
values, nonnegative thicknesses (strictly positive where required by MOM6),
bottom/surface consistency, static stability, rotation sign, and peak-speed
radius/amplitude within expected grid sampling error. Check the requested linear
decay and zero velocity below 1,000 m. Quantify a geostrophic balance residual.

The notebook must show SSH, surface velocity, a central temperature section, and
velocity versus depth. Explain any boundary or balance limitations. Provide the
CLI command, relevant dependencies, output location and validation results.
Keep large NetCDF outputs out of Git if that matches repository conventions;
retain reproducible code/configuration. If the execution environment lacks the
Gadi inputs, do not claim to have generated or validated the final model file:
provide the exact command to run on Gadi and identify the outstanding checks.
