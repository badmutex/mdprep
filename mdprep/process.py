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

class OptCommand(object):
    """
    A process that can take short-form command line parameters as keyword
    arguments.  The order is arguments is not stable, this can only be
    used when the order is unimportant.

    e.g.:
    Given: foo -a arga -b argb -c
    Write: OptCommand('foo')(a='arga', b='argb', c=True)

    Returns: (stdout, stderr)
    """

    def __init__(self, cmd):
        self._cmd = cmd

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
            parms.append(arg)
        parms = ' '.join(parms)

        # the command
        cmd = self._cmd + ' ' + parms

        # run
        return Process(cmd).run()

def proc(name, *supers):
    supers = supers or (Process,)
    cls    = type(name, supers, {})
    cls.__name__ = name
    return cls

def optcmd(cmd, name=None):
    name = name if name is not None else os.path.basename(cmd)
    cls = type(name, (OptCommand,), {})
    return cls(cmd)
