Multiple Sensor Configuration File
==================================

`liveserial` can handle multiple serial ports simultaneously, as well as
multiple sensor streams per serial port. Since each device can have a different
data format arriving at the serial port, we need a way for the user to specify
what to expect for each sensor.

An example file is in the repo (see :download:`sensors.cfg
<../liveserial/sensors.cfg>`). Basically, each sensor has its own section with
the following possible options:

- **key** text that identifies this sensor when it is part of a multi-sensor
  stream on a single port.
- **format** comma-separated list of python data types (`str`, `int`, `float`)
  and `key` to specify the column location that the key will be at.
- **port** name of the serial port on the local machine that this sensor's data
  will arive at.
- **label** for plotting, what label to include on the `y` axis.

Since the config file format is extensible, it is easy to add additional options
later on. The default :class:`~ConfigParser.ConfigParser` is used to extract the
sections (sensors) and their options.
