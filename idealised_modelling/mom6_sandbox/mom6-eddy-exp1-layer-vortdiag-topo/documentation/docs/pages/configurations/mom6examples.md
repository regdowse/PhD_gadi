
## Running a simple MOM6 standalone example

For convenience the [input datasets that are required](https://github.com/NOAA-GFDL/MOM6-examples/wiki/Getting-started#installing-data-sets-on-another-platform) to run these examples are downloaded to a common space here:
```
/g/data/ol01/access-iom3-configs/mom6exampledata/
```

Download MOM6 examples github repository:
```
mkdir -p /g/data/$PROJECT/$USER/
cd  /g/data/$PROJECT/$USER/
git clone git@github.com:NOAA-GFDL/MOM6-examples.git
cd MOM6-examples
```

Link the input data
```
cd /g/data/$PROJECT/$USER/MOM6-examples
ln -s /g/data/ol01/access-iom3-configs/mom6exampledata/ .datasets
```

Some chat with Dougie:
> I've modified a few of the configs in:

> /g/data/tm70/ds0092/model/config/MOM6-examples
> E.g. the one we were looking at yesterday is:

> /g/data/tm70/ds0092/model/config/MOM6-examples/ocean_only/global

> @Dougie Squire, do you have all the input files downloaded somewhere?

> I noticed this /g/data/tm70/ds0092/model/config/MOM6-examples/.datasets/README which suggests you just have three of them.
