import numpy as np
import itertools
import collections

__all__ = ['Axis',
           'XPM',
           'XPMParser',
           'load',
           'SSStats'
       ]

class Axis(object):
    def __init__(self, size):
        self.size = size
        self._i = 0
        self.axis = np.zeros(size, dtype='S32')
    def append(self, val):
        self.axis[self._i] = val
        self._i += 1

    def update(self, values):
        i = self._i
        j = i+ len(values)
        self.axis[i:j] = values
        self._i = j

    def index(self, val):
        return self.axis == val

    def __iter__(self):
        return iter(self.axis)

class Axes(object):
    def __init__(self, **kws):
        for name, size in kws.iteritems():
            setattr(self, name, Axis(size))

class XPM(object):
    def __init__(self, cols=0, rows=0, colors=0, char=0):

        self._cols     = cols
        self._rows     = rows
        self._colors   = colors
        self._char     = char
        self._ssmap    = dict()
        self._colormap = dict()
        self._axes     = Axes(x=cols, y=rows)
        self._data     = np.zeros((rows,cols), dtype='S1')

    def axis(self, name):
        return getattr(self._axes, name)

    @property
    def x(self): return self.axis('x')

    @property
    def y(self): return self.axis('y')

    def tick(self, axis, ix): return self.axis(axis).axis[ix]
    def xtick(self, ix): return self.tick('x', ix)
    def ytick(self, ix): return self.tick('y', ix)


    def __iter__(self):
        return iter(xrange(self._cols))

    def __getitem__(self, column):
        return self._data[:,column]

    def ss(self, code):
        return self._colormap[code]

    @property
    def colormap(self): return self._colormap

    @property
    def ssmap(self): return self._ssmap


class XPMParser(object):
    def __init__(self, stream):
        self._stream = stream
        self._xpm = None

    def _parse_colormap_line(self):
        """
        E.g.:
        "~  c #FFFFFF " /* "Coil" */,
        """
        line = self._stream.readline().strip()
        groups = self._clear_comments(line).replace('"','').replace(',','').split()
        key = groups[0]
        assert groups[1] == 'c'
        color = groups[2]
        sstype = groups[3]
        return key, color, sstype

    def _clear_comments(self, line):
        return line.replace('/*', '').replace('*/', '')

    def _try_parse_axis_line(self):
        pos = self._stream.tell()
        line = self._stream.readline().strip()
        if not line.startswith('/* x-axis:') and not line.startswith('/* y-axis:'):
            self._stream.seek(pos)
            return False
        return self._parse_axis_line(line)

    def _parse_axis_line(self, line):
        groups = self._clear_comments(line).split()
        axis = groups[0]
        try:
            ticks = groups[1:]
        except:
            print 'bad', groups
            raise
        if   axis == 'x-axis:': ax = 'x'
        elif axis == 'y-axis:': ax = 'y'
        else: raise ValueError, 'Unexpected XPM axis %s' % axis
        return ax, ticks

    def parse(self):
        # get to the 'static char *gromacs_xpm' portion
        line = self._stream.readline().strip()
        while True:
            line = self._stream.readline().strip()
            if line.startswith('static char *gromacs_xpm'): break
        line = self._stream.readline().strip()

        # number of columns and rows, colormap, and pixel character
        cols, rows, colors, char = map(int, line[1:-2].split())
        self._xpm = XPM(cols=cols, rows=rows, colors=colors, char=char)
        xpm = self._xpm

        # parse the colormap
        for _ in xrange(xpm._colors):
            key, color, ss = self._parse_colormap_line()
            xpm._ssmap[key] = ss
            xpm._colormap[key] = color

        # parse the axes
        while True:
            result = self._try_parse_axis_line()
            if not result: break
            axis, ticks = result
            xpm.axis(axis).update(ticks)

        # parse the data
        for i, line in enumerate(itertools.imap(str.strip, self._stream)):
            # line is formated as: ".....",
            # ..remove the quotes and comma
            values = line.replace('"','').replace(',','')
            ix = rows-i-1
            xpm._data[ix][:] = list(values)

        assert i+1 == rows
        self._stream.close()
        return xpm

def load(path):
    return XPMParser(open(path)).parse()


class SSStats(object):
    def __init__(self):
        self._param = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
        self.ssmap = dict()
        self.colormap = dict()

    def update(self, key, sslist):
        for ss in sslist:
            self._param[key][ss] += 1

    def stats(self):
        stats = dict()
        for k, info in self._param.iteritems():
            stats[k] = dict()
            for ss, count in info.iteritems():
                stats[k][ss] = count
        return stats

    def plot(self, path, only=None, title=None):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec

        _only = set(only) if only is not None else set(self.ssmap.values())
        rmap  = dict([(v,k) for (k,v) in self.ssmap.iteritems()])
        only  = set([rmap.get(name) for name in _only])


        stats   = self.stats()
        xaxis   = np.array(sorted(stats.keys()))
        totals  = np.zeros(len(xaxis))
        ss_perc = collections.defaultdict(lambda: np.zeros(len(xaxis)))
        for i, x in enumerate(xaxis):
            total = sum(stats[x].values())
            totals[i] = total
            for ss, count in stats[x].iteritems():
                if ss in only: name = ss
                else:          name = 'other'
                ss_perc[name][i] += 100 * count / float(total)
        self.colormap['other'] = 'black'
        self.ssmap['other'] = 'other'

        xaxis /= 10.**3 # convert to ns
        gs = gridspec.GridSpec(2, 1, hspace=0, height_ratios=[1,10])

        # frame counts
        plt.subplot(gs[0])
        plt.title(title)
        ax = plt.gca()
        plt.bar(xaxis, totals, 1, color='grey', alpha=.5)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position('right')
        plt.ylabel('#')

        ax.yaxis.set_major_locator(plt.MaxNLocator(2))
        ax.xaxis.set_visible(False)
        # ax.spines['bottom'].set_visible(False)
        # ax.xaxis.set_ticks_position('none')

        # aggregate SS data
        plt.subplot(gs[1])
        for ss in ss_perc.keys():
            color = self.colormap[ss]
            color = color if not color == '#FFFFFF' else 'black'
            style = ':' if color is 'black' else '-'
            plt.plot(xaxis, ss_perc[ss], linestyle=style,
                       color=color, label=self.ssmap[ss], lw=3, alpha=.6)

        plt.ylabel('%')
        plt.xlabel('Time (ns)')
        ax = plt.gca()
        # ax.tick_params('x', labeltop='off')
        # ax.spines['top'].set_visible(False)
        # ax.xaxis.set_ticks_position('none')
        plt.legend(loc='best', fontsize=9, frameon=False, ncol=len(self.ssmap)/2)

        plt.savefig(path, bbox_inches='tight')


if __name__ == '__main__':
    import sys
    paths = sys.argv[1:]

    stats = SSStats()
    for xpm in itertools.imap(load, paths):
        for ix in xpm:
            stats.update(int(xpm.xtick(ix)), xpm[ix])
            stats.colormap.update(xpm.colormap)
            stats.ssmap.update(xpm.ssmap)

    stats.plot('test.svg', only='B-Bridge B-Sheet Bend Turn'.split())
