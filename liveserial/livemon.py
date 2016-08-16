#!/usr/bin/python
from liveserial import msg
def examples():
    """Prints examples of using the script to the console using colored output.
    """
    script = "LIVE-SERIAL Real-time Serial Port Plotter/Logger"
    explain = ("For any device connected to a serial port (including USB), "
               "it is useful to see and log the data from the port in "
               "real-time (for example in response to human-interaction. "
               "This script sets up live monitoring of a serial port on a "
               "separate thread and plots the data as it is received. Logging "
               "can also be enabled in real-time.")
    contents = [(("Start plotting the data from the COM3 serial port."), 
                 "livemon.py COM3",
                 "If '-logdir' is not specified, *no* data will be logged."),
                (("Plot *and* log the data from /dev/tty."),
                 "livemon.py /dev/tty -logdir ~/sensordata", ""),
                ("Log the data, but don't generate a live plot.",
                 "livemon.py COM3 -noplot -logdir C:\\sensordata\\", ""),
                ("List the available serial ports on the system.",
                 "livemon.py list", "")]
    required = ("REQUIRED: working serial port.")
    output = ("RETURNS: plot window; for logging-only mode, the data being "
              "logged is also periodically printed to stdout.")
    details = ("The plotting uses `matplotlib` with the default configured "
               "backend. If you want a different backend, set the rc config "
               "for `matplotlib` using online documentation.")
    outputfmt = ("")

    msg.example(script, explain, contents, required, output, outputfmt, details)

def _list_serial(port=None):
    """Lists all of the available serial ports on the local machine. If `port`
    is specified, then returns True if port is in the list.

    Args:
    port (str): name of a port to check existence for.

    Returns:
    bool: specifying whether the given port is in the list, or
    list: of available ports on this machine.
    """
    from liveserial.monitor import enumerate_serial_ports
    available = enumerate_serial_ports()
    if port is not None:
        return port in available
    else:
        return available
    
def _parser_options():
    """Parses the options and arguments from the command line."""
    import argparse
    from liveserial import base
    parser = argparse.ArgumentParser(parents=[base.bparser],
                                     description="Real-time serial port plotter/logger.")
    parser.add_argument("port",
                        help="Name of the port to plot/log.")
    parser.add_argument("-noplot", action="store_true",
                        help=("Don't plot the data; only log it."))
    parser.add_argument("-logdir",
                        help=("Path to the directory where sensor data will "
                              "be logged."))
    parser.add_argument("-baudrate", type=int, default=9600,
                        help=("Rate at which information is transferred in a "
                              "communication channel (in bits/second)."))
    parser.add_argument("-stopbits", type=float, default=1., choices=[1, 1.5, 2],
                        help="Serial communication parameter.")
    parser.add_argument("-parity", type=str, default='N',
                        choices=['N', 'E', 'O', 'M', 'S'],
                        help="Serial communication parameter.")
    parser.add_argument("-timeout", type=float, default=0.01,
                        help=("The timeout used for reading the COM port. If "
                              "this value is low, the thread will return data "
                              "in finer grained chunks, with more accurate "
                              "timestamps, but it will also consume more CPU."))
    parser.add_argument("-refresh", type=int, default=100,
                        help=("How often (in milliseconds) to plot new data "
                              "obtained from the serial port."))
    parser.add_argument("-buffertime", type=float, default=25,
                        help=("How often (in milliseconds) to query buffered data "
                              "obtained from the serial port."))
    parser.add_argument("-logfreq", type=float, default=10,
                        help=("How often (in *seconds*) to save the buffered "
                              "data points to CSV."))
    parser.add_argument("-method", default="average", choices=["last", "average"],
                        help=("Specifies how buffered data is aggregated each "
                              "time it is read from the serial port."))
    parser.add_argument("-listen", action="store_true",
                        help=("Prints the raw output from the serial port "
                              "instead of plotting and logging it. Useful "
                              "for debugging port connection issues."))
    parser.add_argument("-virtual", action="store_true",
                        help=("Specifies that the port being connected to is "
                              "virtual (e.g., with `socat`), which changes the "
                              "parameters for connection."))
    parser.add_argument("-sensors", nargs="+", default="all",
                        help="Filter the list of sensors being logged/plotted.")
    parser.add_argument("-maxpts", type=int, default=100,
                        help=("Maximum number of values to keep in the plot "
                              "for each sensor"))
    parser.add_argument("-window", type=float, default=20.,
                        help="Width of window in time units.")
    args = base.exhandler(examples, parser)
    if args is None:
        return

    if args["port"] == "list":
        msg.okay("Available Serial Ports")
        for port in _list_serial():
            msg.info("  {}".format(port))
        return None
    else:
        if not _list_serial(args["port"]):
            msg.err("Port '{}' is not valid.".format(args["port"]))
            return None

    #Convert the units for the buffer and refresh times.
    args["refresh"] /= 1000.
    args["buffertime"] /= 1000.
    
    if args["noplot"] and not args["logdir"]: # pragma: no cover
        msg.warn("Data will only be logged if `-logdir` is specified.", -1)

    return args

def _get_com(args):
    """Gets a configured COM port for serial communication.
    """
    from liveserial.monitor import ComMonitorThread
    from multiprocessing import Queue
    msg.info("Starting monitoring of port '{}'.".format(args["port"]), 2)
    dataq, errorq = Queue(), Queue()
    com = ComMonitorThread(dataq, errorq, args["port"], args["baudrate"],
                           args["stopbits"], args["parity"], args["timeout"],
                           args["listen"], args["virtual"])
    return com

def _com_start(com):
    """Starts the serial port communication thread using the specified object.
    """
    from liveserial.monitor import get_item_from_queue
    com.start()
    msg.okay("COM monitoring thread started.", 2)

    #Even though the thread is going, it doesn't mean that everything is working
    #the way we hope. Check the first item. We have to sleep to give it time to
    #initialize.
    com.join(0.05, terminate=False)
    com_error = get_item_from_queue(com.error_q)
    if com_error is not None: # pragma: no cover
        #We can't easily simulate failure on the serial port to test this message.
        msg.err("monitor thread error--{}".format(com_error))
        com = None
    
def run(args, runtime=None, testmode=False):
    """Starts monitoring of the serial data in a separate thread. Starts the
    plotting or logging based on command-line args.

    Args:
        runtime (float): how many seconds to run for before terminating.
        vardir (dict): to get access to the COM port, logger, feed and plotter
          objects.
    """
    from liveserial.base import set_testmode
    set_testmode(testmode)    
    #When args is None, it means that examples or help or equivalent wants to
    #cancel the execution of the script.
    if args is None: # pragma: no cover
        return
    
    #Get the serial port for communications; this also tests that we are getting
    #data.
    vardir = {}
    com = _get_com(args)
    if com is None: # pragma: no cover
        return

    #The data feed keeps track of the latest, aggregated data selected from the
    #buffer in the com thread.
    from liveserial.monitor import LiveDataFeed
    feed = LiveDataFeed()
    #Logging queries the com thread buffer to get data, and then aggregates it
    #and puts it on the live data feed. Optionally, the data is also
    #periodically saved to CSV.
    from liveserial.logging import Logger
    logger = Logger(args["buffertime"], com.data_q, com.error_q, feed,
                    args["method"], args["logdir"], args["logfreq"],
                    not (not args["noplot"] and not args["listen"]))
    
    import signal
    def exit_handler(signal, frame): # pragma: no cover
        """Cleans up the serial communication and logging.
        """
        msg.warn("SIGINT >> cleaning up threads.", -1)
        logger.stop()
        com.join()
        print("")
        exit(0)
        #Matplotlib's cleanup code for animations is lousy--it doesn't
        #work. I tried calling the private _stop() in a relevant scope and
        #it still let the application hang.
    signal.signal(signal.SIGINT, exit_handler)

    #Add the local variables to the dictionary. This dict is passed in by unit
    #tests usually, which want to investigate the values in each object.
    if vardir is not None:
        vardir["feed"] = feed
        vardir["com"] = com
        vardir["logger"] = logger
        
    #Now that we actually have a way to quit the infinite loop, we can start the
    #data acquisition process.
    _com_start(com)
    
    #Wait until we have some data before the logger gets put to work with it.
    if not args["listen"]:
        from time import sleep
        while com.data_q.empty(): # pragma: no cover
            #If we don't need this delay, it shouldn't trigger unit test
            #problems.
            sleep(0.05)
        logger.start()
    
    #The plotter looks at the live feed data to plot the latest aggregated
    #points.
    plotter = None
    if not args["noplot"] and not args["listen"]:
        while not logger.ready():
            pass
        from liveserial.plotting import Plotter
        import matplotlib.pyplot as plt
        plotter = Plotter(feed, args["refresh"], args["maxpts"],
                          args["window"], testmode)
        if vardir is not None:
            vardir["plotter"] = plotter
        if not testmode: # pragma: no cover
            plt.show()

    _runtime = 0
    while com.is_alive():
        com.join(1, terminate=False)
        _runtime += 1
        if runtime is not None:
            if _runtime >= runtime:
                logger.stop()
                com.join(1)
                if plotter is not None:
                    plotter.stop()

    return vardir
        
if __name__ == '__main__': # pragma: no cover
    run(_parser_options())
