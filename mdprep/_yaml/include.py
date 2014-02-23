"""
Adapted from
http://stackoverflow.com/questions/528281

foo.yaml
    a: 1
    b:
        - 1.43
        - 543.55
    c: !include bar.yaml

bar.yaml
    - 3.6
    - [1, 2, 3]



"""
import os.path
import yaml

class Loader(yaml.Loader):

    def __init__(self, stream):

        ### backwards compatibility
        if hasattr(stream, 'name'):
            self._root = os.path.split(stream.name)[0]

        super(Loader, self).__init__(stream)


    def include(self, node):

        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, 'r') as f:
            return include_load(f)

Loader.add_constructor('!include', Loader.include)

def include_load(*args, **kws):
    kws['Loader'] = Loader
    return yaml.load(*args, **kws)
