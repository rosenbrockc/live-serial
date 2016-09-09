"""Tests simultaneous, multiple port access with multiple sensors on each port.
"""
import pytest
from test_livemon import get_sargs
from liveserial.config import reset_config

@pytest.fixture(scope="module", autouse=True)
def simulated_multi(request):
    """Starts the simulated serial port for the unit tests. Assumes that `socat`
    has been initialized already to setup the virtual COM ports.
    """
    from liveserial.simulator import ComSimulatorThread
    from os import name
    if name == "nt":
        simulator = ComSimulatorThread("COM3", ["P", "S"],
                                        [(int, float), (float, int)])
    else:
        simulator = ComSimulatorThread("lscom-mw", ["P", "S"],
                                    [(int, float), (float, int)])
    simulator.start()
    def cleanup_simulator():
        simulator.join(1)
    request.addfinalizer(cleanup_simulator)

def test_multi_listen(isnt):
    """Tests the explicit monitor setup using the 'multiple.cfg' file in the
    current directory.
    """
    from os import path
    if isnt:
        argv = ["py.test", "COM2", "COM4", "-virtual", "-listen", "-config",
                path.join("tests", "ntmultiple.cfg")]
    else:
        strport = "/dev/tty.{}"
        argv = ["py.test", strport.format("lscom-r"),
                strport.format("lscom-mr"), "-virtual", "-listen", "-config",
                path.join("tests", "multiple.cfg")]
    args = get_sargs(argv)
    from liveserial.livemon import run
    vardir = run(args, 2)
    
    #Make sure that the relevant objects were created and run properly.
    assert "feed" in vardir
    assert "com" in vardir
    assert "logger" in vardir

    assert all(vardir["feed"].has_new_data.values())
    reset_config()

def test_multi_logplot(isnt, tmpdir):
    """Tests the simultaneous logging and plotting from multiple ports with
    multiple sensors per port.
    """
    from os import path
    sub = tmpdir.mkdir("multilog")
    if isnt:
        argv = ["py.test", "COM2", "COM4", "-virtual", "-logdir", str(sub),
                "-config", path.join("tests", "ntmultiple.cfg")]
    else:
        strport = "/dev/tty.{}"
        argv = ["py.test", strport.format("lscom-r"),
                strport.format("lscom-mr"), "-virtual", "-logdir", str(sub),
                "-config", path.join("tests", "multiple.cfg")]
    args = get_sargs(argv)
    
    from liveserial.livemon import run
    vardir = run(args, 5, True)
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

        if sfile.basename == "ppg.csv":
            assert header.strip().split(',')[-1] == "PPG"
            assert len(value.split(',')) == 2

        if sfile.basename == "seat.csv":
            assert header.strip() == "Time,Value 1"
            assert len(value.split(',')) == 2
            
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
    reset_config()
