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
KNOWN_SUFFIXES = set(['.img', '.py', '.icy', '.icy.z', '.cpp', '.so', config.module_object_suffix()])

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


def _header_tokens(text):
  """Read identifiers outside comments and literals, including nested pragmas."""
  import re
  identifier = re.compile(r"[A-Za-z_][A-Za-z_0-9']*(?:\.[A-Za-z_][A-Za-z_0-9']*)*")
  character = re.compile(
      r"'(?:[^'\\\r\n]|\\(?:[0-9]+|x[0-9A-Fa-f]+|o[0-7]+|[A-Za-z]+|[^\r\n]))'"
    )
  symbol = re.compile(r'[!#$%&*+./<=>?@\\^|:~-]+')
  pos = 0
  while pos < len(text):
    if text.startswith('{-', pos):
      depth = 1
      pos += 2
      while pos < len(text) and depth:
        if text.startswith('{-', pos):
          depth += 1
          pos += 2
        elif text.startswith('-}', pos):
          depth -= 1
          pos += 2
        else:
          pos += 1
    elif text[pos] == "'" and (match := character.match(text, pos)):
      pos = match.end()
    elif text[pos] == '"':
      pos += 1
      while pos < len(text):
        char = text[pos]
        pos += 1
        if char == '\\':
          pos += 1
        elif char == '"':
          break
    elif match := symbol.match(text, pos):
      operator = match.group()
      if operator.startswith('--') and not operator.strip('-'):
        end = text.find('\n', pos)
        pos = len(text) if end < 0 else end + 1
      else:
        pos = match.end()
    else:
      match = identifier.match(text, pos)
      if match:
        yield match.group()
        pos += len(match.group())
      else:
        pos += 1


def module_name(filename):
  """The comment-aware declared name, falling back to the source basename."""
  try:
    source = curryfilename(filename)
  except ValueError:
    return os.path.splitext(os.path.basename(filename.removesuffix('.z')))[0]
  try:
    with open(source, encoding='utf-8') as stream:
      tokens = iter(_header_tokens(stream.read()))
      for token in tokens:
        if token == 'module':
          return next(tokens, os.path.basename(source)[:-len('.curry')])
  except (OSError, UnicodeError):
    pass
  return os.path.basename(source)[:-len('.curry')]


def logging_module_name(filename):
  """The declared module name, or the product's basename when source is absent."""
  return module_name(filename)
