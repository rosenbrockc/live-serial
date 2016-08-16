"""Class for monitoring a COM port using pyserial on a separate thread so that
that the main UI thread is not blocked or slowed. Code adapted from
https://github.com/mba7/SerialPort-RealTime-Data-Plotter/blob/master/com_monitor.py
"""
import threading, serial
try:
    from Queue import Empty
except ImportError: # pragma: no cover
    #Why couldn't they have called it queue from the start in py2?
    from queue import Empty
    
from liveserial import msg
class ComMonitorThread(threading.Thread):
    """ A thread for monitoring a COM port. The COM port is 
        opened when the thread is started.
    
    Args:
        data_q (multiprocessing.Queue):
            Queue for received data. Items in the queue are
            (data, timestamp) pairs, where data is a binary 
            string representing the received data, and timestamp
            is the time elapsed from the thread's start (in 
            seconds).
        
        error_q (multiprocessing.Queue):
            Queue for error messages. In particular, if the 
            serial port fails to open for some reason, an error
            is placed into this queue.
        
        port (str):
            The COM port to open. Must be recognized by the 
            system.
        
        port_baud (int):
            Rate at which information is transferred in a communication channel
            (in bits/second).    

        stopbits (float): Serial communication parameter; one of (1, 1.5, 2).
        parity: (str): Serial communication parameter; one of ['N', 'E', 'O', 'M', 'S'].
        
        port_timeout (float):
            The timeout used for reading the COM port. If this
            value is low, the thread will return data in finer
            grained chunks, with more accurate timestamps, but
            it will also consume more CPU.
        listener (bool): specifies that this COMThread is a listener, which prints
            out the raw stream in real-time, but doesn't analyze it.
    Attributes:
        alive (threading.Event): event for asynchronously handling the reads from
          the serial port.
        serial_arg (dict): arguments used to contstruct the :class:`serial.Serial`.
        serial_port (serial.Serial): serial instance for communication.
    """
    def __init__(self, data_q, error_q, port, port_baud,
                 port_stopbits=serial.STOPBITS_ONE,
                 port_parity=serial.PARITY_NONE, port_timeout  = 0.01,
                 listener=False, virtual=False):
        threading.Thread.__init__(self)
        
        self.serial_port = None
        self.serial_arg  = dict(port      = port,
                                baudrate  = port_baud,
                                stopbits  = port_stopbits,
                                parity    = port_parity,
                                timeout   = port_timeout)
        if virtual:
            self.serial_arg["dsrdtr"] = True
            self.serial_arg["rtscts"] = True
            
        self.data_q   = data_q
        self.error_q  = error_q
        self.listener = listener
        self.alive    = threading.Event()
        self.alive.set()
        
    def run(self):
        """Starts the COM monitoring thread. If an existing serial connection is
        open, it will be closed and a new one will be created. The monitoring
        will continue indefinitely until :meth:`join` is called.
        """
        try:
            if self.serial_port: # pragma: no cover
                self.serial_port.close()
            self.serial_port = serial.Serial(**self.serial_arg)
            msg.info("Serial port communication enabled.", 2)
        except serial.SerialException as e: # pragma: no cover
            self.error_q.put(e.message)
            return

        from time import time
        start = time()
        lastlisten = None
        while self.alive.isSet():
            line = self.serial_port.readline()
            if self.listener:
                if lastlisten is None or time() - lastlisten > 0.05:
                    print(line)
                    lastlisten = time()
                #This is crazy to me... The if statement above and its contents
                #are covered by the unit tests, but coverage claims that this
                #continue statement is not...
                continue # pragma: no cover
                    
            raw = line.split()
            if len(raw) == 3:
                timestamp = time() - start
                sensor = raw[0]
                try:
                    qdata = float(raw[2])
                    self.data_q.put((sensor, timestamp, qdata))
                except ValueError: # pragma: no cover
                    # There must have been a communication glitch; just ignore
                    # this data point.
                    pass
            
        # clean up
        if self.serial_port:
            self.serial_port.close()
            
    def join(self, timeout=None, terminate=True):
        """Tells the thread monitoring the COM port to clean up and return.

        Args:
            timeout (float): number of seconds (or fractions of seconds) to wait
              until returning. If `None`, then the operation will
              block until the thread terminates. See also
              :meth:`threading.Thread.join`.
            terminate (bool): when True, the data collection is told to stop before
              trying to join the underlying thread; otherwise, the thread will
              keep processing data until join is called with terminate=True.
        """
        if terminate:
            self.alive.clear()
        threading.Thread.join(self, timeout)

def enumerate_serial_ports():
    """Scans for available serial ports.

    Returns:         
    list: of `str` with  the availables port names.
    """
    from os import name
    from glob import glob
    if name  == 'nt': # pragma: no cover
        #We don't have CI setup for windows at the moment.
        outAvailablePorts = []
        for i in range(256):
            try:
                s = serial.Serial(i)
                outAvailablePorts.append(s.portstr)
                s.close()   
            except serial.SerialException:
                pass
        return outAvailablePorts
    else:
        return glob('/dev/tty.*')
    
def get_all_from_queue(Q):
    """Generator to yield one after the others all items currently in the queue Q,
        without any waiting.

    Args:
        Q (Queue.Queue): queue to empty items from.
    """
    msg.info("Retrieving entire queue.", 2)
    try:
        while True:
            yield Q.get_nowait()
    except Empty:
        raise StopIteration

def get_item_from_queue(Q, timeout=0.01):
    """ Attempts to retrieve an item from the queue Q. If Q is
        empty, None is returned.

    Args:
        Q (Queue.Queue): queue to get an item from.
        timeout (float):
            Blocks for 'timeout' seconds in case the queue is empty,
            so don't use this method for speedy retrieval of multiple
            items (use get_all_from_queue for that).
    """
    try: 
        item = Q.get(True, 0.01)
    except Empty: 
        return None
    return item

class LiveDataFeed(object):
    """A simple "live data feed" abstraction that allows a reader to read the most
    recent data and find out whether it was updated since the last read.

    Attributes:
        has_new_data (dict): A boolean attribute telling the reader whether the
          data was updated since the last read; keyed by sensor identifier.
        cur_data (dict): most recent data point placed on the feed; keyed by the
          sensor identifier.
    """
    def __init__(self):
        self.cur_data = {}
        self.has_new_data = {}
        
    def add_data(self, sensor, data):
        """Add new data to the feed.
        
        Args:
        sensor (str): sensor identifier for the data point.
        """
        self.cur_data[sensor] = data
        self.has_new_data[sensor] = True
    
    def read_data(self, sensor):
        """Returns the most recent data."""
        self.has_new_data[sensor] = False
        return self.cur_data[sensor]
