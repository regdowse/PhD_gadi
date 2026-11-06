# MOM6 eddy exp1 on Gadi

This directory is independent of `mom6-idealised-eddy`. Its own metadata identifies
its current archive; its notebooks use only paths under this experiment.

```bash
cd /g/data/fu5/users/rd7475/github/phd/idealised_modelling/mom6_sandbox/mom6-eddy-exp1-layer-vortdiag-topo
module purge
source env.sh
python input/generate_topography.py
python initialisation/generate_initial_state.py
payu run --new-uuid --initial 0
```

Use a fresh UUID for independent tests. Plain `payu run` intentionally continues
from this experiment's latest restart. Existing source-experiment archives are
preserved; copied output links and bookkeeping have been removed.

The current duration is one model month, using 25 CPUs and 30 minutes walltime.
`experiment_prefix` in config.yaml determines the archive prefix. The analysis
notebook reads this directory's metadata automatically; restart its kernel and
Run All after output is archived. Daily depth-level thetao and volcello are
written together to ocean_daily.nc.

Nonzero beta uses the documented centre-f approximate initialization. Inspect
initialisation/validation.json before interpreting the run.

## Isopycnal initialisation

`initialisation/config.yaml` sets ten fixed layer temperatures (24, 22, 20,
18, 16, 14, 12, 10, 8, 6 °C) and eleven reference interface depths. The first
five layers span 0–500 m in 100 m increments; the remaining five span
500–2500 m in 400 m increments. Edit `layer_temperatures_degC` to set the
water masses and `interface_depths_m` to set their resting depths. Stable
constant-salinity layers require temperatures decreasing downward.

The eddy displaces density interfaces using discrete layer thermal wind;
temperature remains constant within each layer. Exponential velocity amplitudes
are evaluated at reference layer centres, rather than changing a material
layer's temperature or sampling velocity at its displaced physical depth.
Crossing interfaces fail validation. Bottom-intersecting layers collapse to
small positive thicknesses; balance there is approximate. The hydrostatic
check covers full-depth columns, and the interior geostrophic check retains
the centre-f approximation for beta.

Generation writes both `input/initial_state.nc` and `input/layer_coord.nc`.
The latter contains `PTEMP` (°C) and `SALT` (ppt), read by MOM6's
`ts_profile` coordinate initialization, plus EOS-consistent densities in `Layer`. `NK=10`, `USE_REGRIDDING=False`, `COORD_CONFIG="ts_profile"`, and the
LAYER coordinate override match these files. Saved 100-layer reference files
supply only horizontal geometry in this mode. The older setup notebook text
and cached output describe the previous z-star experiment; use this script
and YAML for the layer experiment. No model integration is launched.

## Layer-compatible physics

The failed first layer run stopped because ePBL is ALE-only in this MOM6
source. The configuration now sets `ENERGETICS_SFC_PBL=False`. This removes
ePBL surface turbulent mixing and its Langmuir enhancement; its retained
coefficient settings are inactive. No replacement surface boundary-layer
closure is introduced. `USE_KPP=False` and `BULKMIXEDLAYER=False` explicitly
preserve the fixed-density ten-layer design; a bulk mixed-layer closure would
need a different surface coordinate design. `MLE_USE_PBL_MLD=False` removes
the ePBL-MLD dependency from the already-disabled mixed-layer restratification.

`SIMPLE_TKE_TO_KD=False` selects the exact isopycnal-layer energetics option
in `MOM_set_diffusivity`, replacing the approximate coordinate-general
conversion. The current Law-of-the-Wall bottom diffusivity bypasses this
conversion for bottom mixing, so this switch need not change that contribution.
`MASSLESS_MATCH_TARGETS=True` explicitly keeps vanished-layer properties
consistent with target densities. `ADIABATIC=False` retains diabatic exchange.

Background `KD=2e-5 m2/s`, `KD_MIN=2e-6 m2/s`, `KV=1e-4 m2/s`,
Law-of-the-Wall bottom mixing (`KD_MAX=0.1 m2/s`), Jackson shear mixing,
lateral mixing/viscosity, bottom drag and prescribed forcing remain active as
configured. MEKE, mixed-layer restratification, KPP and the bulk mixed layer
remain off. Layer-mode diapycnal mixing operates through entrainment and
interface movement; this is not an adiabatic eddy experiment.

The source checks are in `MOM_diabatic_driver.F90` (`diabatic_driver_init`
and its layer mixing branch) and `MOM_set_diffusivity.F90`
(`set_diffusivity_init`). Initialization generation now rejects accidentally
re-enabled ePBL or a bulk mixed layer. Configuration and NetCDF checks do not
replace a compiled-model initialization/integration test. Existing failed-run
staging may still contain the earlier parameter values; rerun Payu setup from
the updated control files before testing again.

### Surface forcing for fixed-density layers

The next initialization attempt exposed a further restriction in
`MOM_entrain_diffusive.F90`: without a bulk mixed layer, allocated heat and
freshwater flux arrays are rejected. `BUOY_CONFIG="file"` allocated those
arrays even though all fields in this experiment's forcing file are zero.
The configuration now uses `BUOY_CONFIG="NONE"`, omitting these arrays while
retaining thermodynamics and interior diapycnal mixing. `BUOY_CONFIG="zero"`
would still allocate them and does not resolve the restriction. Wind forcing
remains file-based (the current wind fields are also zero). Introducing
nonzero surface heat/freshwater forcing requires a separate compatible
surface-layer/forcing design. The generator checks this configuration before
writing initial conditions. A new compiled-model test is still required.

## Vorticity-diagnostic topo experiment copy

This copy uses its own `input/` directory and the experiment prefix
`gaussian-eddy-exp-H500_BETA_2p66E11_CE_layer-vortdiag-topo-D2500`. Copied run identity,
logs, manifests, build versions and budget results are retained in `copied_run/`.
Notebook outputs have been cleared. This copy has a fresh Payu UUID and archive
name; run the new experiment before analysing it.
No diagnostic settings have been changed as part of this cleanup.

## Vorticity diagnostic output

See [DIAGNOSTICS.md](DIAGNOSTICS.md) for the current daily native-layer and
29-cell online z-star output specification. This supersedes older output
descriptions above. Runtime output checks remain deferred.

## North–south bottom slope: current 2500 m revision

The interior depth is `2500 + 8e-4 * (y - 250000)` metres, south shallow and
north deep. `BETA=2.66e-11`. The coastline, 45 km shelf width and 25 km quintic
slope blend are retained. Shelf depths are reshaped to meet 2500 m without a
4000 m surrounding trough. Maximum water depth is approximately 2644.75 m;
`MAXIMUM_DEPTH=2700` allows the deeper side without clipping.

The ten reference layers have interfaces 0, 100, 200, 300, 400, 500, 900, 1300,
1700, 2100, 2500 m. Layer temperatures remain 24 to 6 °C in 2 °C increments.
The upper 25 diagnostic cells are retained. Four 114.77 m cells complete the
29-cell z-star diagnostic grid to a nominal depth of 2700 m. Actual interfaces
follow local bathymetry and SSH; vanished cells are masked in diagnostics.

Regenerate topography before initial conditions. The revised bathymetry and
beta require a fresh-start integration, not continuation of the 4000 m restart.
Previous executed notebooks, configuration and budget results are preserved in
`copied_run/pivot4000_beta2e11/`; the original archive remains intact.

## Previous 4000 m slope integration

PBS job `183272148.gadi-pbs` completed with exit status 0. Payu generated
identity `gaussian-eddy-exp-H500_BETA_2E11_CE_layer-vortdiag-topo-55237593`;
`output000` contains the initial 31-day month. The analysis notebook selects
this identity from metadata and checks the archived bathymetry against the
requested slope. Temperature sections use actual diagnostic interfaces;
velocity-animation sections retain nominal z* labels.

The 2500 m revision is staged under `gaussian-eddy-exp-H500_BETA_2p66E11_CE_layer-vortdiag-topo-D2500-13b0b1f8`.
No integration has been submitted for this revision.

## Reversed slope

South is now shallower and north deeper, with interior `dH/dy=+8e-4`.
The 2500 m centre pivot, `BETA=2.66e-11`, native layer interfaces and shelf
blend widths are unchanged. Previous north-shallow inputs and notebook state
are preserved in `copied_run/pivot2500_north_shallow_beta2p66e11/`.
The previous archive remains intact; the reversed slope uses a fresh UUID.

Reversed-slope job `183278193.gadi-pbs` was submitted as a one-month fresh start
under identity `gaussian-eddy-exp-H500_BETA_2p66E11_CE_layer-vortdiag-topo-D2500-south-shallow-af6410db`.
