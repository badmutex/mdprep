from pxul.logging import logger

from StringIO import StringIO

import os
import collections
import copy
from . import _yaml as yaml

__all__ = [
    'velocity_generation_group',
    'MdpGroup',
    'MDP',
    ]

def velocity_generation_group(temp, seed):
    g                    = MdpGroup('VELOCITY GENERATION')
    g.gen_vel            = 'yes'
    g.gen_temp           = temp
    g.gen_seed           = seed

    return g


class MdpGroup(object):
    def __init__(self, description=None):
        # self.__setattr__ is overridden below which causes infinit recursion.
        # use object.__setattr__ to work around this
        object.__setattr__(self, 'descr', description)
        object.__setattr__(self, '_kv',  collections.OrderedDict())
        object.__setattr__(self, '_line_comments', dict())


    def set(self, key, val):
        self._kv[key] = val

    def get(self, key):
        return self._kv[key]

    def __setitem__(self, k, v):
        self.set(k, v)

    def __getitem__(self, k):
        return self.get(k)

    def add_comment(self, k, comment):
        self._line_comments[k] = comment


    def format(self):
        with StringIO() as s:
            s.write('; ')

            # comment for this group
            if self.descr:
                s.write(self.descr)
            s.write('\n')

            # the key/value pairs
            for k, v in self._kv.iteritems():
                s.write(k + ' = ')

                ### cases: value is list of str, str, arbitrary

                # [str]: stringify
                if type(v) is list:
                    v_str = ' '.join(map(str, v))
                    s.write(v_str)

                # str: write
                elif type(v) is str:
                    s.write(v)

                # obj:
                else:
                    s.write(str(v))

                # add line comments
                if k in self._line_comments:
                    s.write(' ; ' + str(self._line_comments[k]))

                # done
                s.write('\n')

            return s.getvalue()

    def __str__(self):
        return self.format()

    def __getattr__(self, k):
        if k in self._kv:
            return self._kv[k]
        else: raise AttributeError, k

    def __deepcopy__(self, memo):
        """
        Overridding __getattr__ requires us to define our own __deepcopy__ method,
        otherwise you get a KeyError: '__deepcopy__' exception
        """
        o = self.__class__()
        o.__dict__.update(copy.deepcopy(self.__dict__))
        return o

    def __setattr__(self, k, v):
        if k in self.__dict__:
            self.__dict__[k] = v
        else:
            self._kv[k] = v

    def __contains__(self, k):
        return k in self._kv


class MDPError (Exception): pass

class MDP(yaml.YAMLObject):
    yaml_tag = '!MDP'

    @classmethod
    def to_yaml(cls, dumper, obj):
        return dumper.represent_scalar(cls.yaml_tag, str(obj), style='|')

    @classmethod
    def from_yaml(cls, loader, node):
        s = loader.construct_python_str(node)
        return cls.loads(s)

    def __init__(self):
        object.__setattr__(self, '_groups', collections.OrderedDict())

    def _find_group(self, i):
        for k, g in self._groups.iteritems():
            if i == k or i in g:
                return g
        raise KeyError, i

    def copy(self):
        return copy.deepcopy(self)

    def get(self, k):
        g = self._find_group(k)
        if k not in g:
            return g
        else:
            return g[k]

    def __getitem__(self, k):
        return self.get(k)

    def set(self, k, v, group=None):
        if group is None:
            try:
                g = self._find_group(k)
            except KeyError:
                # TODO
                g = self._groups[self._groups.keys()[0]]

        g[k] = v

    def __setitem__(self, k, v):
        self.set(k, v)

    def format(self):
        with StringIO() as s:
            for g in self._groups.itervalues():
                s.write(g.format() + '\n')
            return s.getvalue()

    def __str__(self):
        return self.format()

    def __getattr__(self, k):
        return self.get(k)

    def __deepcopy__(self, memo):
        """
        Overridding __getattr__ requires us to define our own __deepcopy__ method,
        otherwise you get a KeyError: '__deepcopy__' exception
        """
        o = self.__class__()
        o.__dict__.update(copy.deepcopy(self.__dict__))
        return o

    def __setattr__(self, k, v):
        if k in self.__dict__:
            self.__dict__[k] = v
        else:
            self.set(k, v)

    def add(self, g):
        k = '_'.join(filter(None, g.descr.split()))
        self._groups[k] = g

    def freq(self, ps):
        """
        Converts picoseconds to steps based on the timestep
        """
        return int(round(ps / self.dt))

    def setall(self, keys, val):
        for k in keys:
            setattr(self, k, val)

    @property
    def tcgroups(self):
        t = type(self.tc_grps)
        if t is str:
            return 1
        elif t is list:
            return len(self.tc_grps)
        else:
            raise ValueError, 'Unknown type %t for "tc_grps"' % t

    def set_temperature(self, t):
        self.ref_t = self.tcgroups * [t]

    def set_tau_t(self, t):
        logger.debug('setting tau_t =', t)
        self.tau_t = self.tcgroups * [t]

    def set_gamma(self, g):
        logger.debug('setting gamma =', g)
        self.set_tau_t(1/float(g))

    def set_velocity_generation(self):
        logger.debug('Setting velocity generation')
        g = velocity_generation_group(self.tau_t[0], self.ld_seed)
        self.add(g)

    def unset_velocity_generation(self):
        try:
            del self._groups['VELOCITY_GENERATION']
            logger.debug('Unsetting velocity generation')
        except KeyError: pass

    def seed(self, value):
        for a in 'ld_seed gen_seed'.split():
            if hasattr(self, a):
                logger.debug('Setting', a, 'to', value)
                setattr(self, a, value)

    @classmethod
    def loads(cls, string):
        mdp   = cls()
        lines = string.split('\n')
        lines = map(str.strip, lines)
        g     = None
        for l in lines:
            if l.startswith(';'):
                desc = l[2:]
                g = MdpGroup(desc)
                mdp.add(g)
                continue
            pair = l.split('=')
            if len(pair) != 2 and len(l) > 0:
                logger.warn('unable able to parse line: "%s"' % l)
                continue
            elif len(l) == 0:
                continue
            k, v = map(str.strip, pair)
            g[k] = v
        return mdp

    def load(self, path):
        return self.loads(open(path).read())

    def dumps(self):
        return str(self)

    def save(self, path, overwrite=True):
        if os.path.exists(path) and not overwrite:
            raise ValueError, 'Path exists: %s' % path

        with open(path, 'w') as fd:
            fd.write(self.format())

        logger.info1('Saved file %s' % os.path.abspath(path))
