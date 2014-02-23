
import yaml

class quoted_str(str): pass

def quoted_str_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
yaml.add_representer(quoted_str, quoted_str_presenter)

class literal_str(str): pass

def literal_str_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
yaml.add_representer(literal_str, literal_str_presenter)
