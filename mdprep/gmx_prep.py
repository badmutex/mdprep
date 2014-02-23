from . import log
from . import gmx
from . import util
from . import mdp_defaults
import mdtraj
import prody
prody.confProDy(verbosity='critical')
import textwrap
import os
import shutil
import copy

__all__ = ['Prep']

logger = log.getLogger()


def count_occurences(string, lines):
    """
    Count the  number of times 'string' occures in 'lines'
    Where
      string :: str
      lines  :: [str]
    returns: int
    """
    count = 0
    for line in lines:
        if string in line:
            count += 1
    return count

class suffix(object):
    @classmethod
    def suffix(cls, name, suf): return name + '.' + suf

    @classmethod
    def gro(cls, n): return cls.suffix(n, 'gro')

    @classmethod
    def mdp(cls, n): return cls.suffix(n, 'mdp')

    @classmethod
    def tpr(cls, n): return cls.suffix(n, 'tpr')

    @classmethod
    def ndx(cls, n): return cls.suffix(n, 'ndx')

    @classmethod
    def pdb(cls, n): return cls.suffix(n, 'pdb')

    @classmethod
    def top(cls, n): return cls.suffix(n, 'top')

    @classmethod
    def trr(cls, n): return cls.suffix(n, 'trr')


class PrepareSolvatedSystem(object):
    def __init__(self, workarea='mdprep'):
        self.name     = None
        self.workarea = workarea
        self._cn      = None      # current name
        self._pn      = None      # previous name
        self._top     = None      # path to topology file

    @property
    def cn(self): return self._cn

    @property
    def pn(self): return self._pn

    @property
    def top(self): return self._top

    def initialize(self, pdb, ff='amber03', water='tip3p', ignh=True):
        logger.info1('Importing to GMX format')
        top = suffix.top(self.cn)
        gmx.pdb2gmx(
            f     = pdb,
            o     = suffix.gro(self.cn),
            p     = top,
            ff    = ff,
            water = water,
            ignh  = ignh).run()
        self._top = top
        self._pn  = self.cn


    def minimize_vacuum(self, mdp):
        logger.info1('Minimization in vacuum')
        self._cn = self.name + '_EMV'
        cn, pn = self.cn, self.pn
        mdp_path = suffix.mdp(self.cn)
        mdp.save(mdp_path)
        tpr = suffix.tpr(cn)
        gmx.grompp(
            f = mdp_path,
            c = suffix.gro(pn),
            p = suffix.top(pn),
            o = tpr
            ).run()
        gmx.mdrun(
            s      = tpr,
            deffnm = cn,
            c      = suffix.pdb(cn),
            ).run()
        self._pn = self._cn

    def solvate(self,
                     mdp, boxtype='triclinic', boxdist=1.0, solv='spc216.gro',
                     concentration=0.15, neutral=True, pname='NA', nname='CL'):
        nbox  = self.name + '_box'
        nwat  = self.name + '_wat'
        nsolv = self.name + '_sol'

        logger.info1('Solvating')
        self._cn = nbox
        gmx.editconf(
            f = suffix.pdb(self.pn),
            o = suffix.gro(nbox),
            bt = boxtype,
            d = boxdist,
            ).run()
        self._cn = nwat
        gmx.genbox(
            cp = suffix.gro(nbox),
            cs = solv,
            p  = self.top,
            o  = suffix.gro(self.cn)
            ).run()
        gmx.grompp(
            f = suffix.mdp(self.pn),
            c = suffix.gro(self.cn),
            p = self.top,
            o = suffix.tpr(self.cn)
            ).run()

        # create atom indices for water
        pdb = suffix.pdb(self.cn)
        gmx.editconf(
            f = suffix.tpr(self.cn),
            o = pdb
            ).run()

        top = prody.parsePDB(pdb)
        sel = top.select('resname is SOL')
        idx = sel.getIndices()
        idx += 1 # GMX starts with 1, prody with 0
        ndx = suffix.ndx(nwat)
        with open(ndx, 'w') as fd:
            fd.write('[ SOL ] \n')
            # GMX has a limited buffer for read ndx files
            idx = map(str, idx)
            idx = ' '.join(idx)
            idx = textwrap.wrap(idx)
            idx = '\n'.join(idx)
            fd.write(idx + '\n')

        gmx.genion(
            n       = ndx,
            s       = suffix.tpr(nwat),
            o       = suffix.gro(nsolv),
            conc    = concentration,
            neutral = neutral,
            pname   = pname,
            nname   = nname
            ).run()

        # figure out the number of solvent, cation, and anion molecules
        logger.info1('Calculating number of solvent, cation, and anion molecules')
        conf = open(suffix.gro(nsolv)).readlines()
        nsol = count_occurences('SOL', conf) / 3
        ncat = count_occurences(pname, conf)
        nani = count_occurences(nname, conf)
        del conf

        # write a new topology file with the updated counts
        logger.info1('Generating new topology file')
        top = open(self.top).readlines()
        top = top[:-1] # the last line containts the number of solvent molecules, which is outdated
        top.append('SOL        %s\n' % nsol)
        top.append('%s        %s\n' % (pname, ncat))
        top.append('%s        %s\n' % (nname, nani))
        top = ''.join(top)
        self._top = suffix.top(nsolv)
        open(self.top, 'w').write(top)
        self._pn = nsolv
        self._cn = nsolv

        # minimize the solvated system
        logger.info1('Minimizaing solvated system')
        mdp_path = suffix.mdp(self.cn)
        mdp.save(mdp_path)
        tpr = suffix.tpr(self.cn)
        gmx.grompp(
            f = mdp_path,
            c = suffix.gro(self.cn),
            p = self.top,
            o = tpr
            ).run()
        gmx.mdrun(
            s      = tpr,
            deffnm = self.cn,
            ).run()
        self._pv = self.cn


    def relax(self, mdp, gammas=None, steps=None):
        logger.info1('Iterative equilibration')
        gammas = [1000, 100, 10, 1] if gammas is None else gammas
        name = self.name + '_itr_posres_eq'

        mdp_itr = suffix.mdp(name)
        mdp.SETUP.define = '-DPOSRES'
        if steps is not None:
            mdp.nsteps = steps

        mdp.set_velocity_generation()
        for g in gammas:
            mdp.dt = 0.001
            mdp.set_gamma(g)
            logger.debug('using gamma =', g)
            logger.debug('using dt =', mdp.dt)
            mdp.save(mdp_itr)

            self._cn = name + '_gamma-%d' % g
            gmx.grompp(
                f = mdp_itr,
                c = suffix.gro(self.pn),
                t = suffix.trr(self.pn),
                p = self.top,
                o = suffix.tpr(self.cn)
                ).run()
            gmx.mdrun(
                s      = suffix.tpr(self.cn),
                deffnm = self.cn,
                v      = True
                ).run()
            self._pn = self.cn
            mdp.unset_velocity_generation()

    def equilibrate(self, mdp, steps=None):
        logger.info1('Equilibrating')
        self._cn = self.name + '_eq'
        if steps is not None:
            mdp.nsteps = steps
        mdp_path = suffix.mdp(self.cn)
        mdp.unset_velocity_generation()
        mdp.save(mdp_path)

        gmx.grompp(
            f = mdp_path,
            c = suffix.gro(self.pn),
            t = suffix.trr(self.pn),
            p = self.top,
            o = suffix.tpr(self.cn)
            ).run()
        gmx.mdrun(
            s      = suffix.tpr(self.cn),
            deffnm = self.cn,
            v      = True
            ).run()


    def prepare(self,
                pdb,
                ff             = 'amber03',
                water          = 'tip3p',
                ignh           = True,
                mdp_min_vac    = None,
                mdp_min_sol    = None,
                mdp_run        = None,
                iter_gammas    = None,
                iter_steps     = 500,
                eq_steps       = 500,
                seed           = None):


        logger.info('Preparing %s with %s in %s' % (pdb, ff, os.getcwd()))

        pdb = os.path.abspath(pdb)
        wa  = os.path.join(self.workarea)
        name = os.path.splitext(os.path.basename(pdb))[0]

        mdp_min_vac = mdp_defaults.minimize_vacuum()   if mdp_min_vac is None else mdp_min_vac.copy()
        mdp_min_sol = mdp_defaults.minimize_solvated() if mdp_min_sol is None else mdp_min_sol.copy()
        mdp_run     = mdp_defaults.explicit_solvent()  if mdp_run     is None else mdp_run.copy()

        if seed is not None:
            mdp_run.seed(seed)

        self.name = name
        self._cn  = name

        with util.StackDir(wa):
            self.initialize(pdb, ff=ff, water=water, ignh=ignh)
            self.minimize_vacuum(mdp_min_vac)
            self.solvate(mdp_min_sol)
            self.relax(copy.deepcopy(mdp_run), gammas=iter_gammas, steps=iter_steps)
            self.equilibrate(copy.deepcopy(mdp_run), steps=eq_steps)

        conf = 'conf.gro',  suffix.gro(self.pn)
        top  = 'topol.top', self.top
        itp  = 'posre.itp', 'posre.itp'

        for new, old in [conf, top, itp]:
            shutil.copy(os.path.join(self.workarea, old), new)
            logger.info1('Saved file %s' % os.path.abspath(new))

        with open('grompp.mdp', 'w') as fd:
            fd.write(str(mdp_run))
            logger.info1('Saved file', os.path.abspath(fd.name))

        # create tpr with velocities
        logger.info1('Creating run tpr')
        gmx.grompp(t = suffix.trr(os.path.join(self.workarea, self.pn))).run()
