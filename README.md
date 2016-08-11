# `live-serial`: real-time serial port plotter/logger

`live-serial` is a simple package that ties `pyserial`, `matplotlib` and
`pandas` together to create a real-time plotter and logger of serial port
data. This is intended to make life easier for people who work with sensors who
need to see real-time feedback when they interact with the sensors.

## Quickstart

```
pip install live-serial
cd live-serial
tox
```

This will install live-serial and run all the unit tests to make sure that your
local setup is working correctly.

## Start Monitoring

The package includes a script `livemon.py` that starts the plotting and
logging. Although the script is documented internally, the most common use cases
are:

```
livemon.py COM3 -logdir C:\sensordata\
```

on a Windows machine, and:

```
livemon.py /dev/ttyACM0 -logdir ~/sensordata
```

for linux or MacOS. To see a full list of examples and command-line arguments,
type `livemon.py -examples`.
