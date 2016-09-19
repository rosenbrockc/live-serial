# `live-serial` Revision History

## Revision 0.1.4

- Fixes issues #19 and #20.

## Revision 0.1.3

- Added support for aggregate sensor types that combine data from other sensors
  to create new data streams. See Issue #5.

## Revision 0.1.2

Added several enhancements and bug fixes as described in:
- Issues #3 and #4
- Issue #6 through #12

## Revision 0.1.1

- Added support for unit testing on Windows.
- Debugged the logging and plotting for Windows.
- Added example configuration files for Windows.

## Revision 0.1.0

- Added support for multiple ports, with multiple sensors on each port.
- Added configuration file support: sensors and ports can have their parameters, labels and CSV output format specified in a configuration `.ini`-formatted file.
- Full unit-testing support and coverage for the multi-port case.

## Revision 0.0.2

- Added the classes for monitoring the serial port in a separate thread,
  querying the serial port buffer using a timer (also threaded) and then
  plotting the data using the animation functionality in `matplotlib`.
- Added the script arguments to tune the functionality of the serial, logging
  and plotting modules.
- Added a virtual serial port simulator (based on `socat`) to simulate multiple
  sensors returning data simultaneously.
- Finished debugging the plots and logging.