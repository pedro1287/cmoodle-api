import imp
import os

def load_from_file(filepath):
    mod_name,file_ext = os.path.splitext(os.path.split(filepath)[-1])
    if file_ext.lower() == '.py':
        return imp.load_source(mod_name, filepath)
    elif file_ext.lower() == '.pyc':
        return imp.load_compiled(mod_name, filepath)
    return None