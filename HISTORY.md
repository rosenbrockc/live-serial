# `live-serial` Revision History

## Revision 0.0.2

- Added the classes for monitoring the serial port in a separate thread,
  querying the serial port buffer using a timer (also threaded) and then
  plotting the data using the animation functionality in `matplotlib`.
- Added the script arguments to tune the functionality of the serial, logging
  and plotting modules.