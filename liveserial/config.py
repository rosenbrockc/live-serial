"""Method for sharing global sensor and port configuration values between
modules.
"""
import serial
portdefaults = {
    "port_baud": 9600,
    "port_stopbits": serial.STOPBITS_ONE,
    "port_parity": serial.PARITY_NONE,
    "port_timeout":  0.01,
    "virtual": False,
    "delimiter": r"\s",
    "encoding": "UTF-8"
    }
"""dict: default parameters passed to the :class:`serial.Serial` constructor for
communicating with the serial port.
"""

def _get_parser(config):
    """Returns a :class:`~configparser.ConfigParser` instance for the specified
    file.

    Args:
        config (ConfigParser): instance from which to extract the sensor list
          and port information. `str` is also allowed, in which case it
          should be the path to the config file to load.
    """
    try:
        from configparser import ConfigParser
    except ImportError: # pragma: no cover
        #Renaming of modules to lower case in python 3.
        from ConfigParser import ConfigParser

    if isinstance(config, str):
        parser = ConfigParser()
        parser.readfp(open(config))    
    else: # pragma: no cover
        parser = config               

    return parser
        
_sensors = {}
"""dict: keys are sensor names, values are :class:`liveserial.config.Sensor`
instances.
"""
_sensors_parsed = False
"""bool: when True, we have already scanned the config file for sensor
settings.
"""
def _load_sensors(config):
    """Loads all the sensors from the specified config file.

    Args:
        config (ConfigParser): instance from which to extract the sensor list.
          `str` is also allowed, in which case it
          should be the path to the config file to load.
    """
    global _sensors, _sensors_parsed
    if not _sensors_parsed:
        parser = _get_parser(config)
        if parser is not None:
            #Now that we have the thread, we can add configuration for each of the
            #sensors in the config file.
            from fnmatch import fnmatch
            for section in parser.sections():
                if fnmatch(section, "sensor.*"):
                    name = section[len("sensor."):]
                    _sensors[name] = Sensor(None,name,**dict(parser.items(section)))
                
        _sensors_parsed = True
    
def sensors(config, sensor=None, port=None, monitor=None):
    """Returns the list of :class:`liveserial.config.Sensor` instances that have
    the specified port.

    Args:
        config (ConfigParser): instance from which to extract the sensor list
          and port information. `str` is also allowed, in which case it
          should be the path to the config file to load.
        port (str): name of the port to configure for.
    """
    _load_sensors(config)
    global _sensors
    if port is not None:
        result = {}
        for sensor_n, instance in _sensors.items():
            if instance.port == port:
                instance.monitor = monitor
                if monitor is not None:
                    instance.port = monitor.port
                result[sensor_n] = instance
    elif sensor is not None:
        if sensor in _sensors:
            result = _sensors[sensor]
        else:
            result = None

    return result
                    
_ports = {}
"""dict: keys are port names, values are updated parameter dictionaries that can
be passed to the :class:`liveserial.monitor.ComMonitorThread` constructor.
"""
_ports_parsed = False
"""bool: when True, we have already examined the config file for port settings.
"""
def _load_ports(config):
    """Loads the configured port information from the specified configuraton.
    """
    global _ports, _ports_parsed
    if not _ports_parsed:
        parser = _get_parser(config)
        if parser is None: # pragma: no cover
            _ports_parsed = True
            return
        
        from fnmatch import fnmatch
        for section in parser.sections():
            if fnmatch(section, "port.*"):
                name = section[len("port."):]
            else: # pragma: no cover
                continue

            params = portdefaults.copy()
            for option, value in params.items():
                #Override the value using the config value unless it doesn't
                #exist.
                if parser.has_option(section, option):
                    params[option] = parser.get(section, option)

            #Python's bool is interesting because bool('0') => True. So, we test
            #explicitly here for the option value the user set.
            import re
            if not isinstance(params["virtual"], bool):
                if re.match(r"\b\d+\b", params["virtual"]):
                    params["virtual"] = bool(int(params["virtual"]))
                elif re.match(r"[a-z]", params["virtual"][0], re.I):
                    params["virtual"] = params["virtual"][0].lower() == 't'

            _ports[name] = params
            
        _ports_parsed = True

def ports(config, port):
    """Returns the port configuration dictionary for the specified port name.

    Args:
        config (ConfigParser): instance from which to extract the port
          information. `str` is also allowed, in which case it
          should be the path to the config file to load.
        port (str): name of the port to return configuration for.
    """
    _load_ports(config)
    if port in _ports:
        return _ports[port]
    else: # pragma: no cover
        return portdefaults.copy()

_script = {}
"""dict: keys are command-line arguments usually accepted by the script when it
is run. Values are configured option values from the config file.
"""
_script_parsed = False
"""bool: when True, the script options have been parsed already.
"""
def script(config):
    """Returns the config options configured globally for the script.

    Args:
        config (ConfigParser): instance from which to extract the port
          information. `str` is also allowed, in which case it
          should be the path to the config file to load.
    """
    global _script, _script_parsed
    if not _script_parsed:
        parser = _get_parser(config)
        if parser is not None:
            for section in parser.sections():
                if section == "global":
                    _script = dict(parser.items("global"))

            #We also need to handle the types, since all the options are just
            #strings by default.
            from liveserial.livemon import script_options
            for name in _script:
                optname = "-{}".format(name)
                if optname in script_options and "type" in script_options[optname]:
                    caster = script_options[optname]["type"]
                    _script[name] = caster(_script[name])
        _script_parsed = True
                
    return _script
    
def _config_split(value, delim, cast=None):
    """Splits the specified value using `delim` and optionally casting the
    resulting items.

    Args:
        value (str): config option to split.
        delim (str): string to split the option value on.
        cast (function): to apply to each item after the split operation.
    """
    if value is None:
        return
    
    if delim is None: # pragma: no cover
        vals = value.split()
    else:
        vals = value.split(delim)
        
    if cast is not None:
        return list(map(cast, vals))
    else:
        return vals

_plot = {}
"""dict: of plot options; keys are ['line', 'axes', 'figure', 'label', 'ticks'];
values are dicts of matplotlib option values.

"""
_plot_parsed = False
"""bool: when True, we have parsed plot options already.
"""

def plot(config, element):
    """Returns the matplotlib configuration options for the specified plotting
    element.

    Args:
        config (ConfigParser): instance from which to extract the port
          information. `str` is also allowed, in which case it
          should be the path to the config file to load.
        element (str): one of ['line', 'axes', 'figure', 'label', 'ticks'];
          specifies which part of the plot the options will apply to.
    """
    global _plot, _plot_parsed
    if not _plot_parsed:
        parser = _get_parser(config)
        if parser is not None:
            from fnmatch import fnmatch
            for section in parser.sections():
                if fnmatch(section, "plot.*"):
                    name = section[len("plot."):]
                else: # pragma: no cover
                    continue

                _plot[name] = dict(parser.items(section))
        _plot_parsed = True

    if element in _plot:
        return _plot[element]
    else:
        return {}

def reset_config():
    """Resets the global config variables so that a session can be continued
    with a new config file.
    """
    global _sensors, _ports, _plot, _script
    global _sensors_parsed, _ports_parsed, _plot_parsed, _script_parsed
    _sensors = {}
    _sensors_parsed = False
    _ports = {}
    _ports_parsed = False
    _plot = {}
    _plot_parsed = False
    _script = {}
    _script_parsed = False

def _parse_transform(function):
    """Parses the transform function's fqdn to return the function that can
    actually transform the data.
    """
    if "numpy" in function: # pragma: no cover
        import numpy as np

    return eval(function)            

class Sensor(object):
    """Represents the configuration of a sensor on the serial port.

    Args:
        monitor (ComMonitorThread): parent instance that this sensor is being logged
          with.
        name (str): name of the sensor in the configuration file.
        key (str): sensor key as it will be written to the serial stream, or `None`
          if there isn't a key in the stream (i.e., only values).
        value_index (list): column index/indices of the value that will
          be plotted.
        dtype (list): of `str` or `type`; items must belong to ['key', int, float,
          str]. Represents the order in which values are found in a single line of
          data read from the serial port. Thus `W 129229 0.928379` would be given by
          ["key", int, float].
        label (str): for plots, what to put on the y-axis. Defaults to `name`.
        port (str): name of the port to read this sensor from. Defaults to
          :data:`ComMonitorThread.port`.
        logging (str): comma-separated list of columns indices (zero-based) to
            include in the log file. If not specified, then the default is to
            include *all* data columns in the log file.
        columns (str): comma-separated list of columns headings for the CSV file;
            these are written in the first row of the file. If excluded, they
            default to `Time` and `Value1`, `Value2`, etc.
        legends (str): if the comma-separated list in `value_index` includes more
            than one index, multiple lines are plotted on the same subplot. In that
            case, `legends` allows a comma-separated list of legend labels to be
            provided for each of those lines.
        sensors (str): comma-separated list of sensor names to include in the data
            vector that will be passed to `function` to be aggregated to a single
            value. This only applies to the case of aggregate sensors.
        function (str): name of a function to use to transform the data. Only
            applies to the case of aggregate sensors.
        kwargs (dict): additional keyword arguments supported that do not require
            special processing (i.e., are just simple string values).

    Attributes:
        options (dict): additional keyword arguments (or configurable options) for
          the sensor.
    """
    def __init__(self, monitor, name, key=None, value_index=None,
                 dtype=["key", "int", "float"], label=None, port=None,
                 logging=None, columns=None, legends=None, function=None,
                 sensors=None, **kwargs):

        self.monitor = monitor
        self.name = name
        self.key = key

        #We analyze the string values set for the dtypes to return the python
        #`types` that can cast strings to actual type values.
        self.dtype = []
        self._keyloc = None
        
        from six import string_types
        if isinstance(dtype, string_types):
            dtype = dtype.split(',')

        for i, sentry in enumerate(dtype):
            if sentry == "key":
                self._keyloc = i
                if key is None and port != "aggregate":
                    #For aggregate ports, we relax this condition since the
                    #sensors being aggregated have the dtypes specified
                    #correctly.
                    raise ValueError("You must specify a sensor key if 'key' "
                                     "is in the 'dtype' option list.")
            else:
                caster = eval(sentry)
                self.dtype.append(caster)

        self.value_index = _config_split(value_index, ',', int)
        self.label = name if label is None else label
        self.port = monitor.port if port is None else port
        self.logging = _config_split(logging, ',', int)
        self.columns = _config_split(columns, ',')
        self.legends = _config_split(legends, ',')
        self.sensors = _config_split(sensors, ',')
        
        if function is not None:
            self.transform = _parse_transform(function)
        else:
            self.transform = None
        
        self.options = kwargs
               
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

            #Previously, we were changing the order of the columns based on the
            #value index to make it easier for the plotter. Since we allow
            #multiple values to be plotted on the same subplot now, it is easier
            #to just not mangle them in the first place.
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
