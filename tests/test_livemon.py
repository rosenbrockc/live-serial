"""Tests the script entry to the live monitoring program by calling its run
method with different combinations of script arguments.
"""
import pytest
# The virtual, pseudorandom port is setup as a session fixture in conftest.py
def _get_sargs(args):
    """Returns the list of arguments parsed from sys.argv.
    """
    import sys
    sys.argv = args
    from liveserial.livemon import _parser_options
    return _parser_options()    

def test_examples():
    """Makes sure the script examples work properly.
    """
    argv = ["py.test", "-examples"]
    _get_sargs(argv)
    
def test_list(isnt):
    """Tests the port listing function of the package.
    """
    #We know that the two virtual ports should be in the list.
    from liveserial.livemon import _list_serial
    allports = _list_serial()
    if not isnt:
        assert _list_serial("/dev/tty.lscom-w")
    assert "/dev/tty.lscom-r" in allports

    #Also, make sure that if the port isn't in the list, we exit gracefully.
    argv = ["py.test", "bogus-port"]
    assert _get_sargs(argv) is None
    
    #Finally, just check that the printing functionality of the entry script
    #works as expected. Here we are just betting against unhandled exceptions.
    argv = ["py.test", "list"]
    _get_sargs(argv)

def test_com():
    """Tests that the com thread can read from the virtual serial port.
    """
    from liveserial.livemon import _get_com, _com_start
    from time import sleep
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual"]
    args = _get_sargs(argv)
    #Create and start the com thread.
    com = _get_com(args)
    _com_start(com)

    #Wait for a second so that data can accumulate. Then terminate the thread.
    com.join(1, terminate=False)
    assert not(com.data_q.empty())
    com.join(1)

def _raise_sigint(duration):
    """Raises the standard ^C signal interrupt to test proper termination of the
    threads.

    Args:
    duration (float): how many seconds to wait before raising the signal.
    """
    #If the simulated port was running in script mode, it would also have a
    #signal interrupt handler defined; however, for unit tests we only import
    #it, so we don't have to worry about that.
    def _interrupt():
        raise KeyboardInterrupt("^C")
    from threading import Timer
    timer = Timer(duration, _interrupt)
    timer.start()
    
def test_listen():
    """Tests the logger's listening ability on a com port.
    """
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-listen"]
    args = _get_sargs(argv)    
    from liveserial.livemon import run
    vardir = run(args, 2)
    #Make sure that the relevant objects were created and run properly.
    assert "feed" in vardir
    assert "com" in vardir
    assert "logger" in vardir

    assert all(vardir["feed"].has_new_data.values())

def test_logging(tmpdir):
    """Tests the sensor logging in temporary directory.
    """
    for method in ["last", "average"]:
        sub = tmpdir.mkdir(method)
        argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-logdir", str(sub),
                "-logfreq", "1.5", "-noplot", "-method", method]
        args = _get_sargs(argv)
        
        from liveserial.livemon import run
        vardir = run(args, 4)
        assert "logger" in vardir
        assert "com" in vardir
        
        nfiles = 0
        for sfile in sub.listdir():
            #The size of the file is in bytes. The header is at least 11 and
            #each line should be around 30 (depending on encoding). We expect
            #lots of lines from 3 seconds worth of logging.
            assert sfile.stat().size > 120
            nfiles += 1
            
        #Also make sure that we have a file for every sensor.
        assert nfiles == len(vardir["logger"].csvdata)

def test_plotting():
    """Tests the plotting data functionality. Because backends aren't always
    easily configured for unit tests, the actual calls to matplotlib to plot are
    ignored by the plotter; instead the tests just verify that the data is
    accessible and that it is passed around correctly.
    """
    #We don't need to log for the plotting tests.
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual"]
    args = _get_sargs(argv)

    #The matplotlib import takes a long time, let this run for at least 7
    #seconds so that we can collect data for 2.
    from liveserial.livemon import run
    vardir = run(args, 4, True)

    assert "plotter" in vardir
    assert "feed" in vardir
    assert len(vardir["plotter"].ts) == len(vardir["feed"].cur_data)
    assert len(vardir["plotter"].ys) == len(vardir["feed"].cur_data)
    assert all([len(q) > 0
                for q in vardir["plotter"].ts.values()])
    assert all([len(q) > 0
                for q in vardir["plotter"].ys.values()])    

def test_logplot(tmpdir):
    """Tests the logging and plotting running simultaneously.
    """
    #For this test, we only use the averaging method (which is the default).
    sub = tmpdir.mkdir("combined")
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-logdir", str(sub),
            "-logfreq", "1.5"]
    args = _get_sargs(argv)
    
    from liveserial.livemon import run
    vardir = run(args, 4, True)
    #This is the one place where we make sure getting a single item works.
    from liveserial.monitor import get_item_from_queue
    assert get_item_from_queue(vardir["com"].data_q) is not None
    assert "logger" in vardir
    assert "com" in vardir
    
    nfiles = 0
    for sfile in sub.listdir():
        #The size of the file is in bytes. The header is at least 11 and
        #each line should be around 30 (depending on encoding). We expect
        #lots of lines from 3 seconds worth of logging.
        assert sfile.stat().size > 120
        nfiles += 1
        
    #Also make sure that we have a file for every sensor.
    assert nfiles == len(vardir["logger"].csvdata)
    assert "plotter" in vardir
    assert "feed" in vardir
    assert len(vardir["plotter"].ts) == len(vardir["feed"].cur_data)
    assert len(vardir["plotter"].ys) == len(vardir["feed"].cur_data)
    assert all([len(q) > 0
                for q in vardir["plotter"].ts.values()])
    assert all([len(q) > 0
                for q in vardir["plotter"].ys.values()])    
