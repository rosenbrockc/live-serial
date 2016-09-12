[![Build Status](https://travis-ci.org/rosenbrockc/live-serial.svg?branch=master)](https://travis-ci.org/rosenbrockc/live-serial) [![Coverage Status](https://coveralls.io/repos/github/rosenbrockc/live-serial/badge.svg?branch=master)](https://coveralls.io/github/rosenbrockc/live-serial?branch=master) [![PyPI](https://img.shields.io/pypi/v/live-serial.svg)](https://pypi.python.org/pypi/live-serial/)

# `live-serial`: real-time serial port plotter/logger

`live-serial` is a simple package that ties `pyserial`, `matplotlib` and
`csv` together to create a real-time plotter and logger of serial port
data. This is intended to make life easier for people who work with sensors who
need to see real-time feedback when they interact with the sensors.

## Quickstart

```
pip install live-serial
```

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

for linux or MacOS. That command will open a live plotting window and log the
port data to file simultaneously. To see a full list of examples and
command-line arguments, type `livemon.py -examples`.

## Configuration Files

Although the command-line parameters are useful for many quick tasks, repetitive
debugging of a multi-sensor serial port setup can be tedious. For these cases,
we recommend creating a configuration file (an example is shown in
[sensors.cfg](https://github.com/rosenbrockc/live-serial/blob/master/sensors.cfg)). This
is also a great way to share configuration information with other team members
working on the same project: they just need to change the port numbers in the
config file for their system.

The documentation on configuration options is at [API
Documentation](https://rosenbrockc.github.io/liveserial/config.html).

## Running the Unit Tests

To run all the unit tests to make sure that your local setup is working
correctly, you will need to have `socat` installed (for UNIX-based systems), or
some virtual COM ports running (for Windows). `socat` is available via `apt-get`
and `brew`. For Windows systems, you will need to find a virtual port generator
(we have used https://freevirtualserialports.com/ before and it worked fine). On
Windows, the COM ports are assigned by the OS, so we can't label them for
you. The scripts expect `COM1` and `COM3` to be the writeable, virtual ports
(attached to `COM2` and `COM4` respectively). If that is not the case, the unit
tests will not work out of the box for you. You can edit `tests/conftest.py` (~
line 20) and `tests/test_multi.py` (~ line 15) to use different port numbers.

```
cd live-serial
tox
```

## API Documentation

Full API documentation is hosted at [github
pages](https://rosenbrockc.github.io/liveserial/).