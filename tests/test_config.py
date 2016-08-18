"""Methods to test the configuration file setup for the monitor.
"""
import pytest
from test_livemon import get_sargs

def test_auto():
    """Tests the automatic monitor setup using the 'sensors.cfg' file in the
    current directory.
    """
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-listen", "-auto"]
    args = get_sargs(argv)    
    from liveserial.livemon import run
    vardir = run(args, 2)
    #Make sure that the relevant objects were created and run properly.
    assert "feed" in vardir
    assert "com" in vardir
    assert "logger" in vardir

    assert all(vardir["feed"].has_new_data.values())   

def test_quick():
    """Tests the quick initialization of a ComMonitorThread using only the port
    name.
    """
    from liveserial.monitor import ComMonitorThread
    com = ComMonitorThread.from_port("/dev/tty.lscom-r", virtual=True)
    com.start()

    #Wait for a second so that data can accumulate. Then terminate the thread.
    com.join(1, terminate=False)
    assert not(com.data_q.empty())
    com.join(1)
    
def test_explicit():
    """Tests the automatic monitor setup when an explicit path is provided to a
    configuration file.
    """
    from os import path
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-listen",
            "-config", path.join("tests", "exception.cfg")]
    args = get_sargs(argv)
    from liveserial.livemon import run
    with pytest.raises(ValueError):
        vardir = run(args, 2)

def test_logging(tmpdir):
    """Tests logging when the config specifies special column names and
    restricts which columns to use.
    """
    #For this test, we only use the averaging method (which is the default).
    sub = tmpdir.mkdir("configlog")
    argv = ["py.test", "/dev/tty.lscom-r", "-virtual", "-logdir", str(sub),
            "-logfreq", "1.5", "-auto"]
    args = get_sargs(argv)
    
    from liveserial.livemon import run
    vardir = run(args, 4, True)
    assert "logger" in vardir
    assert "com" in vardir
    
    nfiles = 0
    for sfile in sub.listdir():
        #The size of the file is in bytes. The header is at least 11 and
        #each line should be around 30 (depending on encoding). We expect
        #lots of lines from 3 seconds worth of logging.
        assert sfile.stat().size > 120
        nfiles += 1

        with sfile.open() as f:
            header = f.readline()
            value = f.readline()

        if sfile.basename == "weight.csv":
            assert header.strip().split(',')[-1] == "Weight"
            assert len(value.split(',')) == 2

        if sfile.basename == "cardio.csv":
            assert header.strip() == "Time,Value 1,Value 2"
            assert len(value.split(',')) == 3
            
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

