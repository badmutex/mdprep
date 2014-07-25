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

pdb2gmx  = OptCommand('pdb2gmx', short_flag_prefix='-', long_flag_prefix='-')
editconf = OptCommand('editconf', short_flag_prefix='-', long_flag_prefix='-')
grompp   = OptCommand('grompp', short_flag_prefix='-', long_flag_prefix='-')
genion   = OptCommand('genion', short_flag_prefix='-', long_flag_prefix='-')
genbox   = OptCommand('genbox', short_flag_prefix='-', long_flag_prefix='-')
mdrun    = OptCommand('mdrun', short_flag_prefix='-', long_flag_prefix='-')

