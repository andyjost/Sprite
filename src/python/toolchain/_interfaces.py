'''Content provenance of the interfaces read by the toolchain.

The FlatCurry interface supplies operation indices, constructor order,
arities and newtypes; the Curry interface supplies types and synonyms.
Neither file's timestamp nor its installation path enters the digest.
'''
from .. import cache, config
from . import _filenames, _frontend
from .flat2icurry.interfaces import InterfaceFinder
from .flat2icurry.errors import Flat2ICurryError
import hashlib, json, os, re

VERSION = 1
SUFFIX = '.imports'
_HEADER = re.compile(r'\s*\(IProg\s+"[^"]*"\s*\[([^]]*)\]')

def search_path(filename, currypath=()):
  try:
    filename = _filenames.curryfilename(filename)
  except ValueError:
    pass
  return _frontend.searchdirs(filename, currypath or ())

def interface_file(name, searchdirs, frontend=False):
  '''Prefer the versioned copies that travel with ICurry, as typing does.'''
  subdirs = [config.intermediate_subdir(), config.frontend_subdir()]
  if frontend:
    subdirs.reverse()
  finder = InterfaceFinder(searchdirs, subdirs)
  try:
    return finder.filename(name)
  except Flat2ICurryError:
    return None

def digest(name, searchdirs, frontend=False):
  '''SHA-256 of the two labelled interface texts; None if neither exists.'''
  filename = interface_file(name, searchdirs, frontend)
  if filename is None:
    return None
  stem = os.path.splitext(filename)[0]
  result = hashlib.sha256(b'Sprite interface 1\0')
  for suffix in cache.INTERFACE_SUFFIXES:
    result.update(suffix.encode('ascii') + b'\0')
    try:
      path = filename if suffix == '.fint' else stem + suffix
      if path.endswith('.fcy'):
        result.update(b'FlatCurry fallback\0')
      with open(path, 'rb') as stream:
        result.update(b'present\0' + stream.read())
    except FileNotFoundError:
      result.update(b'missing')
    result.update(b'\0')
  return result.hexdigest()

def imports(icyfile):
  '''Read only the ICurry header, without parsing bodies or importing code.'''
  with open(icyfile, encoding='utf-8') as stream:
    text = stream.read()
  match = _HEADER.match(text)
  if match is None:
    raise ValueError('no ICurry import list in %r' % icyfile)
  return re.findall(r'"([^"]*)"', match.group(1))

def snapshot(names, searchdirs, frontend=False):
  return {name: digest(name, searchdirs, frontend) for name in sorted(set(names))}

def encode(imports):
  return json.dumps({'version': VERSION, 'imports': imports}, sort_keys=True)

def decode(text):
  try:
    value = json.loads(text)
    if value['version'] == VERSION and isinstance(value['imports'], dict):
      names = value['imports']
      if all(isinstance(k, str) and (v is None or isinstance(v, str))
             for k, v in names.items()):
        return names
  except (ValueError, KeyError, TypeError):
    pass
  return None

def read(filename):
  try:
    with open(filename, encoding='utf-8') as stream:
      return decode(stream.read())
  except (OSError, UnicodeError):
    return None

def current(recorded, searchdirs):
  return recorded is not None and recorded == snapshot(recorded, searchdirs)

def write(icyfile, currypath=(), frontend=False):
  cache.write_file(icyfile + SUFFIX,
      encode(snapshot(imports(icyfile), search_path(icyfile, currypath), frontend)) + '\n')

def is_current(icyfile, currypath=()):
  recorded = read(icyfile + SUFFIX)
  if recorded is None:
    return False
  try:
    # --tidy can remove ICurry while retaining JSON, objects and provenance.
    if os.path.isfile(icyfile) and set(recorded) != set(imports(icyfile)):
      return False
  except (OSError, ValueError):
    return False
  return current(recorded, search_path(icyfile, currypath))

def object_snapshot(names, searchdirs):
  '''Code generation also reads imported bodies for inlining and aliases.

  Conservatively digest the entire imported ICurry, including private
  symbols. JSON-only installations use the corresponding JSON instead.
  '''
  result = {}
  for name in sorted(set(names)):
    value = hashlib.sha256((digest(name, searchdirs) or 'missing').encode('ascii'))
    parts = name.split('.')
    for directory in searchdirs:
      stem = os.path.join(directory, *parts[:-1], '.curry',
          config.intermediate_subdir(), parts[-1])
      found = False
      for suffix in ('.icy', '.json.z', '.json'):
        try:
          with open(stem + suffix, 'rb') as stream:
            value.update(suffix.encode('ascii') + b'\0' + stream.read())
          found = True
          break
        except FileNotFoundError:
          pass
      if found:
        break
    result[name] = value.hexdigest()
  return result

def objects_current(recorded, searchdirs):
  return recorded is not None and recorded == object_snapshot(recorded, searchdirs)
