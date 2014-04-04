from . import gmx_prep
from . import mdp
from . import state
from . import _yaml as yaml

import pxul
from pxul.StringIO import StringIO
from pxul.logging import logger

import collections
import os
import types

class Run(object):
    """
    A collection of parameters and inputs that can be run
    """

    def __init__(self, *namespace):
        self.params = dict()
        self.inputs = dict()

    @property
    def param_names(self): return set(self.params.keys())

    @property
    def input_names(self): return set(self.inputs.keys())

    def __str__(self):
        return yaml.dump(self, default_flow_style=False)

    def save(self, prefix='.', name='run.yaml'):
        pxul.os.ensure_dir(prefix)
        ypath = os.path.join(prefix, name)
        with open(ypath, 'w') as fd:
            logger.info1('Saving', fd.name)
            yaml.dump(self, fd)

    def prepare(self, *args, **kws):
        raise NotImplementedError

    def satisfies(self, **predicates):
        """
        Returns boolean indicating that the parameters satisfy the requested parameters in 'predicates'
        """

        if not predicates: return True

        for param, value in predicates.iteritems():
            if param in self.params and not value == self.params[param]:
                return False
        return True


class GromacsRun(Run):

    @property
    def mdp(self): return self.inputs['mdp']

    @mdp.setter
    def mdp(self, v): self.inputs['mdp'] = v

    def get_mdp(self):
        typ    = type(self.mdp)
        logger.debug('Loading MDP from', typ)

        if typ is str:
            return mdp.MDP.loads(self.mdp)

        elif typ is types.FunctionType:
            return self.mdp()

        elif typ is mdp.MDP:
            return self.mdp

        else:
            raise TypeError, 'Unknown mdp type %s' % typ

    @property
    def conf(self): return self.inputs['conf']

    @conf.setter
    def conf(self, v): self.inputs['conf'] = v

    def prepare(self):
        prep = gmx_prep.PrepareSolvatedSystem()
        prep.prepare(self.conf,
                     self.params['forcefield'],
                     self.params['water'],
                     mdp_run = self.get_mdp(),
                     seed    = self.inputs['seed'])


class Experiment(object):
    """
    A collections of different 'Run's exploring some parameter space
    """

    def __init__(self, *namespace):
        n = ('experiment',) if not namespace else namespace
        n = map(str, n)
        self.name = os.path.join(*n)
        self.runs = dict()

    def add(self, e, k=None):
        ix = k if k is not None else len(self.runs)
        self.runs[ix] = e

    def __getitem__(self, k):
        return self.runs[k]

    def __setitem__(self, k, v):
        self.add(k, v)

    def __iter__(self):
        return iter(self.runs)

    def _name_set(self, attr):
        s = set()
        for e in self.runs.itervalues():
            for a in getattr(e, attr):
                s.add(a)
        return s

    def load_state(self, prefix=None, name='state.yaml'):
        prefix = prefix if prefix is not None else self.name
        path   = os.path.join(prefix, name)
        anl    = state.State.load(path)
        return path, anl

    @property
    def param_names(self):
        return self._name_set('param_names')

    def summary(self):
        ### collect the sets of the keys and values for each experiment
        parms    = set()
        p_values = collections.defaultdict(set)
        inputs   = set()
        i_values = collections.defaultdict(set)
        for e in self.runs.itervalues():
            for p in e.param_names:
                parms.add(p)
                p_values[p].add(e.params[p])
            for i in e.input_names:
                inputs.add(i)
                i_values[i].add(e.inputs[i])

        ### create summary
        with StringIO() as si:
            si.writeln('Experiment: %d runs' % len(self.runs))
            si.indent()
            si.writeln('Parameters of (values):')
            si.indent()
            for p in parms: si.writeln('- %s: [%s]' % (p, ', '.join(map(str, p_values[p]))))
            si.dedent()
            si.writeln('Inputs of (count):')
            si.indent()
            for i in inputs: si.writeln('- %s: %s' % (i, len(i_values[i])))
            si.dedent()
            si.dedent()

            return si.getvalue().strip() # strip to remove trailing newline

    def __str__(self):
        return self.summary()

    def __len__(self):
        return len(self.runs)

    def save(self, prefix=None, name='experiment.yaml'):
        prefix = self.name if prefix is None else prefix
        pxul.os.ensure_dir(prefix)
        ypath = os.path.join(prefix, name)
        with  open(ypath, 'w') as fd:
            logger.info('Saving experiments:', fd.name)
            yaml.dump(self, fd, default_flow_style=False)
            logger.info1('Writing children')
            for k, r in self.runs.iteritems():
                r.save(prefix=os.path.join(self.name, str(k)))

