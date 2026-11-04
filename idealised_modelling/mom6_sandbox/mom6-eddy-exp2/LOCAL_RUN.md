# MOM6 eddy exp2 on Gadi

This directory is independent of `mom6-idealised-eddy`. Its own metadata identifies
its current archive; its notebooks use only paths under this experiment.

```bash
cd /g/data/fu5/users/rd7475/github/phd/idealised_modelling/mom6_sandbox/mom6-eddy-exp2
module purge
source env.sh
python initialisation/generate_initial_state.py
payu run --initial 0
```

Use a fresh UUID for independent tests. Plain `payu run` intentionally continues
from this experiment's latest restart. Existing source-experiment archives are
preserved; copied bookkeeping is retained as `copied_archive/` and `copied_work`.

The current duration is one model month, using 100 CPUs and 30 minutes walltime.
`experiment_prefix` in config.yaml determines the archive prefix. The analysis
notebook reads this directory's metadata automatically; restart its kernel and
Run All after output is archived. Daily depth-level thetao and volcello are
written together to ocean_daily.nc.

Nonzero beta uses the documented centre-f approximate initialization. Inspect
initialisation/validation.json before interpreting the run.

Exp2 is the AE counterpart: the analytic streamfunction sign is reversed; velocity,
SSH and temperature anomalies are regenerated together. Copied CE metadata,
links and manifests are records under copied_CE_bookkeeping/, not live restart inputs.

The AE UUID is already initialized by a successful `payu setup --new-uuid`.
The unrun setup was verified and retained under setup_preview/; its active scratch
work directory was retired so the first `payu run --initial 0` can stage normally.
No model simulation has been submitted. For later independent tests use
`payu run --new-uuid --initial 0`; plain `payu run` continues an existing run.
