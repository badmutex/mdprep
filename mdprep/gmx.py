from . import process
from . import mdp
from . import mdp_defaults
from .util import StackDir
from . import log

import os
import collections
import subprocess
import shlex

__all__ = [
    'NoAutobackup',
    'pdb2gmx',
    'grompp',
    'editconf',
    'genion',
    'genbox',
    'mdrun',
]

class NoAutobackup(object):
    def __init__(self):
        self._k = 'GMX_MAXBACKUP'
        self._val = None

    def disable_backups(self):
        self.__enter__()

    def enable_backups(self):
        self.__exit__()

    def __enter__(self):
        if self._k in os.environ:
            self._val   = os.environ[self._k]
        os.environ[self._k] = '-1'

    def __exit__(self, *args, **kws):
        if self._val is not None:
            os.environ[self._k] = self._val


pdb2gmx  = process.OptCommand('pdb2gmx')
editconf = process.OptCommand('editconf')
grompp   = process.OptCommand('grompp')
genion   = process.OptCommand('genion')
genbox   = process.OptCommand('genbox')
mdrun    = process.OptCommand('mdrun')

