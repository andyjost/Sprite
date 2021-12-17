'''Code for determining related filenames.'''

from .. import config
import logging, os

__all__ = ['curryfilename', 'icurryfilename', 'jsonfilenames', 'pyfilename']
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

def curryfilename(filename):
  '''
  Gets the Curry file associated with a JSON file or ICurry file.  If the input
  is a Curry file, it is returned.
  '''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if filename.endswith('.curry'):
    return filename
  else:
    parts = filename.split(os.sep)
    if len(parts) < 3 or parts[-2] != SUBDIR or parts[-3] != '.curry':
      raise ValueError('bad path for %s' % filename)
    name = parts[-1]
    for suffix in ['.json', '.json.z', '.icy', '.icy.z']:
      if name.endswith(suffix):
        break
    else:
      raise ValueError('bad suffix for %s' % filename)
    return os.path.join(
        os.sep.join(parts[:-3])
      , name[:-len(suffix)]+'.curry'
      )

def icurryfilename(filename):
  '''Gets the ICurry file name associated with a Curry file.'''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if filename.endswith('.icy'):
    return filename
  elif filename.endswith('.json'):
    return filename[:-5] + '.icy'
  elif not filename.endswith('.curry'):
    raise ValueError('bad suffix for %s' % filename)
  assert filename.endswith('.curry')
  path,name = os.path.split(filename)
  return os.path.join(path, '.curry', SUBDIR, name[:-6]+'.icy')

def jsonfilenames(filename, suffixes=None):
  '''Gets the JSON file name(s) associated with a Curry or ICY file.'''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if not filename.endswith('.icy'):
    filename = icurryfilename(filename)
  assert filename.endswith('.icy')
  base = filename[:-4] + '.json'
  return tuple(
      name for name in [base, base + '.z']
           if suffixes is None or
              any(name.endswith(suffix) for suffix in suffixes)
    )

def pyfilename(filename):
  '''Gets the Python file name associated with a Curry, ICY, or JSON file.'''
  icy = icurryfilename(filename)
  assert icy.endswith('.icy')
  return icy[:-4] + '.py'
