"""Provides a session-scoped, auto-use fixture for all the unit tests.
"""
import pytest

@pytest.fixture(scope="session")
def isnt(request):
    """Returns a value indicating if the OS is Windows or not.
    """
    from os import name
    return name == "nt"

@pytest.fixture(scope="session", autouse=True)
def simulated_serial(request):
    """Starts the simulated serial port for the unit tests. Assumes that `socat`
    has been initialized already to setup the virtual COM ports.
    """
    from liveserial.simulator import ComSimulatorThread
    simulator = ComSimulatorThread("lscom-w")
    simulator.start()
    def cleanup_simulator():
        simulator.join(1)
    request.addfinalizer(cleanup_simulator)
