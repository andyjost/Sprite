'''Code for determining related filenames.'''

from ..backends import IBackend
from .. import config
import logging, os

__all__ = ['curryfilename', 'icurryfilename', 'jsonfilenames', 'replacesuffix']
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()
KNOWN_SUFFIXES = set(['.py', '.json', '.json.z', '.icy', '.icy.z', '.cpp', '.so'])

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
    for suffix in KNOWN_SUFFIXES:
      if filename.endswith(suffix):
        return os.path.join(
            os.sep.join(parts[:-3])
          , name[:-len(suffix)]+'.curry'
          )
    else:
      raise ValueError('bad suffix for %s' % filename)

def icurryfilename(filename):
  '''Gets the ICurry file name associated with a Curry file.'''
  if filename.endswith('.curry'):
    path,name = os.path.split(filename)
    return os.path.join(path, '.curry', SUBDIR, name[:-6]+'.icy')
  else:
    for suffix in KNOWN_SUFFIXES:
      if filename.endswith(suffix):
        return filename[:-len(suffix)] + '.icy'
    else:
      raise ValueError('bad suffix for %s' % filename)

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

def replacesuffix(filename, suffix):
  icyname = icurryfilename(filename)
  assert icyname.endswith('.icy')
  return icyname[:-4] + suffix

