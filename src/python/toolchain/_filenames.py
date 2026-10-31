'''Code for determining related filenames.'''

from ..backends import IBackend
from .. import config
import logging, os

__all__ = [
    'curryfilename', 'icurryfilename', 'installed_relpath'
  , 'replacesuffix'
  ]
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()
KNOWN_SUFFIXES = set(['.img', '.py', '.icy', '.icy.z', '.cpp', '.so'])

class ImageProduct(str):
  """A private image path with its original translation input."""
  def __new__(cls, path, icyfile):
    result = super().__new__(cls, path)
    result.icyfile = icyfile
    return result


def sourcefilename(filename):
  """Associate a translation record with its source, including standalone ICurry."""
  try:
    return curryfilename(filename)
  except ValueError:
    return filename


def curryfilename(filename):
  '''
  Gets the Curry file associated with a module product.  If the input
  is a Curry file, it is returned.
  '''
  if isinstance(filename, ImageProduct):
    filename = filename.icyfile
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

def installed_relpath(filename):
  '''
  The path of ``filename`` relative to the installation (SPRITE_HOME) when
  the file lies under it, by the spelling of the two paths or by their real
  paths; else None.  The code generators name the source of a library
  module this way, and the loaders of the backends resolve the name against
  the installation of the process (config.installed_path).  So a generated
  file of the library carries no path of the machine, and a package manager
  that relocates an installation rewrites nothing in it.
  '''
  if not filename:
    return None
  prefix = config.prefix()
  for root, name in [
      (prefix, filename)
    , (os.path.realpath(prefix), os.path.realpath(filename))
    ]:
    root = root.rstrip(os.sep)
    if name.startswith(root + os.sep):
      return os.path.relpath(name, root)
  return None

def icurryfilename(filename):
  '''Gets the ICurry file name associated with a Curry file.'''
  if isinstance(filename, ImageProduct):
    return filename.icyfile
  if filename.endswith('.curry'):
    path,name = os.path.split(filename)
    return os.path.join(path, '.curry', SUBDIR, name[:-6]+'.icy')
  else:
    for suffix in KNOWN_SUFFIXES:
      if filename.endswith(suffix):
        return filename[:-len(suffix)] + '.icy'
    else:
      raise ValueError('bad suffix for %s' % filename)

def replacesuffix(filename, suffix):
  icyname = icurryfilename(filename)
  assert icyname.endswith('.icy')
  return icyname[:-4] + suffix


def logging_module_name(filename):
  """The declared module name, or the product's basename when source is absent."""
  import re
  try:
    source = curryfilename(filename)
  except ValueError:
    return os.path.splitext(os.path.basename(filename.removesuffix('.z')))[0]
  try:
    with open(source, encoding='utf-8') as stream:
      text = stream.read()
    match = re.search(r'^\s*module\s+([\w.]+)\b', text, re.MULTILINE)
    if match:
      return match.group(1)
  except (OSError, UnicodeError):
    pass
  return os.path.basename(source)[:-len('.curry')]
