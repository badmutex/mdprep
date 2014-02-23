from .mdp import *

__all__ = ['minimize_vacuum',
           'minimize_solvated',
           'explicit_solvent',
           'posres_explicit_solvent'
           ]

def minimize_vacuum():
    m             = MDP()
    g             = MdpGroup('PARAMETERS')
    g.define      = '-DFLEXIBLE'
    g.integrator  = 'steep'
    g.emtol       = 10.0
    g.nsteps      = -1
    g.nstenergy   = 1
    g.energygrps  = 'System'
    g.nstlist     = 1
    g.ns_type     = 'grid'
    g.coulombtype = 'Reaction-Field'
    g.epsilon_rf  = 78
    g.rcoulomb    = 1
    g.rvdw        = 1
    g.constraints = 'none'
    g.pbc         = 'no'
    m.add(g)
    return m

def minimize_solvated():
    m       = minimize_vacuum()
    m.emtol = 1.0
    m.pbc   = 'xyz'
    return m

def explicit_solvent(velocity_generation=False):

    m                    = MDP()
    g                    = MdpGroup('SETUP')
    m.add(g)
    
    g                    = MdpGroup('RUN CONTROL')
    g.integrator         = 'sd'
    g.ld_seed            = 42
    g.dt                 = 0.001
    g.nsteps             = -1
    m.add(g)

    g                    = MdpGroup('OUTPUT CONTROL')
    g.nstxout            = m.freq(100)
    g.nstvout            = m.freq(100)
    g.nstfout            = m.freq(100)
    g.nstlog             = m.freq(100)
    g.nstenergy          = m.freq(100)
    g.nstxtcout          = m.freq(100)
    g.xtc_grps           = 'System'
    m.add(g)

    g                    = MdpGroup('NEIGHBOR SEARCHING')
    g.nstlist            = 10
    g.ns_type            = 'grid'
    g.pbc                = 'xyz'
    g.periodic_molecules = 'no'
    g.rlist              = 1
    m.add(g)

    g                    = MdpGroup('ELECTROSTATICS')
    g.coulombtype        = 'PME'
    g.rcoulomb           = 1
    m.add(g)

    g                    = MdpGroup('VdW')
    g.vdwtype            = 'shift'
    g.rvdw               = 1
    m.add(g)

    g                    = MdpGroup('TEMPERATURE COUPLING')
    g.tcoupl             = 'no'
    g.tc_grps            = ['System']
    g.ref_t              = [330]
    g.tau_t              = [1.0]
    m.add(g)

    g                    = MdpGroup('PRESSURE COUPLING')
    g.pcoupl             = 'no'
    m.add(g)

    g                    = MdpGroup('BOND CONSTRAINTS')
    g.constraints        = 'none'
    m.add(g)

    if velocity_generation:
        g = velocity_generation_group(m)
        m.add(g)


    return m

def posres_explicit_solvent():
    m = explicit_solvent()
    m.define = '-DPOSRES'
    return m

