"""Tests the aggregate sensor functionality.
"""
import pytest
from test_livemon import get_sargs
from liveserial.config import reset_config

def test_auto(isnt, tmpdir):
    """Tests the automatic monitor setup for aggregate sensors using the
    'aggregate.cfg' file in the tests directory.

    """
    from os import path
    sub = tmpdir.join("aggregate")
    argv = ["py.test", "auto", "-config", path.join("tests", "aggregate.cfg"),
            "-logdir", str(sub), "-logfreq", "1.5"]
    args = get_sargs(argv)
    from liveserial.livemon import run
    vardir = run(args, 4, True)
    
    #Make sure that the relevant objects were created and run properly.
    assert "feed" in vardir
    assert "com" in vardir
    assert "logger" in vardir
    assert "plotter" in vardir

    assert all(vardir["feed"].has_new_data.values())
    assert "total" in vardir["feed"].cur_data
    assert len(vardir["plotter"].ts) == len(vardir["feed"].cur_data)
    assert ("total", 1) in vardir["plotter"].ys
    assert len(vardir["plotter"].ys[("total", 1)]) > 0
    assert ("total", 2) in vardir["plotter"].ys

    nfiles = 0
    for sfile in sub.listdir():
        assert sfile.stat().size > 120
        nfiles += 1

        with sfile.open() as f:
            header = f.readline()
            value = f.readline()

        if sfile.basename == "weight.csv":
            assert header.strip().split(',')[-1] == "Weight"
            assert len(value.split(',')) == 2

        if sfile.basename == "total.csv":
            assert header.strip() == "Time,isum,fsum"
            assert len(value.split(',')) == 3
    
    reset_config()
