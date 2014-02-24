from . import process
from . import mdp
from . import mdp_defaults
from .util import StackDir
from . import log

import os
import collections
import subprocess
import shlex

__all__ = ['GmxCommand',
           'command',
           'cmd',
           'pdb2gmx',
           'grompp',
           'editconf',
           'genion',
           'genbox',
           'mdrun',
           ]

logger = log.getLogger()


def command(name):
    """
    Return a subclass of GmxCommand and set the __cmd__ static field.
    """
    cls = process.proc(name, GmxCommand)
    cls.__cmd__ = name
    return cls


def cmd(name, **parms):
    """
    Create a subclass of GmxCommand and return an instance with initialized parameters.
    """
    clazz = command(name)
    obj   = clazz(**parms)
    return obj

class GmxCommand(object):
    """
    A GROMACS command line utility.

    To add a new command, subclass GmxCommand and set the __cmd__ field.
    This can be done using the 'command' function above
    E.G.
    class pdb2gmx(GmxCommand):
        __cmd__ = 'pdb2gmx'

    This is equivalent to:
    pdb2gmx = command('pdb2gmx')

    Arguments passed to the constructor should mirror those passed the the underlying command.
    E.G.
    To exectute: pdb2gmx -f foo.pdb -o test.gro -water tip3p -ignh
    write: pdb2gmx(f='foo.pdb', o='test.gro', water='tip3p', ignh=True).run()
    """

    def __init__(self, **kws):
        self._parms = kws
        self._log = self.__cmd__ + '.log'
        self._logmode = 'a'

    def setLog(self, path, mode='a'):
        self._log = path
        self._logmode = mode

    def prep_parms(self):
        parms = list()
        for a, v in self._parms.iteritems():
            p = '-' + a
            if v is None: continue
            elif type(v) is bool:
                parms.append(p)
            else:
                parms.append('%s %s' % (p, v))
        return ' '.join(parms)

    def cmd(self):
        return self.__cmd__ + ' ' + self.prep_parms()

    def process(self):
        cmd = self.cmd()
        p = process.Process(cmd)

        try:
            p.run(self._log, self._logmode)
        except subprocess.CalledProcessError, e:
            logger.error('\n'.join([e.cmd, e.output]))
            raise

    def run(self):
        self.process()

    def __str__(self):
        return self.cmd()

pdb2gmx  = command('pdb2gmx')
editconf = command('editconf')
grompp   = command('grompp')
genion   = command('genion')
genbox   = command('genbox')
mdrun    = command('mdrun')

