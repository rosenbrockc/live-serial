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

def _list_serial(ports=None):
    """Lists all of the available serial ports on the local machine. If `port`
    is specified, then returns True if port is in the list.

    Args:
    ports (list): name(s) of ports to check existence for.

    Returns:
    bool: specifying whether the given port is in the list, or
    list: of available ports on this machine.
    """
    from liveserial.monitor import enumerate_serial_ports
    available = enumerate_serial_ports()
    if ports is not None:
        result = True
        for port in ports:
            if port not in available:
                msg.err("Port '{}' is not valid.".format(port))
                result = False
        return result
    else:
        return available
    
def _parser_options():
    """Parses the options and arguments from the command line."""
    import argparse
    from liveserial import base
    parser = argparse.ArgumentParser(parents=[base.bparser],
                                     description="Real-time serial port plotter/logger.")
    parser.add_argument("port", nargs="+",
                        help="Name of the port(s) to plot/log.")
    parser.add_argument("-noplot", action="store_true",
                        help=("Don't plot the data; only log it."))
    parser.add_argument("-auto", action="store_true",
                        help=("Runs in automatic mode by loading a "
                              "configuration file in the current directory "
                              "called 'sensors.cfg'."))
    parser.add_argument("-config",
                        help=("Specify a configuration file to get sensor "
                              "setup information from."))
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

    if args["port"] == ["list"]:
        msg.okay("Available Serial Ports")
        for port in _list_serial():
            msg.info("  {}".format(port))
        return None
    else:
        if not _list_serial(args["port"]):
            return None

    #Convert the units for the buffer and refresh times.
    args["refresh"] /= 1000.
    args["buffertime"] /= 1000.
    
    if args["noplot"] and not args["logdir"]: # pragma: no cover
        msg.warn("Data will only be logged if `-logdir` is specified.", -1)

    #Handle the automatic configuration file setup.
    if args["auto"]:
        from os import path
        args["config"] = path.abspath("sensors.cfg")
        
    return args

def _get_com(args):
    """Gets a list of configured COM ports for serial communication.
    """
    from liveserial.monitor import ComMonitorThread as CMT
    from multiprocessing import Queue
    dataq, errorq = Queue(), Queue()
    result = []
    msg.info("Starting setup of ports {}.".format(args["port"]), 2)
    if args["config"]:
        for port in args["port"]:
            com = CMT.from_config(args["config"], port, dataq, errorq,
                                  args["listen"], args["sensors"])
            result.append(com)                                            
    else:
        for port in args["port"]:
            com = CMT(dataq, errorq, port, args["baudrate"],
                      args["stopbits"], args["parity"], args["timeout"],
                      args["listen"], args["virtual"])
            result.append(com)
    return result

def _com_start(coms):
    """Starts the serial port communication thread using the specified object.

    Args:
        coms (list): of :class:`monitor.ComMonitorThread` instances to start
          running.
    """
    from liveserial.monitor import get_item_from_queue
    for i, com in enumerate(coms):
        com.start()
        msg.okay("COM monitoring thread {} started.".format(i), 2)

        #Even though the thread is going, it doesn't mean that everything is working
        #the way we hope. Check the first item. We have to sleep to give it time to
        #initialize.
        com.join(0.05, terminate=False)
        com_error = get_item_from_queue(com.error_q)
        if com_error is not None: # pragma: no cover
            #We can't easily simulate failure on the serial port to test this message.
            msg.err("monitor thread error--{}".format(com_error))
            coms[i] = None
    
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
    if args is None:
        return
    
    #Get the serial port for communications; this also tests that we are getting
    #data.
    vardir = {}
    coms = _get_com(args)

    #The data feed keeps track of the latest, aggregated data selected from the
    #buffer in the com thread.
    from liveserial.monitor import LiveDataFeed
    feed = LiveDataFeed()
    
    #Logging queries the com thread buffer to get data, and then aggregates it
    #and puts it on the live data feed. Optionally, the data is also
    #periodically saved to CSV.
    from liveserial.log import Logger
    dataqs = [c.data_q for c in coms]
    #The logger prints values to screen if it isn't running in plotting
    #mode. Plotting mode means that the plot window is present, or that
    #'-listen' was specified.
    plotting = args["listen"] or (not args["noplot"])
    logger = Logger(args["buffertime"], dataqs, feed,
                    args["method"], args["logdir"], args["logfreq"],
                    plotting, args["config"])
    
    import signal
    def exit_handler(signal, frame): # pragma: no cover
        """Cleans up the serial communication and logging.
        """
        msg.warn("SIGINT >> cleaning up threads.", -1)
        logger.stop()
        for com in coms:
            com.join(1)
        if plotter is not None:
            plotter.stop()
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
        vardir["com"] = coms
        vardir["logger"] = logger
        
    #Now that we actually have a way to quit the infinite loop, we can start the
    #data acquisition process.
    plotter = None
    _com_start(coms)
    if any([com is None for com in coms]): # pragma: no cover
        msg.err("One of the COM threads didn't initialize properly.")
        msg.info("COM Threads that were Okay")
        for com in coms:
            if com is not None:
                msg.std(com.port)
        return

    #Wait until we have some data before the logger gets put to work with it.
    if not args["listen"]:
        from time import sleep
        tries = 0
        while (not all([not com.data_q.empty() for com in coms])
               and tries < 10): # pragma: no cover
            #If we don't need this delay, it shouldn't trigger unit test
            #problems.
            sleep(0.05)
            tries += 1
        logger.start()

    #The plotter looks at the live feed data to plot the latest aggregated
    #points.
    if not args["noplot"] and not args["listen"]:
        tries = 0
        while not logger.ready(0.05) and tries < 10:
            tries += 1

        from liveserial.plotting import Plotter
        import matplotlib.pyplot as plt
        plotter = Plotter(feed, args["refresh"], args["maxpts"],
                          args["window"], testmode, logger)
        if vardir is not None:
            vardir["plotter"] = plotter
        if not testmode: # pragma: no cover
            plt.show()

    _runtime = 0
    while all([com.is_alive() for com in coms]):
        #Here is the tricky bit; we want to join the threads for a second to
        #keep the main thread busy while everything is going on. More than a
        #second causes delay when the user sends SIGINT to stop the whole
        #process. We instead join on every thread for fractions of a second.
        for com in coms:
            com.join(1./len(coms), terminate=False)
        _runtime += 1.
        if runtime is not None:
            if _runtime >= runtime:
                logger.stop()
                for com in coms:
                    com.join(1)
                if plotter is not None:
                    plotter.stop()

    return vardir
        
if __name__ == '__main__': # pragma: no cover
    run(_parser_options())
