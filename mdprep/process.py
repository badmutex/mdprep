from . import log

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

def proc(name, *supers):
    supers = supers or (Process,)
    cls    = type(name, supers, {})
    cls.__name__ = name
    return cls
