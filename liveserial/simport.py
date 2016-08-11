"""Module that sets up a virtual serial port for unit testing.
"""
import threading
class ComSimulatorThread(threading.Thread):
    """Simulates a sine wave, masquerading as a separate COM port on the machine so
    that we can unit test the code against it.

    Args:
        port (str): name of the simulated port to write to.
        dataform (tuple): of `type` that specifies how a row of simulated data will
          look when written to the COM port.
        sensors (list): of `str` giving sensor ids for which data will be randomly
          generated with equal probability between each sensor.
        seed (int): random seed so the values are predictable.

    Attributes:
        alive (threading.Event): event for asynchronously handling the reads from
          the serial port.
    """
    def __init__(self, port="com1", sensors=["W", "K"], dataform=(int, float),
                 seed=42):
        threading.Thread.__init__(self)
        self.dataform = dataform
        self.sensors = sensors
        from os import name
        if name  == 'nt':
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
        #Seed the random number generator so that it always produces the same
        #values for the random variables.
        random.seed(self.seed)
        
        while self.alive.isSet():
            #Choose one of the sensors at random to generate data for.
            sensor = random.choice(self.sensors)
            raw = []
            for t in self.dataform:
                if t is int:
                    raw.append(random.randint(0, 100))
                elif t is float:
                    raw.append(random.randint(-1, 1) + random.random())

            data = ' '.join([str(d) for d in raw])
            x = self.serial.write(data + '\n')
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
        threading.Thread.join(self, timeout)

if __name__ == '__main__':
    #This module is intended mainly to be imported and used by the unit
    #tests. However, it can also be run directly, in which case we just simulate
    #some data.
    simsig = ComSimulatorThread()
    import signal
    def exit_handler(signal, frame):
        """Cleans up the serial communication, plotting and logging.
        """
        from liveserial import msg
        msg.warn("SIGINT >> cleaning up threads.", -1)
        simsig.join()
    signal.signal(signal.SIGINT, exit_handler)

    simsig.start()
    while simsig.is_alive():
        simsig.join(1, terminate=False)
