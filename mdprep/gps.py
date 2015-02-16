
"""
Import/export utilities functions for guamps (gps) format.
"""

import numpy as np

import re
import textwrap

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
