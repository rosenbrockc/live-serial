"""Module that sets up a virtual serial port for unit testing.
"""
from liveserial import msg
def examples():
    """Prints examples of using the script to the console using colored output.
    """
    script = "LIVE-SERIAL Virtual Serial Port Writer"
    explain = ("For testing the plotting and logging locally, it is useful to "
               "have virtual serial ports started on the local machine so "
               "that code can be tested without the real devices. This "
               "script creates threads that write to virtual ports.")
    contents = [(("Write 2 sensors to '/dev/tty.lscom-w' with formats `int`,"
                  "`float` and `int`,`int."), 
                 ("simport.py lscom-w -sensors K W -dtype K int float "
                  "W int int"),
                 ("Use '-seed' to change the random seed for the generated "
                  "values. ")),
                (("Write 2 sensor values to '/dev/tty.lscom-w' and "
                  "'/dev/tty.lscom-mw' simultaneously. Use default `int',"
                  "`float` data types for all but sensor `P`."),
                 ("simport.py lscom-w lscom-mw -sensors lscom-w K W "
                  "lscom-mw P S -dtype P float float"),
                 ("`None` can be used as a sensor name, in which case "
                  "a sensor without a key will be written to the stream."))]
    required = ("REQUIRED: virtual serial ports with the given names.")
    output = ("")
    details = ("For unix-based OS, the name is automatically changed to "
               "'/dev/tty.{}', where '{}' is the given name.")
    outputfmt = ("")

    msg.example(script, explain, contents, required, output, outputfmt, details)
    
def _parser_options():
    """Parses the options and arguments from the command line."""
    import argparse
    from liveserial import base
    parser = argparse.ArgumentParser(parents=[base.bparser],
                                     description="Real-time serial port plotter/logger.")
    parser.add_argument("ports", nargs="+",
                        help="Name of the port(s) to write random data to.")
    parser.add_argument("-sensors", nargs="+",
                        help=("Specify the port names and sensor names to "
                              "generate random data for. Format: "
                              "`-sensor portname sensor_0 sensor_1 None`"))
    parser.add_argument("-dtype", nargs="+",
                        help=("Specify data types to write for each sensor "
                              "type. Format: `-dtype sensor_0 int float`."))
    parser.add_argument("-seed", type=int, default=42,
                        help="Set the random seed for the generated data.")
    parser.add_argument("-runtime", type=float,
                        help=("Specify a maximum runtime before automatically "
                              "terminating the writer threads."))
    args = base.exhandler(examples, parser)
    if args is None:
        return

    #Verify that all the ports exist on the machine.
    from liveserial.monitor import enumerate_serial_ports
    from os import name
    allports = enumerate_serial_ports()
    failure = False
    for port in args["ports"]:
        if name != "nt":
            portname = "/dev/tty.{}".format(port)
        else: # pragma: no cover
            #We only have unit testing configured for unix-based systems at the
            #moment, so this check will never fire.
            portname = port
            
        if portname not in allports:
            msg.err("port {} does not exist locally.".format(port))
            failure = True
            
    if failure:
        return None
    
    sensors = {k: [] for k in args["ports"]}
    allsensors = []
    if args["sensors"]:
        current = args["ports"][0]
        for sensor in args["sensors"]:
            if sensor == "None":
                sensor = None
            allsensors.append(sensor)
            if sensor in args["ports"]:
                current = sensor
            else:
                sensors[current].append(sensor)
    args["sensors"] = sensors

    dtypes = {s: [] for s in allsensors}
    if args["dtype"]:
        current = None
        for dtype in args["dtype"]:
            if dtype == "None":
                dtype = None
            if dtype in allsensors:
                current = dtype
            else:
                dtypes[current].append(eval(dtype))
        for s in allsensors:
            if len(dtypes[s]) == 0:
                dtypes[s] = [int, float]
    args["dtype"] = dtypes
                
    return args

def _setup_simulator(args, port):
    """Sets up a simulator for the specified port.
    """
    from liveserial.simulator import ComSimulatorThread
    sensors = args["sensors"][port]
    dtypes = []
    for s in sensors:
        dtypes.append(tuple(args["dtype"][s]))

    simsig = ComSimulatorThread(port, sensors, dtypes, args["seed"])
    return simsig

def run(args, runtime=None):
    """Starts simulating the serial data in a separate thread.

    Args:
        runtime (float): how many seconds to run for before terminating.
    """
    if args is None: # pragma: no cover
        return

    simsigs = []
    for port in args["ports"]:
        simsigs.append(_setup_simulator(args, port))

    import signal
    def exit_handler(signal, frame): # pragma: no cover
        """Cleans up the serial communication, plotting and logging.
        """
        for simsig in simsigs:
            simsig.join(1)
        print("")
        exit(0)        
    signal.signal(signal.SIGINT, exit_handler)

    for simsig in simsigs:
        simsig.start()

    runtotal = 0.
    while all([sim.is_alive() for sim in simsigs]):
        #Here is the tricky bit; we want to join the threads for a second to
        #keep the main thread busy while everything is going on. More than a
        #second causes delay when the user sends SIGINT to stop the whole
        #process. We instead join on every thread for fractions of a second.
        for simsig in simsigs:
            simsig.join(1./len(simsigs), terminate=False)
        runtotal += 1.
        if runtime is not None and runtotal >= runtime:
            for simsig in simsigs:
                simsig.join(1)            

if __name__ == '__main__': # pragma: no cover
    #We skip the unit tests for this section because it is short and clear
    #and just calls methods that are being tested elsewhere.
    args = _parser_options()
    run(args, args["runtime"])
