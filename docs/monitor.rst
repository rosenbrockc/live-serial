Serial Port Monitoring
======================

The monitoring module provides a class structure for interacting with a single
serial port. Multiple class instances can be made for interacting with multiple
ports at the same time and aggregating their data on a single
plot. Synchronization is handled through :class:`~Queue.Queue` instances that
allow multi-thread access to putting and getting data.

.. autoclass:: liveserial.monitor.ComMonitorThread
   :members:

Inferring Raw Data Format
-------------------------

When sensors are not pre-configured, the package provides options for inferring
the format of data by looking for string-valued columns that may represent
sensor keys and then trying `int` and `float` parsing on the remaining
columns. The inferrence is handled on a per-port basis using a class instance
that looks at the first `15` raw lines and attempts to guess what kinds of
sensors are present.

.. autoclass:: liveserial.monitor.FormatInferrer
   :members:
      
Live Feed for Data Aggregation
------------------------------

Serial port data is read off by the :class:`~liveserial.monitor.ComMonitorThread`
instances. However, the amount of data generated on the serial stream exceeds
what we need to generate a useful plot, and sometimes even exceeds our needs for
logging. The :class:`~liveserial.logging.Logger` class instance monitors the data
queues and periodically aggregates that data to form a single value,
representative of the interval between checks (see :doc:`logging`). These single point
values are stored in :class:`~liveserial.monitor.LiveDataFeed`.

.. autoclass:: liveserial.monitor.LiveDataFeed
   :members:

Useful Utility Functions
------------------------

The monitoring module also exposes some useful functions for interacting with
the data and error queues, and for listing available serial ports on a machine.

.. automodule:: liveserial.monitor
   :synopsis: Utility modules for listing ports and getting values from
	      multi-thread queues.
   :members: enumerate_serial_ports, get_all_from_queue, get_item_from_queue
