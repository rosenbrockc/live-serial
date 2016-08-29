"""Methods for plotting the real-time data feed.
"""
from liveserial.base import testmode
from matplotlib import cm
import matplotlib.animation as animation
import matplotlib

#We have to fiddle with the backends for Windows and Unix-based, otherwise we
#get unhandled exceptions or program-stopped working problems.
import os
if os.name != "nt":
    matplotlib.use("Agg" if testmode else "TkAgg")

from liveserial import msg
import numpy as np
from threading import Timer

def colorspace(size, cmap=cm.winter):
    """Returns an cycler over a linear color space with 'size' entries.
    
    :arg int size: the number of colors to define in the space.
    :returns: iterable cycler with 'size' colors.
    :rtype: itertools.cycle
    """
    from itertools import cycle
    import numpy as np
    rbcolors = cmap(np.linspace(0, 1, size))
    return (rbcolors, cycle(rbcolors))

class Plotter(animation.TimedAnimation):
    """Plots the live stream for each of the sensors in a subplot.

    Args:
        livefeed (monitor.LiveDataFeed): data feed with the latest data points to
          plot. Also an attribute on the class instance.
        interval (int): how often (in milliseconds) to redraw the plot with the
          latest plot values.
        maxlen (int): maximum number of time points kept for each subplot.    
        window (float): width of the plot window for sensors.
        testmode (bool): when True, the animator is not initialized so that a
          backend isn't required to run the unit tests.
        logger (log.Logger): logger instance for interacting with config
          parameters.
        plotargs (dict): arguments that get passed through directly to the
          `matplotlib` plotting function.

    Attributes:
        lines (dict): of :class:`matplotlib.lines.Line2D` being animated with
          the serial data; keyed by the sensor identifiers.
        axes (dict): of :class:`matplotlib.axes.Axes` being animated with the
          serial data; keyed by the sensor identifiers.
        ts (dict): of lists of the last `maxlen` sensor timestamp readings.
        ys (dict): of lists of the last `maxlen` sensor value readings.

    """
    def __init__(self, livefeed, interval, maxlen=100, window=20,
                 testmode=False, logger=None, **plotargs):
        self.livefeed = livefeed
        self.interval = interval
        self.maxlen = maxlen
        self.window = window
        self.testmode = testmode
        self.logger = logger
        self.plotargs = plotargs
        self.lines = {}
        self.axes = {}
        self.ts = {}
        self.ys = {}
        self._plotorder = []
        """Sensor keys, ordered alphabetically; this is the order in which the
        subplots show up in the figure.
        """
        self._timer = None
        """Timer for unit testing the plotting code data acquisition.
        """
        
        #Find out how many subplots we will need; sort their keys for plotting.
        self._plotorder = sorted(self.livefeed.cur_data.keys(), key=lambda k: str(k))
        if len(self._plotorder) == 0: # pragma: no cover
            raise ValueError("Live feed has no sensor data keys. "
                             "Can't setup plotting.")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D

        #We are going to use a common time axis
        fig, axes = plt.subplots(len(self.livefeed.cur_data), 1, sharex=True,
                                 squeeze=False,
                                 figsize=(12, 3*len(self.livefeed.cur_data)))
        cspace = colorspace(len(axes))[0]
        from collections import deque
        for isense, sensor in enumerate(self._plotorder):
            axes[isense,0].set_xlabel('t')
            if isinstance(sensor, str):
                label = self.logger.sensor_option(sensor, "label", sensor)
                port = self.logger.sensor_option(sensor, "port")
                if port is not None:
                    ylabel = "{} ({})".format(label, port)
                else: # pragma: no cover
                    ylabel = label
                axes[isense,0].set_ylabel(ylabel)
            else:
                axes[isense,0].set_ylabel("Auto {}".format(isense + 1))

            line = Line2D([], [], color=cspace[isense], linewidth=2)
            axes[isense,0].add_line(line)
            axes[isense,0].set_xlim((0, window + 2.5))
            self.lines[sensor] = line
            self.ts[sensor] = deque(maxlen=self.maxlen)
            self.ys[sensor] = deque(maxlen=self.maxlen)
            self.axes[sensor] = axes[isense, 0]

        from os import name
        if not self.testmode: # pragma: no cover
            if name != "nt":
                #Mac doesn't support blitting yet with its backends, so we have to
                #do the costly redraw at every iteration.
                animation.TimedAnimation.__init__(self, fig, blit=False)
            else:
                animation.TimedAnimation.__init__(self, fig, blit=True)
        else:
            self._init_draw()
            self.new_frame_seq()
            self._timer = Timer(self.interval, self._draw_frame, (0,))
            self._timer.start()
            
        msg.info("Plotting animation configured.", 2)

    def new_frame_seq(self):
        return iter(range(self.maxlen))
        
    def _draw_frame(self, iframe):
        """Draws the latest frame for each sensor on the relevant plot.
        """
        for sensor in self._plotorder:
            #First, we get the latest data point from the live feed.
            t, y = self.livefeed.read_data(sensor)
            self.ts[sensor].append(t)
            self.ys[sensor].append(y)
            self.lines[sensor].set_data(self.ts[sensor], self.ys[sensor])
            if t > self.window: # pragma: no cover
                # We don't want the tests to run long enough for this window to
                # kick in (at least for the moment).
                self.axes[sensor].set_xlim((self.ts[sensor][0], t + 2.5))

            self.axes[sensor].relim() # reset intern limits of the current axes 
            self.axes[sensor].autoscale_view()   # reset axes limits 
            
        self._drawn_artists = [self.lines[s] for s in self._plotorder]
        if self.testmode:
            self._timer = Timer(self.interval, self._draw_frame, (0,))
            self._timer.start()
        
    def _init_draw(self):
        """Initializes all the subplot line objects to be empty."""
        for l in self.lines.values():
            l.set_data([], [])

    def stop(self):
        """Cleans up the timer when the plotter is running in test mode.
        """
        if self._timer:
            self._timer.cancel()
