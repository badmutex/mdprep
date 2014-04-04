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

pdb2gmx  = OptCommand('pdb2gmx')
editconf = OptCommand('editconf')
grompp   = OptCommand('grompp')
genion   = OptCommand('genion')
genbox   = OptCommand('genbox')
mdrun    = OptCommand('mdrun')

