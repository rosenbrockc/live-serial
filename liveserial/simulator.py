"""Thread for simulating writes to a virtual port.
"""
import threading
from liveserial import msg
class ComSimulatorThread(threading.Thread):
    """Simulates a sine wave, masquerading as a separate COM port on the machine so
    that we can unit test the code against it.

    Args:
        port (str): name of the simulated port to write to.
        dataform (dict): keys are sensor ids; values are tuples of `type` that
          specifies how a row of simulated data will look when written to the COM
          port.
        sensors (list): of `str` giving sensor ids for which data will be randomly
          generated with equal probability between each sensor.
        seed (int): random seed so the values are predictable.

    Attributes:
        alive (threading.Event): event for asynchronously handling the reads from
          the serial port.
    """
    def __init__(self, port="lscom-w", sensors=["W", None, "K"],
                 dataform=[(int, float), (float, float), (int, float)],
                 seed=42):
        threading.Thread.__init__(self)
        self.dataform = {s: d for s, d in zip(sensors, dataform)}
        self.sensors = sensors
        from os import name
        if name  == 'nt': # pragma: no cover
            self.port = port
        else:
            self.port = "/dev/tty.{}".format(port)

        from serial import Serial
        self.serial = Serial(self.port, 9600, dsrdtr=True, rtscts=True)
        self.seed = seed
        self.alive = threading.Event()
        self.alive.set()
        
    def run(self):
        """Starts simulating the communication.
        """
        import random, time, math
        import os
        #Seed the random number generator so that it always produces the same
        #values for the random variables.
        random.seed(self.seed)
        
        while self.alive.isSet():
            #Choose one of the sensors at random to generate data for.
            randsense = int(len(self.sensors)*random.random())
            sensor = self.sensors[randsense]
            if sensor is not None:
                raw = [sensor]
            else:
                raw = []
                
            for t in self.dataform[sensor]:
                if t is int:
                    raw.append(random.randint(0, 100))
                elif t is float:
                    raw.append(random.randint(-1, 1) + random.random())

            data = ' '.join([str(d) for d in raw]) + os.linesep
            #Usually people encode with UTF-8. However, we know that our data is
            #really simple and ASCII takes less space.
            x = self.serial.write(data.encode("ascii"))
            time.sleep(0.0025)

        if self.serial:
            self.serial.close()

    def join(self, timeout=None, terminate=True):
        """Tells the thread simulating the COM port to clean up and return.

        Args:
            timeout (float): number of seconds (or fractions of seconds) to wait
              until returning. If `None`, then the operation will
              block until the thread terminates. See also
              :meth:`threading.Thread.join`.
        """
        if terminate:
            self.alive.clear()
            self.serial.cancel_write()
            self.serial.flushOutput()
        threading.Thread.join(self, timeout)
