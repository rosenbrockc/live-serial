"""Methods for grabbing data and logging it to CSV files.
"""
class Logger(object):
    """Logs data points from the serial port to CSV. The arguments to this class
    constructor are also available as attributes on the class instance.

    Args:
        interval (int): how often (in milliseconds) to read data from the serial
          buffer.
        dataqs (list): of :class:`multiprocessing.Queue`; stores the data read
          in from the serial port.
        errorqs (list): of :class:`multiprocessing.Queue`; stores any error
          raised during serial port reading.
        livefeed (monitor.LiveDataFeed): feed for storing the latest data points
          obtained from the serial port.
        method (str): one of ['average', 'last'] specifies how to aggregate multiple
          data points in the buffer.
        logdir (str): directory to place log files in for the sensors. If `None`,
          then data will *not* be logged to disk.
        logfreq (int): how often (in seconds) to write the accumulated data points
          to CSV.
        plotting (bool): when False, the values being read off will be printed if
          logging is not enabled.
        config (ConfigParser): global sensor configuration parser; if the
          argument is a `str`, then the file path.
    Attributes:
        timer (threading.Timer) executes calls to the serial port reader to get the
          latest data and push it to the live feed.    
        lastsave (float): timestamp indicating the last time the CSV file was
          appended to
        csvdata (dict): lists of sensor time and value readings, keyed by sensor
          identifier.
        config (ConfigParser): global sensor configuration parser.
    """
    def __init__(self, interval, dataqs, livefeed,
                 method="last", logdir=None, logfreq=10,
                 plotting=False, config=None):
        
        self.interval = interval
        #Our first business is to make sure that we have only a list of *unique*
        #data queues to be querying.
        self.dataqs = []
        for dq in dataqs:
            if dq not in self.dataqs:
                self.dataqs.append(dq)
                
        self.livefeed = livefeed
        self.method = method
        self.logdir = logdir
        self.logfreq = logfreq
        self.lastsave = None
        self.csvdata = {}
        self.plotting = plotting
        self.timer = None
        self._timer_calls = 0
        """Number of times that the timer has executed during the application
        run.
        """
        self._cancel = False
        """When true, the main thread is trying to shut us down; don't start the
        timer again once it fires.
        """

        self.config = None
        if config is not None:
            try:
                from configparser import ConfigParser
            except ImportError: # pragma: no cover
                #Renaming of modules to lower case in python 3.
                from ConfigParser import ConfigParser

            if isinstance(config, str):
                self.config = ConfigParser()
                self.config.readfp(open(config))
            else: # pragma: no cover
                self.config = config

        self._config_sections = {}
        """dict: keys are sensor ids; values are section names in the config
        file.
        """
        self._invert_config()

    def sensor_option(self, sensor, option, default=None):
        """Returns the specified sensor option if available.

        Args:
        sensor (str): name of the sensor to return `option` for.
        option (str): option name.
        """
        if sensor in self._config_sections:
            section = self._config_sections[sensor]
            if self.config.has_option(section, option):
                return self.config.get(section, option)
            else: # pragma: no cover
                return default
        else: # pragma: no cover
            return default
        
    def _invert_config(self):
        """Extracts the sensor keys and the sections they map to from the
        configuration file.
        """
        if self.config is None:
            return

        from fnmatch import fnmatch
        for section in self.config.sections():
            if fnmatch(section, "sensor.*"):
                key = None
                if self.config.has_option(section, "key"):
                    key = self.config.get(section, "key")
                if key is not None:
                    self._config_sections[key] = section
                
    def ready(self, delay=None):
        """Returns True once we have accumulated a few timer calls of data. This
        ensures that we know how many sensors are running on the same COM port.

        Args:
            delay (float): fraction of a second to wait before checking if the
              data is there.
        """
        if delay is not None:
            from time import sleep
            sleep(delay)
            
        havepts = False
        if len(self.csvdata) > 0:
            datapoints = sum([len(v) for v in self.csvdata.values()])/len(self.csvdata)
            havepts = datapoints > 2

        return self._timer_calls > 5 and (self.logdir is None or havepts)
        
    def start(self):
        """Starts a new timer for the configured interval to gather data from
        the serial stream.
        """
        if not self._cancel:
            from threading import Timer
            self.timer = Timer(self.interval, self._read_serial)
            self.timer.start()

    def stop(self):
        """Stops the automatic collection and logging of data. Cleans up threads.
        """
        self._cancel = True
        if self.timer is not None:
            self.timer.cancel()
        #Write whatever data is left over to CSV file.
        self._csv_append()
        
    def _read_serial(self):
        """Reads the latest buffered serial information and places it onto the live
        feed for the application.
        """
        self._timer_calls += 1
        from liveserial.monitor import get_all_from_queue
        sensedata = {}
        havedata = False
        #Just iterate over the various queues we have and process their data.
        for dataq in self.dataqs:
            for qdata in get_all_from_queue(dataq):
                sensor = qdata[0]              
                if sensor not in sensedata:
                    sensedata[sensor] = []
                sensedata[sensor].append(qdata[1:])
                havedata = True

        # We average/discard the data in the queue to produce the single entry that
        # will be posted to the livefeed.
        if havedata:
            for sensor, qdata in sensedata.items():
                data = None
                if self.method == "average":
                    #We use the last data point's time stamp as the authoritative
                    #one for the averaged set.
                    tstamp = qdata[-1][0]
                    #For the values, we take a simple mean.
                    from numpy import mean
                    ldata = mean(qdata, axis=0)
                    data = (tstamp, ldata[1])
                elif self.method == "last":
                    data = qdata[-1][0:2]
                    ldata = qdata[-1]
                if data is not None:
                    self.livefeed.add_data(sensor, data)
                if self.logdir is not None:
                    if sensor not in self.csvdata:
                        self.csvdata[sensor] = []
                    self.csvdata[sensor].append(ldata)
                elif not self.plotting: # pragma: no cover
                    print("{0}: {1: <20f}  {2: <20f}".format(sensor, *data))

            #Before we restart the timer again, see if we need to save the data to
            #CSV.
            self.save()
        self.start()

    def _csv_append(self):
        """Appends the new data points to the relevant CSV files for each of the
        sensor's whose data is being tracked.
        """
        from os import path
        import csv
        for sensor in self.csvdata:
            if self.logdir is None: # pragma: no cover
                #This should never fire because of checks further up the chain.
                #it is here as as sanity check to keep the file system clean.
                continue

            #Check if we have configuration settings available for this sensor.
            columns = None
            if self.config is not None and sensor in self._config_sections:
                logids = self.sensor_option(sensor, "logging")
                if logids is not None:
                    logids = list(map(int, logids.split(',')))
                #We have one issue with the column labeling. We have switched
                #the important value to be in position 1, whereas it could be
                #anywhere in the list. Fix the order of the columns.
                cols = self.sensor_option(sensor, "columns")
                if cols is not None:
                    cols = cols.split(',')
                if logids is None and cols is not None: # pragma: no cover
                    #It is possible that the user will specify one or the other,
                    #but I want to limit the number of concurrent streams for
                    #the unit tests (especially for multi-port testing).
                    logids = list(range(len(cols)))
                                  
                vindex = self.sensor_option(sensor, "value_index")
                if vindex is not None:
                    vindex = int(vindex)
                #The other issue is that if the user limits the columns being
                #logged to include only a few columns, they will supply only a
                #few column labels.
                if (logids is not None and cols is not None and
                    len(logids) == len(cols)):
                    columns = {l: c for l, c in zip(logids, cols)}
                elif cols is not None: # pragma: no cover
                    msg.warn("A different number of column headings than "
                             "logging ids was specified in configuration.")
                else:
                    columns = None
                name = self._config_sections[sensor].split('.')[-1]
            else:
                logids = None
                vindex = 0
                name = sensor
            
            #Let's figure out how many columns to post in the header.
            if len(self.csvdata[sensor]) > 0:
                #We subtract 1 because the time is handled separately.
                N = len(self.csvdata[sensor][0])-1
            else: # pragma: no cover
                #No sense in writing to the file at this time; we have no
                #data to write!
                continue
            
            if logids is None:
                logids = list(range(N))

            logpath = path.join(self.logdir, "{}.csv".format(name))
            if not path.isfile(logpath):
                with open(logpath, 'w') as f:
                    if columns is None:
                        columns = {li: "Value {}".format(i+1)
                                   for i, li in enumerate(logids)}
                    #Now, write the columns in the order specified in the
                    #logindex. However, we must remember that until now, we have
                    #kept the value in position 1, so we have to unmix that.
                    strcols = [columns[li] for li in logids]
                    f.write("{}\n".format(','.join(["Time"] + strcols)))

            with open(logpath, 'a') as f:
                #We log the full data stream from the sensor unless the logging is
                #limited by the configuration file.
                from numpy import array
                writer = csv.writer(f)
                #Generate a new vector of logids with the indices set back to
                #what they were before. Index 0 is the time id, so it should be
                #included always.
                unmix = [0]
                for li in logids:
                    if li == vindex:
                        unmix.append(1)
                        continue
                    unmix.append(li+1)
                    
                for idata in self.csvdata[sensor]:
                    writer.writerow([idata[li] for li in unmix])
                #Since we appended the most recent data points, just reset the
                #lists of points to be empty again.
                self.csvdata[sensor] = []        
        
    def save(self):
        """Saves the logger's buffered points to a CSV file. If the file exists,
        then the data points are appended.
        """
        #We need to see if enough time has passed since the last
        from datetime import datetime
        from time import time
        if self.lastsave is not None:
            elapsed = (datetime.fromtimestamp(time()) -
                       datetime.fromtimestamp(self.lastsave)).total_seconds()
        else:
            elapsed = self.logfreq + 1

        if elapsed > self.logfreq:
            self._csv_append()
            self.lastsave = time()
