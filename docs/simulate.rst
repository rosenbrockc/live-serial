Serial Port Simulation
======================

For unit testing, we setup virtual serial ports. On UNIX-based systems, we can
use `socat` to create the virtual ports. Once the linked, virtual ports exist,
we write random data to them (with fixed random seed) using a simulator
thread. The simulator is defined in
:class:`liveserial.simulator.ComSimulatorThread` and an entry script for
creating a local simulator is included in `simport.py`.

.. automodule:: liveserial.simulator
   :synopsis: Sensor data separation, aggregation and logging.
   :members:      
