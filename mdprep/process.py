from . import log

import os
import subprocess
import shlex

logger = log.getLogger()

class Process(object):
    def __init__(self, cmd):
        self.cmd = cmd

    def run(self, log=None, mode='a'):
        logger.debug('EXECUTING: %s' % self.cmd)
        p = subprocess.Popen(shlex.split(self.cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode is not 0:
            raise subprocess.CalledProcessError(p.returncode, self.cmd, err + out)
        if log is not None:
            with open(log, mode) as fd:
                fd.write(err + '\n' + out)
        return out, err


class Command(object):
    def __init__(self, path):
        self._cmd = [path]

    @property
    def path(self):
        return self._cmd[0]

    def o(self, arg):
        """Add CLI option"""
        self._cmd.extend(shlex.split(arg))
        return self

    def __str__(self):
        return '<%s>' % ' '.join(map(repr, self._cmd))

    def __repr__(self):
        s = 'Command(%r)' % self.path
        for o in self._cmd[1:]:
            s += '.o(%r)' % repr(o)
        return s

    def __call__(self):
        return Process(self._cmd).run()


class OptCommand(Command):
    """
    A process that can take short-form command line parameters as keyword
    arguments.  The order is arguments is not stable, this can only be
    used when the order is unimportant.

    e.g.:
    Given: foo -a arga -b argb -c
    Write: OptCommand('foo')(a='arga', b='argb', c=True)

    Returns: (stdout, stderr)
    """

    def __call__(self, **kws):
        # prepare the parameters
        parms = list()
        for k, v in kws.iteritems():
            flag = '-' + k
            if v is None: continue
            elif type(v) is bool and v:
                arg = flag
            else:
                arg = '%s %s' % (flag, v)
            self.o(arg)

        # run
        return super(Command, self).__call__()

