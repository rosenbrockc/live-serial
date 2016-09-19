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

    Attributes:
        lines (dict): of :class:`matplotlib.lines.Line2D` being animated with
          the serial data; keyed by the sensor identifiers.
        axes (dict): of :class:`matplotlib.axes.Axes` being animated with the
          serial data; keyed by the sensor identifiers.
        ts (dict): of lists of the last `maxlen` sensor timestamp readings.
        ys (dict): of lists of the last `maxlen` sensor value readings. Keys for
          this dict are sensor names if only one value is specified in the
          sensor's `value_index` config option; otherwise, the keys are `(sensor,
          vindex)` tuple, where `vindex` is the zero-based, integer column index
          being plotted.

    """
    def __init__(self, livefeed, interval, maxlen=100, window=20,
                 testmode=False, logger=None):
        self.livefeed = livefeed
        self.interval = interval
        self.maxlen = maxlen
        self.window = window
        self.testmode = testmode
        self.logger = logger
        self.lines = {}
        self.axes = {}
        self.ts = {}
        self.ys = {}
        self._vindices = {}
        """Keys are sensor names; values are lists of value_index options from
        the configuration of each sensor.
        """
        self._plotorder = []
        """Sensor keys, ordered alphabetically; this is the order in which the
        subplots show up in the figure.
        """
        self._timer = None
        """Timer for unit testing the plotting code data acquisition.
        """
        
        #Find out how many subplots we will need; sort their keys for plotting.
        self._plotorder = sorted(self.livefeed.cur_data.keys(),
                                 key=lambda k: str(k))
        self._vindices = {s: self.logger.sensor_option(s, "value_index", [1])
                          for s in self._plotorder}

        if len(self._plotorder) == 0: # pragma: no cover
            raise ValueError("Live feed has no sensor data keys. "
                             "Can't setup plotting. Try fiddling with the "
                             "`-wait` parameter.")

        #For the plot styling, we use the config files. Logger has access to the
        #config file setting, so we just use that.
        from liveserial.config import plot
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D

        #We are going to use a common time axis
        figopts = plot(self.logger.config, "figure")
        axesopts = plot(self.logger.config, "axes")
        if "figsize" not in figopts:
            figopts["figsize"] = (12, 3*len(self.livefeed.cur_data))
        else:
            figopts["figsize"] = tuple(map(float,figopts["figsize"].split(',')))
            
        fig, axes = plt.subplots(len(self.livefeed.cur_data), 1, sharex=True,
                                 squeeze=False, subplot_kw=axesopts, **figopts)

        from itertools import cycle
        from collections import deque
        totlines = sum([len(v) for v in self._vindices.values()])
        cspace = cycle(colorspace(totlines)[0])

        lineopts = plot(self.logger.config, "line")
        labelopts = plot(self.logger.config, "label")
        from six import string_types
        for isense, sensor in enumerate(self._plotorder):
            axes[isense,0].set_xlabel('t', **labelopts)
            if isinstance(sensor, string_types):
                label = self.logger.sensor_option(sensor, "label", sensor)
                port = self.logger.sensor_option(sensor, "port")
                if port is not None:
                    if port == "aggregate":
                        ylabel = "{} (agg.)".format(label)
                    else:
                        ylabel = "{} ({})".format(label, port)
                else: # pragma: no cover
                    ylabel = label
                axes[isense,0].set_ylabel(ylabel, **labelopts)
            else:
                axes[isense,0].set_ylabel("Auto {}".format(isense + 1),
                                          **labelopts) 

            legends = None
            if len(self._vindices[sensor]) > 1:
                legends = self.logger.sensor_option(sensor, "legends")

            for vi, vindex in enumerate(self._vindices[sensor]):
                if legends is not None:
                    legend = legends[vi]
                else:
                    legend = None
                    
                line = Line2D([], [], color=next(cspace), linewidth=2,
                              label=legend, **lineopts)
                axes[isense,0].add_line(line)
                axes[isense,0].set_xlim((0, window + 2.5))
                self.lines[(sensor, vindex)] = line
                self.ys[(sensor, vindex)] = deque(maxlen=self.maxlen)
                
            self.ts[sensor] = deque(maxlen=self.maxlen)
            self.axes[sensor] = axes[isense, 0]
            if legends is not None:
                self.axes[sensor].legend()

        tickopts = plot(self.logger.config, "ticks")
        if len(tickopts) > 0:
            plt.tick_params(**tickopts)
                
        from os import name
        if not self.testmode: # pragma: no cover
            if name != "nt":
                #Mac doesn't support blitting yet with its backends, so we have to
                #do the costly redraw at every iteration.
                animation.TimedAnimation.__init__(self, fig, blit=False)
            else:
                #If blitting is enabled, the plot labels don't update with
                #auto-scaling. Since our machines are fast enough, we make it
                #true by default. The user can override it using an option in
                #the config file if they need the extra speed.
                animopts = plot(self.logger.config, "animation")
                if "blit" not in animopts:
                    blit = False
                else:
                    blit = animopts["blit"] == "1"
                    
                animation.TimedAnimation.__init__(self, fig, blit=blit)
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
            ldata = self.livefeed.read_data(sensor)
            if len(ldata) < 2: # pragma: no cover
                #We don't have anything reasonable to plot; exit gracefully.
                continue
            
            t = ldata[0]
            self.ts[sensor].append(t)
            
            for vindex in self._vindices[sensor]:
                self.ys[(sensor, vindex)].append(ldata[vindex])
                ts, ys = self.ts[sensor], self.ys[(sensor, vindex)]
                self.lines[(sensor, vindex)].set_data(ts, ys)
            if t > self.window: # pragma: no cover
                # We don't want the tests to run long enough for this window to
                # kick in (at least for the moment).
                self.axes[sensor].set_xlim((self.ts[sensor][0], t + 2.5))

            self.axes[sensor].relim() # reset intern limits of the current axes 
            self.axes[sensor].autoscale_view()   # reset axes limits 
            
        self._drawn_artists = self.lines.values()
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
