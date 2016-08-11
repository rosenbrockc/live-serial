#!/usr/bin/python
def examples():
    """Prints examples of using the script to the console using colored output.
    """
    from liveserial import msg
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
                 "livemon.py COM3 -noplot", "")] 
    required = ("REQUIRED: working serial port.")
    output = ("RETURNS: plot window; for logging-only mode, the data being "
              "logged is also periodically printed to stdout.")
    details = ("The plotting uses `matplotlib` with the default configured "
               "backend. If you want a different backend, set the rc config "
               "for `matplotlib` using online documentation.")
    outputfmt = ("")

    msg.example(script, explain, contents, required, output, outputfmt, details)

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
    args = base.exhandler(examples, parser)

    if args["noplot"] and not args["logdir"]:
        from liveserial.msg import warn
        warn("Data will only be logged if `-logdir` is specified.")
    return args

def run(args):
    """Starts monitoring of the serial data in a separate thread. Starts the
    plotting or logging based on command-line args.
    """
    from liveserial.msg import info
    info("Starting monitoring of port '{}'.".format(args["port"]), 2)
    
if __name__ == '__main__':
    run(_parser_options())
