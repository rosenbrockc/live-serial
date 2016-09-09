"""Tests the script entry for simulating the writing to virtual ports.
"""
def get_sargs(args):
    """Returns the list of arguments parsed from sys.argv.
    """
    import sys
    sys.argv = args
    from liveserial.simport import _parser_options
    return _parser_options()    

def test_examples():
    """Makes sure the script examples work properly.
    """
    argv = ["py.test", "-examples"]
    assert get_sargs(argv) is None

def test_writing(isnt):
    """Tests that the simulator script connects everything together correctly.
    """
    if isnt:
        #Windows blocks the serial ports so that nothing else can write to them.
        #So, we just ignore testing the writes on Windows for now. If the rest
        #of the scripts run correctly, then the hook-ups in the simport.py
        #script should be fine with just the linux tests.
        return
        argv = ["py.test", "COM4", "COM3", "-sensors", "COM4",
                "K", "None", "COM3", "P", "S", "-dtype",
                "S", "float", "int"]
    else:
        argv = ["py.test", "lscom-w", "lscom-mw", "-sensors", "lscom-w",
                "K", "None", "lscom-mw", "P", "S", "-dtype",
                "S", "float", "int", "None", "int", "float"]
    args = get_sargs(argv)

    #We just run this for 3 seconds to make sure all the configuration options
    #from the command-line are parsed correctly. The actual reading from the
    #serial ports is tested in multiple places elsewhere so that we don't need
    #to explicitly test it here.
    from liveserial.simport import run
    run(args, 3)

def test_missing():
    """Tests that the script executes gracefully if the wrong port name is
    specified.
    """
    argv = ["py.test", "lscom-dummy", "-sensors", "lscom-dummy",
            "K", "None", "-dtype", "K", "float", "int"]
    args = get_sargs(argv)

    from liveserial.simport import run
    run(args, 1)
