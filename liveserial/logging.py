"""Methods for grabbing data and logging it to CSV files.
"""
class Logger(object):
    """Logs data points from the serial port to CSV. The arguments to this class
    constructor are also available as attributes on the class instance.

    Args:
        interval (int): how often (in milliseconds) to read data from the serial
          buffer.
        dataq (Queue.Queue): stores the data read in from the serial port.
        errorq (Queue.Queue): stores any error raised during serial port
        reading.
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
    Attributes:
        timer (threading.Timer) executes calls to the serial port reader to get the
          latest data and push it to the live feed.    
        lastsave (float): timestamp indicating the last time the CSV file was
          appended to
        csvdata (dict): lists of sensor time and value readings, keyed by sensor
          identifier.
    """
    def __init__(self, interval, dataq, errorq, livefeed,
                 method="last", logdir=None, logfreq=10,
                 plotting=False):
        
        self.interval = interval
        self.dataq = dataq
        self.errorq = errorq
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

    def ready(self):
        """Returns True once we have accumulated a few timer calls of data. This
        ensures that we know how many sensors are running on the same COM port.
        """
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
        """Stops the automatic collection and logging of data.
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
        for sensor, timestamp, qdata in get_all_from_queue(self.dataq):
            if sensor not in sensedata:
                sensedata[sensor] = []
            sensedata[sensor].append((timestamp, qdata))
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
                    data = (tstamp, mean([d[1] for d in qdata]))
                elif self.method == "last":
                    data = qdata[-1]

                if data is not None:
                    self.livefeed.add_data(sensor, data)
                if self.logdir is not None:
                    if sensor not in self.csvdata:
                        self.csvdata[sensor] = []
                    self.csvdata[sensor].append(data)
                elif not self.plotting:
                    print("{0: <20f}  {1: <20f}".format(*data))

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
            logpath = path.join(self.logdir, "{}.csv".format(sensor))
            if not path.isfile(logpath):
                with open(logpath, 'w') as f:
                    f.write("Time,Value\n")

            with open(logpath, 'a') as f:
                writer = csv.writer(f)
                for idata in self.csvdata[sensor]:
                    writer.writerow(idata)
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
