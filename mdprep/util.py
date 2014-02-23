import os
from . import log
logger = log.getLogger()
import collections
import copy
import StringIO as stringio


class StackDir(object):
    def __init__(self, path):
        self.dst = path
        self.src = os.path.abspath(os.getcwd())

    def __enter__(self):
        ensure_dir(self.dst)
        os.chdir(self.dst)
        logger.info1('Working in %s' % os.getcwd())

    def __exit__(self, *args, **kws):
        logger.info1('Leaving %s' % os.getcwd())
        os.chdir(self.src)

def ensure_dir(path):
    """
    Make sure the `path` if a directory by creating it if needed.
    """

    if not os.path.exists(path):
        logger.info1('Creating directory', path)
        os.makedirs(path)

def ensure_file(path):
    """
    make sure the `path` is a file by creating it if needed.
    """
    if os.path.exists(path): return
    root = os.path.dirname(path)
    ensure_dir(root)
    open(path, 'w').close()


class StringIO(stringio.StringIO):
    def __init__(self, *args, **kws):
        stringio.StringIO.__init__(self, *args, **kws)
        self.indentlvl = 0

    def indent(self, by=4):
        self.indentlvl += by

    def dedent(self, by=4):
        self.indentlvl -= by

    def write(self, *args, **kws):
        stringio.StringIO.write(self, self.indentlvl * ' ')
        stringio.StringIO.write(self, *args, **kws)

    def writeln(self, *args, **kws):
        self.write(*args, **kws)
        stringio.StringIO.write(self, '\n')
        

'''
WIP

def make_dotdict(base=dict):
    class DotDictBase(object):
        def __init__(self):
            object.__init__(self)
            object.__setattr__(self, '_kv', base())

        def __setitem__(self, k, v):
            self._kv[k] = v

        def __getitem__(self, k):
            return self._kv[k]

        def __getattr__(self, k):
            if k in self._kv:
                return self._kv
            else:
                raise AttributeError, k

        def __setattr__(self, k, v):
            if k in self.__dict__:
                self.__dict__[k] = v
            else:
                self._kv[k] = v

        def __deepcopy__(self, memo):
            o = self.__class__()
            o.__dict__.update(copy.deepcopy(self.__dict__))
            return o

    return DotDictBase



class dotdictify(dict):
    """
    Access dict via keys as attributes
    http://stackoverflow.com/questions/3031219
    """

    marker = object()
    def __init__(self, value=None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError, 'expected dict'

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, dotdictify):
            value = dotdictify(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        found = self.get(key, dotdictify.marker)
        if found is dotdictify.marker:
            found = dotdictify()
            dict.__setitem__(self, key, found)
        return found

    __setattr__ = __setitem__
    __getattr__ = __getitem__

'''
