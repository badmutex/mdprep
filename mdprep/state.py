from . import util
from . import _yaml as yaml
import collections

class State(object):

    def attributes(self):
        return self.__dict__.keys()

    def __contains__(self, key):
        return key in self.__dict__

    def __getitem__(self, k):
        return self.__dict__[k]

    def __setitem__(self, k, v):
        self.__dict__[k] = v

    @classmethod
    def load(csl, path):
        util.ensure_file(path)
        st = yaml.load(open(path))
        if st: return st
        else  : return csl()

    def add(self, name, init=None):
        init = init if init is not None else dict()
        setattr(self, name, init)
        return getattr(self, name)

    def astype(self, cls):
        obj = cls()
        obj.__dict__ = self.__dict__
        return obj

    def save(self, path):
        yaml.dump(self, open(path, 'w'), default_flow_style=False)


class Analysis(State): pass
