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
portdefaults = {
    "port_baud": 9600,
    "port_stopbits": serial.STOPBITS_ONE,
    "port_parity": serial.PARITY_NONE,
    "port_timeout":  0.01,
    "virtual": False
    }
"""dict: default parameters passed to the :class:`serial.Serial` constructor for
communicating with the serial port.
"""

class Sensor(object):
    """Represents the configuration of a sensor on the serial port.

    Args:
        monitor (ComMonitorThread): parent instance that this sensor is being logged
          with.
        name (str): name of the sensor in the configuration file.
        dtype (list): of `str` or `type`; items must belong to ['key', int, float,
          str]. Represents the order in which values are found in a single line of
          data read from the serial port. Thus `W 129229 0.928379` would be given by
          ["key", int, float].
        label (str): for plots, what to put on the y-axis. Defaults to `name`.
        port (str): name of the port to read this sensor from. Defaults to
          :attr:`ComMonitorThread.port`.
        value_index (int): column index of the value that will be plotted.
    """
    def __init__(self, monitor, name, key=None, value_index=None,
                 dtype=["key", "int", "float"], label=None, port=None,
                 **kwargs):

        self.monitor = monitor
        self.name = name
        self.key = key

        #We analyze the string values set for the dtypes to return the python
        #`types` that can cast strings to actual type values.
        self.dtype = []
        self._keyloc = None
        if isinstance(dtype, str):
            dtype = dtype.split(',')
        for i, sentry in enumerate(dtype):
            if sentry == "key":
                self._keyloc = i
                if key is None:
                    raise ValueError("You must specify a sensor key if 'key' "
                                     "is in the 'dtype' option list.")
            else:
                caster = eval(sentry)
                self.dtype.append(caster)

        self.value_index = int(value_index)
        self.label = name if label is None else label
        self.port = monitor.port if port is None else port

    def _cast(self, raw):
        """Casts all the values in the given list to their relevant data
        types. Assumes that the list has the correct format.
        
        Args:
            vals (list): string values from the split line to cast.
        """
        if (len(raw) != len(self.dtype)
            + (1 if self._keyloc is not None else 0)): # pragma: no cover
            return
        
        try:
            vals = []
            for iv, v in enumerate(raw):
                if iv != self._keyloc:
                    vals.append(self.dtype[len(vals)](v))
                    
            if self.value_index is not None and self.value_index > 0:
                #We have to change the order in which the values are
                #returned. The plotting and logging routines expect the plotted
                #value to be in position 2 (after sensor and timestamp). The
                #remaining values can come in any order.

                #The value index is specified relative the full list of columns;
                #but we exclude the key from the list of values. If a key is
                #specified, we need to subtract 1 from value index, if the key
                #index comes before the value index.
                if self._keyloc is not None and self._keyloc < self.value_index:
                    first = vals[self.value_index-1]
                else:
                    first = vals[self.value_index]
                    
                result = [first]
                for i, val in enumerate(vals):
                    if i != self.value_index:
                        result.append(val)
                return result
            else: # pragma: no cover 
                return vals
        except ValueError: # pragma: no cover
            return None
        
    def parse(self, raw):
        """Parses a single line read from the serial port and returns a tuple of
        values.

        Args:
            raw (list): of split ASCII-encoded strings from the serial port. 
        
        Returns:
            list: of values parsed using :attr:`Sensor.dtype` casting.
            None: if the `key` was not found in the correct location.
        """
        result = None
        if self._keyloc is not None:
            if raw[self._keyloc] == self.key:
                result = self._cast(raw)
        elif self.key is None:
            result = self._cast(raw)
            
        return result

class FormatInferrer(object):
    """Class that can infer the data types of an unknown sensor stream, provided
    they are consistent between calls.

    Args:
        infer_limit (int): number of raw lines to consider before reaching consensus
            on the format of the data (when inferring).
    """
    def __init__(self, infer_limit=15):
        self.infer_limit = infer_limit
        self._infer_count = 0
        """int: number of lines that have been analyzed alread for inferring data
        structure when no configuration is provided.
        """
        self._infer_keys = {}
        """dict: keys are sensor names, values are the indices at which the
        sensor key can be found in the raw line.
        """
        self.inferred = {}
        """dict: keys are inferred sensor ids, values are lists of casting
        types as for the implementation in :class:`Sensor`. This dict only
        gets populated when no configuration is available and data structure has
        to be inferred from the incoming stream.
        """        

    def _infer_structure(self, raw):
        """Infers the structure of the raw data; returns the parsed line.
        
        Args:
            raw (list): of `str` values read from the line.
        """
        #We still try to infer some structure for the data by looking at
        #each value and trying to parse it as either int or float.
        dtype = []
        key = None
        for i, val in enumerate(raw):
            try:
                ival = int(val)
                dtype.append(int)
            except ValueError:
                try:
                    fval = float(val)
                    dtype.append(float)
                except ValueError:
                    key = i

        #Now that we have the general format, see if we can pick out the
        #sensor key from the string-valued entry.
        sensor = None
        if key is not None:
            sensor = raw[key]
        self._infer_keys[sensor] = key
                                         
        if sensor not in self.inferred:
            self.inferred[sensor] = dtype
        else:
            current = self.inferred[sensor]
            if current != dtype: # pragma: no cover
                #It turned out with unit testing that the consensus was reached
                #immediately so that this never fired.
                
                #We hope that the inferrence will reach a consensus at some
                #point. If it doesn't, do we take the latest point or stick
                #with the original? Probably, the first points will have the
                #highest likelihood to be incomplete.
                self.inferred[sensor] = dtype

    def parse(self, raw):
        """Attempts to parse the specified string values into one of the formats
        that has been inferred by this instance.

        Args:
            raw (list): of `str` values read from the line.
        """
        if self._infer_count < self.infer_limit:
            self._infer_structure(raw)
            self._infer_count += 1
            #We need to throw away the first points while we are inferring the
            #structure of the data.
            return (None, None)

        try:
            for k, v in self._infer_keys.items():
                if v is None:
                    continue
                if raw[v] == k:
                    result = []
                    for i in range(len(raw)):
                        if i != v:
                            caster = self.inferred[k][len(result)]
                            result.append(caster(raw[i]))

                    #This step makes sure that we have the right number of
                    #points to return.
                    if len(result) == len(self.inferred[k]):
                        return (result, k)
                    else: # pragma: no cover
                        # We have multiple checks to make sure the lengths are
                        # consistent, so this never fires in unit tests.
                        return (None, k)
            else:
                return ([t(r) for t, r in zip(self.inferred[None], raw)], None)
        except ValueError: # pragma: no cover
            #If the inference works correctly, we have already worked through
            #the formatting of the stream so that it should always parse
            #properly.
            return None, None
        
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
        infer_limit (int): number of raw lines to consider before reaching consensus
            on the format of the data (when inferring). If None, then a format
            inferrer is not created.
        virtual (bool): when True, additional serial port parameters are set so that
            the monitor can work with `socat` or other virtual ports.
    Attributes:
        alive (threading.Event): event for asynchronously handling the reads from
          the serial port.
        serial_arg (dict): arguments used to contstruct the :class:`serial.Serial`.
        serial_port (serial.Serial): serial instance for communication.
        sensors (dict): keys are sensor names; values are Sensor instances used to
          parse raw lines read from the serial port.
        inferrer (FormatInferrer): for inferring the format in the absence of
            configured sensor structure.
    """
    def __init__(self, data_q, error_q, port, port_baud,
                 port_stopbits=serial.STOPBITS_ONE,
                 port_parity=serial.PARITY_NONE, port_timeout  = 0.01,
                 listener=False, virtual=False, infer_limit=15):
        threading.Thread.__init__(self)

        self.port = port
        self.serial_port = None
        self.serial_arg  = dict(port      = port,
                                baudrate  = port_baud,
                                stopbits  = port_stopbits,
                                parity    = port_parity,
                                timeout   = port_timeout)
        if virtual:
            msg.std("Running in virtual serial port mode.", 2)
            self.serial_arg["dsrdtr"] = True
            self.serial_arg["rtscts"] = True
            
        self.data_q   = data_q
        self.error_q  = error_q
        self.listener = listener
        self.sensors = {}
        self._manual_sensors = False
        """bool: when True, the sensors list was constructed manually using a
        configuration file; otherwise, it was inferred from the first few lines
        of data from the serial port.
        """
        if infer_limit is not None:
            self.inferrer = FormatInferrer(infer_limit)
        else: # pragma: no cover
            self.inferrer = None
        self.alive    = threading.Event()
        self.alive.set()

    @staticmethod
    def from_port(port, port_baud=9600, virtual=False):
        """Returns a COMMonitor instance for the specified port using the
        default configurati of port parameters and with inferrence for the structure
        of the data.

        Args:
            port (str):
                The COM port to open. Must be recognized by the 
                system.
            
            port_baud (int):
                Rate at which information is transferred in a communication channel
                (in bits/second).    
        """
        from multiprocessing import Queue
        dataq = Queue()
        errorq = Queue()
        return ComMonitorThread(dataq, errorq, port, port_baud, virtual=virtual)
        
    @staticmethod
    def from_config(config, port, dataq=None, errorq=None, listener=False,
                    sfilter=None):
        """Returns a COMMonitor instance from the specified configuration
        parser.

        Args:
            config (ConfigParser): instance from which to extract the sensor list
              and port information. `str` is also allowed, in which case it
              should be the path to the config file to load.
            port (str): name of the port to configure for.
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
            listener (bool): specifies that this COMThread is a listener, which prints
                out the raw stream in real-time, but doesn't analyze it.
            sfilter (list): of sensor names that should be *included* in the
              monitor. By default, all sensors in the config are included that
              match the port.
        Returns:
            ComMonitorThread: instance created using the configuration
            parameters.
        """
        if isinstance(config, str):
            try:
                from configparser import ConfigParser
            except ImportError: # pragma: no cover
                #Renaming of modules to lower case in python 3.
                from ConfigParser import ConfigParser
                
            parser = ConfigParser()
            parser.readfp(open(config))
        else: # pragma: no cover
            parser = config
        
        from multiprocessing import Queue
        #We allow the user to choose to use a common data and error queue
        #between all the threads. If they don't specify one, then we will just
        #create a new one.

        #This method is usually called from the entry script, which allows all
        #the ports to share the same multiprocessing queues by default.
        if dataq is None: # pragma: no cover
            dataq = Queue()
        if errorq is None: # pragma: no cover
            errorq = Queue()

        #If the port has non-default settings, they will be in a special section
        #with the port name.
        portsec = "port.{}".format(port)
        params = portdefaults.copy()
        if parser.has_section(portsec):
            for option, value in params.items():
                #Override the value using the config value unless it doesn't
                #exist.
                if parser.has_option(portsec, option):
                    params[option] = parser.get(portsec, option)

        #Python's bool is interesting because bool('0') => True. So, we test
        #explicitly here for the option value the user set.
        import re
        if not isinstance(params["virtual"], bool):
            if re.match(r"\b\d+\b", params["virtual"]):
                params["virtual"] = bool(int(params["virtual"]))
            elif re.match(r"[a-z]", params["virtual"][0], re.I):
                params["virtual"] = params["virtual"][0].lower() == 't'

        vtext = "{}: using {} as config-set serial paramaters."
        msg.std(vtext.format(port, params))
        result = ComMonitorThread(dataq, errorq, port, listener=listener,
                                  **params)

        #Now that we have the thread, we can add configuration for each of the
        #sensors in the config file.
        from fnmatch import fnmatch
        for section in parser.sections():
            if fnmatch(section, "sensor.*"):
                sport = None
                if parser.has_option(section, "port"):
                    sport = parser.get(section, "port")
                if sport == port:
                    name = section.split('.')[1]
                    result.add_sensor(name, dict(parser.items(section)))

        return result

    def add_sensor(self, name, options):
        """Adds a sensor to the COM monitors active list. Sensors in the active
        list have their data parsed and pushed to the data queue. If no sensors
        are added to the list, the monitor will try to infer the sensor
        configuration using the first few raw data samples.

        Args:
            options (dict): keys are option names from the sensors.cfg file; values
              are the option values.
        """
        self._manual_sensors = True
        sensor = Sensor(self, name, **options)
        self.sensors[name] = sensor
        
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
                    
            raw = line.decode("ASCII").split()
            if len(raw) == 0: # pragma: no cover
                #No data read from the stream.
                continue
            
            vals, sensor = None, None
            if self._manual_sensors:
                for sensor in self.sensors.values():
                    vals, sensor = sensor.parse(raw), sensor.key
                    #The parsing will return None if the raw line does not apply
                    #to its configuration. The moment we found the one that does
                    #apply, there is not sense in still checking.
                    if vals is not None:
                        break
            else:
                #We try to infer the structure of the data from the raw line.
                if self.inferrer is not None:
                    vals, sensor = self.inferrer.parse(raw)
                
            if vals is not None and len(vals) > 0:
                if sensor is None:
                    #We use the id of the com thread (which corresponds
                    #one-to-one with the serial ports) as the sensor key; that
                    #way, multiple inferred, null-key sensors from different
                    #ports can still be differentiated in the logs.
                    sensor = id(self)
                timestamp = time() - start
                self.data_q.put((sensor, timestamp) + tuple(vals))
            #else:
            # There must have been a communication glitch; just ignore
            # this data point.
            
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
