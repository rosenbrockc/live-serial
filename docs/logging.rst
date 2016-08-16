Data Logging
============

`liveserial` provides support for logging multiple sensor streams from a single
serial port. To differentiate the streams, serial expects a key to be specified
in the global configuration file (see :doc:`config`). Once the data lines can be
differentiated by the sensor key, the data is split in the plots and log files.

In addition to just logging the data to `csv` files, the logging module also
handles the periodic querying of the data queues that the serial monitor threads
continuously write to (see :doc:`monitor`). Thus, even in the event that the user
chooses no file logging, a :class:`liveserial.logging.Logger` instance is still
needed to help the :doc:`plotting` and :doc:`monitor` to talk to each other.

There are two different intervals configured for the logging:

1. `buffertime`: how often (in milliseconds) the logger aggregates the serial
   data queues to produce a single value.
2. `logfreq`: how often (in seconds) the logger appends the latest data points
   to the `csv` files for persistent storage.

Because the logger implements :class:`threading.Timer` to handle the aggregation
and saving, the main thread doesn't experience latency for large datasets being
written to disk, which allows the plotting to continue smoothly.

.. automodule:: liveserial.logging
   :synopsis: Sensor data separation, aggregation and logging.
   :members:      
