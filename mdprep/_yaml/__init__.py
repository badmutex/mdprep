
# initial
from yaml         import *

"""
Comment out below because this in introducing a bug.
For instance the following will fail because the yaml_tag is not registered to the correct Loader.yaml_constructors dictionary

    from mdprep import yaml

    class Person(yaml.YAMLObject):
        yaml_tag = '!Person'

        def __init__(self, f, l):
            self.f = f
            self.l = l
"""

# # enhance
# from .strings     import *
# from .ordereddict import *
# from .include     import *

# # override
# load = include_load
