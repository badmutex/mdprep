from . import gmx
from . import mdp_defaults

import pxul
from pxul.logging import logger

import mdtraj
import prody
prody.confProDy(verbosity='critical')
import textwrap
import os
import shutil
import copy
import glob


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

    @classmethod
    def itp(cls, n): return cls.suffix(n, 'itp')



class SystemPreparer(object):
    def __init__(self, workarea='mdprep'):
        self._name     = None
        self._workarea = workarea
        self._cn       = None      # current name
        self._pn       = None      # previous name
        self._top      = None      # path to topology file

        self._md_steps = [] # [(function, args, kwds)]

    def register_md_step(self, fn, *args, **kws):
        self._md_steps.append((fn, args, kws))

    def register_mdp(self, mdp):
        self._mdp_run = mdp


    @property
    def name(self): return self._name

    def set_name(self, n): self._name = n

    def get_name(self, path):
        """
        The `name` is the basename of `path` stripped of the suffix
        """
        return os.path.splitext(os.path.basename(path))[0]

    @property
    def workarea(self): return self._workarea

    @property
    def cn(self): return self._cn

    @cn.setter
    def cn(self, new): self._cn = new

    @property
    def pn(self): return self._pn

    @pn.setter
    def pn(self,new): self._pn = new

    @property
    def top(self): return self._top

    @top.setter
    def top(self,new): self._top = new



    def next_name(self):
        self.pn = self.cn


    def initialize(self, pdb, ff='amber03', water='tip3p', ignh=True):
        logger.info1('Importing to GMX format')
        top = suffix.top(self.cn)
        gmx.pdb2gmx(
            f     = pdb,
            o     = suffix.gro(self.cn),
            p     = top,
            ff    = ff,
            water = water,
            ignh  = ignh)
        self.top = top
        self.next_name()

    def minimize(self, mdp, output_to=suffix.pdb):
        logger.info1('Minimization')
        self.cn = self.name + '_EM'
        cn, pn = self.cn, self.pn
        mdp_path = suffix.mdp(self.cn)
        mdp.save(mdp_path)
        tpr = suffix.tpr(cn)
        gmx.grompp(
            f = mdp_path,
            c = suffix.gro(pn),
            p = suffix.top(pn),
            o = tpr
            )
        gmx.mdrun(
            s      = tpr,
            deffnm = cn,
            c      = output_to(cn),
            nt     = 1,
            )
        self.next_name()

    def equilibrate(self, mdp, steps=None, gen_velocities=True):
        logger.info1('Equilibrating')
        self.cn = self.name + '_eq'
        if steps is not None:
            mdp.nsteps = steps
        mdp_path = suffix.mdp(self.cn)
        if gen_velocities:
            mdp.set_velocity_generation()
        else:
            mdp.unset_velocity_generation()
        mdp.save(mdp_path)

        gmx.grompp(
            f = mdp_path,
            c = suffix.gro(self.pn),
            t = suffix.trr(self.pn),
            p = self.top,
            o = suffix.tpr(self.cn)
            )
        gmx.mdrun(
            s      = suffix.tpr(self.cn),
            deffnm = self.cn,
            v      = True
            )

    def prepare(self, pdb,
                seed = None):

        cwd = os.getcwd()
        logger.info('Preparing %s in %s' % (os.path.relpath(pdb, cwd), cwd))

        pdb = os.path.abspath(pdb)
        wa  = os.path.join(self.workarea)
        name = os.path.splitext(os.path.basename(pdb))[0]

        if seed is not None:
            mdp_run.seed(seed)

        self.set_name(name)
        self.cn  = name

        with pxul.os.StackDir(wa):
            pxul.os.clear_dir(os.getcwd())
            for fn, args, kws in self._md_steps:
                fn(*args, **kws)

        if not name:
            name = self.name

        conf = suffix.gro(name), suffix.gro(self.pn)
        top  = suffix.top(name), self.top
        itp  = suffix.itp(name), 'posre.itp'
        mdp  = suffix.mdp(name)

        for new, old in [conf, top, itp]:
            shutil.copy(os.path.join(self.workarea, old), new)
            logger.info1('Saved file %s' % os.path.abspath(new))

        with open(mdp, 'w') as fd:
            fd.write(str(self._mdp_run))
            logger.info1('Saved file', os.path.abspath(fd.name))

        # create tpr with velocities
        logger.info1('Creating run tpr')
        conf  = conf[0]
        top   = top[0]
        mdout = suffix.mdp('{}_mdout'.format(name))
        tpr   = suffix.tpr(name)
        gmx.grompp(f=mdp, c=conf, po=mdout, p=top, o=tpr, t=suffix.trr(os.path.join(self.workarea, self.cn)))

        return dict(conf=conf,top=top,mdout=mdout,tpr=tpr)


class PrepareSolvatedSystem(SystemPreparer):


    def solvate(self,
                     mdp, boxtype='triclinic', boxdist=1.0, solv='spc216.gro',
                     concentration=0.15, neutral=True, pname='NA', nname='CL'):
        nbox  = self.name + '_box'
        nwat  = self.name + '_wat'
        nsolv = self.name + '_sol'

        logger.info1('Solvating')
        self.cn = nbox
        gmx.editconf(
            f = suffix.pdb(self.pn),
            o = suffix.gro(nbox),
            bt = boxtype,
            d = boxdist,
            )
        self.cn = nwat
        gmx.genbox(
            cp = suffix.gro(nbox),
            cs = solv,
            p  = self.top,
            o  = suffix.gro(self.cn)
            )
        gmx.grompp(
            f = suffix.mdp(self.pn),
            c = suffix.gro(self.cn),
            p = self.top,
            o = suffix.tpr(self.cn)
            )

        # create atom indices for water
        pdb = suffix.pdb(self.cn)
        gmx.editconf(
            f = suffix.tpr(self.cn),
            o = pdb
            )

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
            )

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
        self.top = suffix.top(nsolv)
        open(self.top, 'w').write(top)
        self.pn = nsolv
        self.cn = nsolv

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
            )
        gmx.mdrun(
            s      = tpr,
            deffnm = self.cn,
            )
        self.next_name()


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

            self.cn = name + '_gamma-%d' % g
            gmx.grompp(
                f = mdp_itr,
                c = suffix.gro(self.pn),
                t = suffix.trr(self.pn),
                p = self.top,
                o = suffix.tpr(self.cn)
                )
            gmx.mdrun(
                s      = suffix.tpr(self.cn),
                deffnm = self.cn,
                v      = True
                )
            self.next_name()
            mdp.unset_velocity_generation()


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


        mdp_min_vac = mdp_defaults.minimize_vacuum()   if mdp_min_vac is None else mdp_min_vac.copy()
        mdp_min_sol = mdp_defaults.minimize_solvated() if mdp_min_sol is None else mdp_min_sol.copy()
        mdp_run     = mdp_defaults.explicit_solvent()  if mdp_run     is None else mdp_run.copy()

        self.register_md_step(self.initialize , os.path.abspath(pdb), ff=ff, water=water, ignh=ignh)
        self.register_md_step(self.minimize   , mdp_min_vac)
        self.register_md_step(self.solvate    , mdp_min_sol)
        self.register_md_step(self.relax      , copy.deepcopy(mdp_run), gammas=iter_gammas, steps=iter_steps)
        self.register_md_step(self.equilibrate, copy.deepcopy(mdp_run), steps=eq_steps)
        self.register_mdp(mdp_run)

        return super(PrepareSolvatedSystem, self).prepare(pdb, seed=seed)

class PrepareImplicitSolventSystem(SystemPreparer):

    def prepare(self,
                pdb,
                ff = 'amber03',
                water = 'none',
                ignh = True,
                mdp_min = None,
                mdp_run = None,
                iter_gammas = None,
                iter_steps = 500,
                eq_steps = 500,
                seed = None):

        mdp_min = mdp_defaults.minimize_implicit_solvent() if mdp_min is None else mdp_min.copy()
        mdp_run = mdp_defaults.implicit_solvent()          if mdp_run is None else mdp_run.copy()

        self.register_md_step(self.initialize , os.path.abspath(pdb)  , ff=ff, water=water   , ignh=ignh)
        self.register_md_step(self.minimize   , mdp_min               , output_to=suffix.gro)
        self.register_md_step(self.equilibrate, copy.deepcopy(mdp_run), steps=eq_steps)
        self.register_mdp(mdp_run)

        return super(PrepareImplicitSolventSystem, self).prepare(pdb, seed=seed)
