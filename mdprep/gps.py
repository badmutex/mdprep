
"""
Import/export utilities functions for guamps (gps) format.
"""

import numpy as np

import re
import textwrap
from cStringIO import StringIO

def write_array(fd, vector, fmt='%f'):

    # find the dimensions
    shape = vector.shape
    if len(shape) == 1:
        ncells, ncoords, ndims = 1, len(vector), 1
    elif len(shape) == 2:
        ncells, ncoords = shape
        ndims = 1
    elif len(shape) == 3:
        ncells, ncoords, ndims = shape
    else:
        raise ValueError, 'Unknown shape {}'.format(shape)

    # format and write
    header = textwrap.dedent("""\
        ncells: {}
        ncoords: {}
        ndims: {}

        """.format(ncells, ncoords, ndims))

    fd.write(header)
    np.savetxt(fd, vector.flatten(), fmt=fmt)

def write_scalar(fd, val):
    fd.write(str(val))

def read_array(fd):
    def match_header(name):
        line = fd.readline()
        match = re.match(r'{}: *(\d+)'.format(name), line)
        strval = match.group(1)
        intval = int(strval)
        return intval

    ncells = match_header('ncells')
    ncoords = match_header('ncoords')
    ndims = match_header('ndims')
    fd.readline()

    array = np.loadtxt(fd)
    return array.reshape((ncells, ncoords, ndims))

def read_scalar(fd, mktype):
    return mktype(fd.readline().strip())


def _with_stringio(creator, retval, fn, *args, **kws):
    fd = creator()
    try:
        val = fn(fd, *args, **kws)
        if retval == 'cont':
            return val
        elif retval == 'str':
            s = fd.getvalue()
            return s
        else:
            raise ValueError, 'Unknown retval {}'.format(retval)
    finally:
        fd.close()

def array2str(vector, fmt='%f'):
    return _with_stringio(StringIO, 'str', lambda fd: write_array(fd, vector, fmt=fmt))

def scalar2str(val):
    return _with_stringio(StringIO, 'str', lambda fd: write_scalar(fd, val))

def str2array(s):
    return _with_stringio(lambda: StringIO(s), 'cont', read_array)

def str2scalar(s, mktype):
    return _with_stringio(lambda: StringIO(s), 'cont', lambda fd: read_scalar(fd, mktype))
