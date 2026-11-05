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
  from ._findcurry import _installed_library_file
  if _installed_library_file(filename):
    from ..utility import curryname
    return curryname.makeCurryPath(list(currypath or ()) +
                                  config.system_curry_path().split(os.pathsep))
  return _frontend.searchdirs(filename, currypath or ())

def interface_file(name, searchdirs, frontend=False):
  '''Prefer the versioned copies that travel with ICurry, as typing does.'''
  from ._findcurry import loaded_generation
  generation = loaded_generation(name)
  if generation is not None:
    return generation.name + '.fint' if '.fint' in generation.texts else None
  subdirs = [config.intermediate_subdir(), config.frontend_subdir()]
  from ._findcurry import loaded_source, module_path
  if frontend and loaded_source(name) is None:
    subdirs.reverse()
  finder = InterfaceFinder(module_path(name, searchdirs), subdirs)
  try:
    return finder.filename(name)
  except Flat2ICurryError:
    return None

def digest(name, searchdirs, frontend=False):
  '''SHA-256 of the two labelled interface texts; None if neither exists.'''
  from ._findcurry import loaded_generation
  generation = loaded_generation(name)
  if generation is not None and not any(
      suffix in generation.texts for suffix in cache.INTERFACE_SUFFIXES):
    return None
  filename = interface_file(name, searchdirs, frontend) if generation is None else name + '.fint'
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
      if generation is not None:
        data = generation.texts.get(suffix)
        if data is None:
          raise FileNotFoundError(path)
      else:
        with open(path, 'rb') as stream:
          data = stream.read()
      result.update(b'present\0' + data.replace(b'\r\n', b'\n'))
    except FileNotFoundError:
      result.update(b'missing')
    result.update(b'\0')
  return result.hexdigest()

def imports(icyfile):
  '''Read only the ICurry header, without parsing bodies or importing code.'''
  from ._findcurry import generation_for_source
  generation = generation_for_source(icyfile)
  if generation is not None:
    return [name for name, _ in generation.imports]
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
  from ._findcurry import generation_for_source
  generation = generation_for_source(filename)
  if generation is not None:
    text = generation.texts.get('.icy.imports')
    return decode(text.decode('utf-8')) if text is not None else None
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
    # The import record can outlive a missing translation record.
    if os.path.isfile(icyfile) and set(recorded) != set(imports(icyfile)):
      return False
  except (OSError, ValueError):
    return False
  return current(recorded, search_path(icyfile, currypath))

def object_snapshot(names, searchdirs):
  '''Code generation also reads imported bodies for inlining and aliases.

  Digest the imported image, whose summaries include private symbols,
  together with the typed interfaces.
  '''
  result = {}
  for name in sorted(set(names)):
    value = hashlib.sha256((digest(name, searchdirs) or 'missing').encode('ascii'))
    from ._findcurry import module_path, loaded_generation, loaded_source, _translation_interp
    generation = loaded_generation(name)
    source = loaded_source(name)
    if generation is not None:
      from ..backends.cxx import image
      value.update(image.generation_digest(generation).encode('ascii'))
      result[name] = value.hexdigest()
      continue
    elif source is not None:
      from ..backends.cxx import image
      paths = [image._path(_translation_interp.get(), source)]
    else:
      parts = name.split('.')
      paths = [os.path.join(directory, *parts[:-1], '.curry',
          config.intermediate_subdir(), parts[-1] + suffix)
          for suffix in ('.img', '.icy')
          for directory in module_path(name, searchdirs)]
    for path in paths:
      if path is None:
        continue
      try:
        with open(path, 'rb') as stream:
          value.update(hashlib.sha256(stream.read()).hexdigest().encode('ascii'))
        break
      except FileNotFoundError:
        pass
    result[name] = value.hexdigest()
  return result

def objects_current(recorded, searchdirs):
  return recorded is not None and recorded == object_snapshot(recorded, searchdirs)
