# MOM6 eddy exp1 on Gadi

This directory is independent of `mom6-idealised-eddy`. Its own metadata identifies
its current archive; its notebooks use only paths under this experiment.

```bash
cd /g/data/fu5/users/rd7475/github/phd/idealised_modelling/mom6_sandbox/mom6-eddy-exp1
module purge
source env.sh
python initialisation/generate_initial_state.py
payu run --new-uuid --initial 0
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
