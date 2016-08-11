"""Methods for plotting the real-time data feed.
"""
from matplotlib import cm
def colorspace(size, cmap=cm.rainbow):
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
        plotargs (dict): arguments that get passed through directly to the
          `matplotlib` plotting function.

    Attributes:
        lines (dict): of :class:`matplotlib.axes.Axes` being animated with the
          serial data; keyed by the sensor identifiers.
        ts (dict): of lists of the last `maxlen` sensor timestamp readings.
        ys (dict): of lists of the last `maxlen` sensor value readings.
    """
    def __init__(self, livefeed, interval, maxlen=250, **plotargs):
        self.livefeed = livefeed
        self.interval = interval
        self.maxlen = maxlen
        self.plotargs = plotargs
        self.lines = {}
        self.ts = {}
        self.ys = {}
        self._plotorder = []
        """Sensor keys, ordered alphabetically; this is the order in which the
        subplots show up in the figure.
        """
        
    def animate(self):
        """Starts an animation by getting data from the specified function.

        Args:
        datafun (function): will be called every 'interval' milliseconds to get new
          data points to plot.
        interval (int): number of milliseconds between fetching of data and drawing
          on the canvas.
        """
        #Find out how many subplots we will need; sort their keys for plotting.
        self._plotorder = sorted(self.livefeed.cur_data.keys())
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        #We are going to use a common time axis
        fig, axes = plt.subplots(len(self.livefeed.cur_data), 1, sharex=True)
        cspace = colorspace(len(axes))[0]
        from collections import deque
        for isense, sensor in enumerate(self._plotorder):
            axes[isense].set_xlabel('t')
            axes[isense].set_ylabel(sensor)
            line = Line2D([], [], color=cspace[isense])
            axes[isense].add_line(line)
            self.lines[sensor] = line
            self.ts[sensor] = deque(maxlen=self.maxlen)
            self.ys[sensor] = deque(maxlen=self.maxlen)
            
        from os import name
        if name != "nt":
            animation.TimedAnimation.__init__(self, fig, interval=interval,
                                              blit=False)
        else:
            animation.TimedAnimation.__init__(self, fig, interval=interval,
                                              blit=True)
        plt.show()
        
    def _draw_frame(self, iframe):
        """Draws the latest frame for each sensor on the relevant plot.
        """
        for sensor in self._plotorder:
            #First, we get the latest data point from the live feed.
            t, y = self.livefeed.read_data(sensor)
            self.ts[sensor].append(t)
            self.ys[sensor].append(y)
            self.lines[sensor].set_data(self.ts, self.ys)

        self._drawn_artists = [self.lines[s] for s in self._plotorder]
        
    def _init_draw(self):
        """Initializes all the subplot line objects to be empty."""
        for l in self.lines.values:
            l.set_data([], [])
