Data Plotting
=============

Because `liveserial` supports simultaneous reading from multiple serial ports,
each also supporting streams of data from multiple sensors, the plotting has to
be flexible enough to support animation for multiple data sets. Plotting uses a
single class that inherits from :class:`~matplotlib.animation.TimedAnimation` and
overrides the methods for frame drawing to get the latest data points from the
:class:`~liveserial.monitor.LiveDataFeed`. Using :class:`~collections.deque`
instances allows a fixed number of data points to be plotted so that the plot
window moves intuitively as the stream continues to come in. Older values are
discarded so that memory doesn't become an issue either.

For unit testing, the base class initializer is ignored in favor of a standard
system timer to test the drawing methods and the data acquisition and
passing. The background is also switched to `Agg` so that no plot window is
generated.

.. automodule:: liveserial.plotting
   :synopsis: Live stream plotting via `matplotlib` animation.
   :members:

