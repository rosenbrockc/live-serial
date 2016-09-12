Plotting and Logging Overview
=============================

The API is structured around classes that inherit from thread so that they can
interact with multiple serial ports simultaneously without affecting the
performance of the main thread. There are three procedures running in separate
threads:

1. serial port communication (see :doc:`monitor`)
2. periodic aggregation and logging of serial stream (see :doc:`logging`)
3. plotting of live streams for multiple sensors (see :doc:`plotting`)

`livemon.py` provides script access to each of these procedures and handles
connecting them together so that plotting and logging can happen
simultaneously.

.. automodule:: liveserial.livemon
   :synopsis: Script access to threading classes and methods.
   :members: run
