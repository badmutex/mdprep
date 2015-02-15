from pxul.command import OptCommand
from pxul.os import SetEnv

import os

__all__ = [
    'NoAutobackup',
    'pdb2gmx',
    'grompp',
    'editconf',
    'genion',
    'genbox',
    'mdrun',
]

NoAutobackup = SetEnv(GMX_MAXBACKUP=-1)

class GmxCommand(OptCommand):
    def __init__(self, cmd):
        OptCommand.__init__(self, cmd, short_flag_prefix='-', long_flag_prefix='-')

pdb2gmx  = GmxCommand('pdb2gmx')
editconf = GmxCommand('editconf')
grompp   = GmxCommand('grompp')
genion   = GmxCommand('genion')
genbox   = GmxCommand('genbox')
mdrun    = GmxCommand('mdrun')
gmxdump  = GmxCommand('gmxdump')
