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

def test_writing():
    """Tests that the simulator script connects everything together correctly.
    """
    argv = ["py.test", "lscom-w", "lscom-mw", "-sensors", "lscom-w",
            "K", "None", "lscom-mw", "P", "S", "-dtype", "S", "float", "int"]
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
