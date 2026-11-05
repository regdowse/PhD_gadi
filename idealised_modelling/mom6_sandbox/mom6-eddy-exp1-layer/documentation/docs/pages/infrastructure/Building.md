# Building MOM6

To run idealised models, or add extra features for yourself and others, you will likely need to build a MOM6 executable.
The aim of this page is provide instructions for how to do this using the infrastructure provided by ACCESS-NRI.
If you notice anything that is missing or could be improved in the explanation please [raise an issue!](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs/issues)

# Building a standalone MOM6 executable

The below are instructions for how to build a standalone MOM6 executable.
Here, we show two ways of building MOM6 standalone using [Spack](https://spack.io/) with OM3.

For some inspiration of why this is fun, have a look at the available test cases in the [`MOM6-examples` repository](https://github.com/NOAA-GFDL/MOM6-examples/tree/dev/gfdl/src). For some additional background on the below two workflows, see these official docs:

 - [Modify and build an ACCESS model's source code](https://docs.access-hive.org.au/models/build_a_model/build_source_code/)
 - [Create Prereleases and Releases for an ACCESS Model](https://docs.access-hive.org.au/models/build_a_model/create_a_prerelease/)

## Building MOM6 standalone within your own Spack environment
!!! tip
    This option is slower but does not require `write` access to [ACCESS-NRI/ACCESS-OM3](https://github.com/ACCESS-NRI/ACCESS-OM3). It does require your own Spack installation.

Before starting on the below steps, you need to install your own version of Spack. There are instructions on how to do that [here](https://docs.access-hive.org.au/getting_started/spack/#enable-spack), you can stop once you've completed the [enable spack step](https://docs.access-hive.org.au/getting_started/spack/#enable-spack) (i.e. you may skip the test step). With spack installed, we first need to change to the spack directory, then load spack's custom bash script and check everything is up to date:

```bash
cd /g/data/$PROJECT/$USER/spack/0.22
. spack-config/spack-enable.bash
cd spack-packages
git pull
cd ../spack-config 
git pull
cd /g/data/$PROJECT/$USER/spack/0.22
```

<terminal-window>
  <terminal-line data="input"> cd /g/data/$PROJECT/$USER/spack/0.22</terminal-line>
  <terminal-line data="input", directory="0.22">. spack-config/spack-enable.bash</terminal-line>
  <terminal-line data="input", directory="0.22">cd spack-packages</terminal-line>
  <terminal-line data="input", directory="spack-packages">git pull</terminal-line>
  <terminal-line>pull any git changes to spack-packages</terminal-line>
  <terminal-line data="input", directory="spack-packages">cd ../spack-config</terminal-line>
  <terminal-line data="input", directory="spack-config">git pull</terminal-line>
  <terminal-line data="input", directory="spack-config"> cd /g/data/$PROJECT/$USER/spack/0.22</terminal-line>
</terminal-window>

Now we clone ACCESS-OM3 into our spack directory:
```bash
git clone git@github.com:ACCESS-NRI/ACCESS-OM3.git
cd ACCESS-OM3
git tag #check out the release you want
git checkout 2025.08.001
```

<terminal-window>
  <terminal-line data="input", directory="0.22">git clone git@github.com:ACCESS-NRI/ACCESS-OM3.git</terminal-line>
  <terminal-line>Cloning into ACCESS-OM3...</terminal-line>
  <terminal-line data="input", directory="0.22">cd ACCESS-OM3</terminal-line>
  <terminal-line data="input", directory="ACCESS-OM3">git tag</terminal-line>
  <terminal-line data="input", directory="ACCESS-OM3">git checkout 2025.08.001</terminal-line>
  <terminal-line>switching to '2025.08.001'</terminal-line>
</terminal-window>

At this point we need to modify the `ACCESS-OM3/spack.yaml` so it knows how to build MOM6 on it's own, we do this by modifying this line:
```yaml
spack:
  specs:
    - access-om3@git.2025.08.001
```

To this:
```yaml
spack:
  specs:
    - access-mom6@2025.07.000 fflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" cflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" cxxflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" ~access3

```
Note the use of `access-mom6` at `@2025.07.000`, this is because that is what was originally specified in the spack.yaml with tag `2025.08.001`.
Then we have to comment out the following lines:
```yaml
    access-mom6:
      require:
        - '@2025.07.000'
        - 'fflags="-march=sapphirerapids -mtune=sapphirerapids -unroll"'
        - 'cflags="-march=sapphirerapids -mtune=sapphirerapids -unroll"'
        - 'cxxflags="-march=sapphirerapids -mtune=sapphirerapids -unroll"'
```

Now we can create the spack environment in which to build MOM6:
```bash
cd ..
spack env create mom6standalone ACCESS-OM3/spack.yaml
```

<terminal-window>
  <terminal-line data="input", directory="ACCESS-OM3">cd ..</terminal-line>
  <terminal-line data="input", directory="0.22">spack env create mom6standalone ACCESS-OM3/spack.yaml</terminal-line>
  <terminal-line><span class="spack-indigo bold">\==></span> Created environment <span class="spack-cyan">mom6standalone</span> in: <span class="spack-cyan">/g/data/$PROJECT/$USER/spack/0.22/environments/mom6standalone</span></terminal-line>
  <terminal-line><span class="spack-indigo bold">\==></span> Activate with: <span class="spack-cyan">spack env activate mom6standalone</span></terminal-line>
</terminal-window>

Finally, we `activate` the mom6standalone environment and build MOM6:
```bash
spack env activate mom6standalone -p
spack concretize -f --fresh
spack install access-mom6 ~access3
```

<terminal-window>
    <terminal-line data="input", directory="0.22">spack env activate -p mom6standalone</terminal-line>
    <terminal-line data="input" directory="[mom6standalone] 0.22" class="spack" >spack concretize -f --fresh</terminal-line>
    <terminal-line data="input" directory="[mom6standalone] 0.22" class="spack" >spack install access-mom6 ~access3</terminal-line>
</terminal-window>

These last two commands will take some time.
!!! tip
    `spack concretize` only needs to be re-run if there are changes to the `spack.yaml` file. If changes are made to the MOM6
    source code that `mom6standalone` is built from, running `spack install` should be sufficient for the build system to use the modified source code.
     However, if something does not work correctly running `spack concretize` should fix things up.

Once completed one can find the executable with `which mom6`:

<terminal-window>
<terminal-line data="input" directory="[mom6standalone] 0.22" class="spack" >which mom6</terminal-line>
<terminal-line>/g/data/$PROJECT/$USER/spack/0.22/environments/mom6standalone/.spack-env/view/bin/mom6</terminal-line>
</terminal-window>

!!! warning
    The `mom6` executable can only be found if the spack environment it is built from is `activated`. Specifically,
    if `spack deactivate` is run, the command `which mom6` will not be able to find the MOM6 executable unless it is added.
    to `PATH`.

## Building MOM6 standalone with a pre-release build 
!!! tip
    This option is faster but requires `write` access to [ACCESS-NRI/ACCESS-OM3](https://github.com/ACCESS-NRI/ACCESS-OM3).

!!! warning
    This is [NOT a supported workflow](https://github.com/ACCESS-NRI/ACCESS-OM3/pull/151#issuecomment-3326505434) and is only provided to show that it is possible.

1. Create branch from main, e.g. `cbull_test_mom6standalone`
1. Edit the spack.yaml to have the following line:
```yaml
spack:
  specs:    
    - access-mom6@2025.07.000 fflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" cflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" cxxflags="-march=sapphirerapids -mtune=sapphirerapids -unroll" ~access3
```
1. create a pre-release by opening a pull request with the above change ([example](https://github.com/ACCESS-NRI/ACCESS-OM3/pull/151))

When loading the pre-release a slight change of text is needed, here's an example:
```bash
module purge
module use /g/data/vk83/prerelease/modules
module load access-mom6/pr151-4
which mom6
```

<terminal-window>
  <terminal-line data="input", directory="0.22">module purge</terminal-line>
  <terminal-line data="input", directory="0.22">module use /g/data/vk83/prerelease/modules</terminal-line>
  <terminal-line data="input", directory="0.22">module load access-mom6/pr151-4</terminal-line>
  <terminal-line>Loading access-mom6/pr151-4</terminal-line>
  <terminal-line>Loading requirement: access-mom6/dependencies/pr151-4/access-mocsy/2025.07.002-ucihukj access-mom6/dependencies/pr151-4/access-generic-tracers/2025.08.000-lbeknxx</terminal-line>
  <terminal-line data="input", directory="0.22">which mom6</terminal-line>
  <terminal-line>/g/data/vk83/prerelease/apps/spack/0.22/release/linux-rocky8-x86_64_v4/oneapi-2025.2.0/access-mom6-2025.07.000-ruhunvj5oyc2nidysvbmajb42ehtszzm/bin/mom6</terminal-line>
</terminal-window>

Then add the following to your `config.yaml`:
```yaml
modules:
    use:
        - /g/data/vk83/prerelease/modules
    load:
        - access-mom6/pr151-4

model: mom6
exe: mom6
```
The model field is the name of the Payu "model driver" to use. The `exe` field is the path to the executable (or just the executable name if it is already in your PATH).

## Additional resources for running MOM6 standalone 

Here are some other guides for building MOM6 using [FMS](https://www.gfdl.noaa.gov/fms/).
These builds will be more difficult to relate to ACCESS-OM3. Links:

 - [Building with `ninja`](https://github.com/angus-g/mom6-ninja-nci)
 - [Building with Autoconf](https://noaa-gfdl.github.io/MOM6/ac/)
 - [Presentation slides on building MOM6](https://www.marshallward.org/mom6workshop/build.html#/title-slide)
 - [Step-by-step video guide to building MOM6](https://www.youtube.com/watch?v=xuqjV1OYjbI)

