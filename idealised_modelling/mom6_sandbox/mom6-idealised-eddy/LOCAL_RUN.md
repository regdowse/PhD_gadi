# Local anu-tub run on Gadi

This configuration is prepared for project `fu5`, with the original 240-rank
(6 by 40) ZSTAR layout and a one-day segment. It uses locally built standalone
MOM6 with FMS 2021.01, Intel 2021.10.0, OpenMPI 4.1.2 and NetCDF 4.9.2.

From this directory:

```bash
source env.sh
payu run
```

The environment uses `/g/data/fu5/users/rd7475/.venv/mom6` (Payu 1.3.6).
The first setup creates `metadata.yaml` with the experiment UUID.
Work and output are under `/scratch/fu5/rd7475/tmp/mom6-payu`;
archive important results elsewhere before scratch expiry.

`payu setup` stages the model without submitting a job. If you need to inspect
an existing work directory again, use `payu setup --help` for setup options.

For annual segments after a successful first run, edit `input.nml` to set
`months = 12`, `days = 0`, and increase `walltime` in `config.yaml` (the
original configuration requested `12:00:00`).

## Rebuilding

Source repositories and build files are siblings of this configuration:
`../src/MOM6`, `../src/FMS`, and `../mom6-ninja-nci`.
Compiler logs are `build.log` in each build directory.

```bash
source env.sh
(cd ../mom6-ninja-nci/shared && ninja -j 2 libfms.a)
(cd ../mom6-ninja-nci/ocean_only_symmetric && ninja -j 2 MOM6)
```

The build uses the FMS1 interface for compatibility with FMS 2021.01,
and AVX2 instructions for standard Gadi normal-queue nodes.
No model source modifications are required.
