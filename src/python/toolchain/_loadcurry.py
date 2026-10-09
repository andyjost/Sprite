from ..icurry import json as icurry_json, types as icurry_types
from .. import cache, config, exceptions
from . import _filenames, _makecurry
from ..utility import formatDocstring
import logging, os, zlib

__all__ = ['json_beside', 'loadcurry', 'loadjson']

logger = logging.getLogger(__name__)

@formatDocstring(config.python_package_name())
def loadcurry(plan, name, currypath=None, **kwds):
  '''
  Builds (if necessary) and loads the named module.

  Args:
    plan:
        The compile plan.
    name:
        The source file, module, or package name.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').  By
        default, ``{0}.path`` is used.
    is_sourcefile:
        If true, the name arguments is interpreted as a source file.
        Otherwise, it is interpreted as a module name.

  Raises:
    ModuleLookupError: the module was not found.

  Returns:
    A Python object containing the ICurry for the given name.
  '''
  filename = _makecurry.makecurry(plan, name, currypath, **kwds)
  logger.debug('Found module %s at %s', name, filename)
  if os.path.isdir(filename):
    package = icurry_types.IPackage(name)
    package.filename = filename
    return package
  elif filename.endswith('.json') or filename.endswith('.json.z'):
    return loadjson(filename)
  elif filename.endswith('.cpp'):
    # The plan ended at a generated file (Cpp2So.ends_plan of the C++
    # backend, under tiered execution): the module is interpreted from the
    # JSON beside it.
    return loadjson(json_beside(filename))
  else:
    # The plan's own route: the object is the current product of an import,
    # not a file the user named (loader.load_module of the C++ backend).
    return plan.interp.load(filename, from_plan=True)

def json_beside(filename):
  '''
  The ICurry-JSON file beside a generated file (.cpp, .py): the zipped one
  when it exists, else the plain one, else None.
  '''
  stem = os.path.splitext(filename)[0]
  for suffix in '.json.z', '.json':
    candidate = stem + suffix
    if os.path.isfile(candidate):
      return candidate
  return None

def loadjson(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  assert os.path.exists(jsonfile)
  assert jsonfile.endswith('.json') or jsonfile.endswith('.json.z')
  if config.enable_parsed_json_cache():
    cached = cache.ParsedJsonCache.Slot(jsonfile)
  else:
    cached = None
  if cached:
    logger.info('Loading cached ICurry-JSON for %s', jsonfile)
    return cached.icur
  else:
    logger.info('Reading ICurry-JSON from %s', jsonfile)
  if jsonfile.endswith('.z'):
    with open(jsonfile, 'rb') as istream:
      json = istream.read()
    json = zlib.decompress(json)
  else:
    with open(jsonfile) as istream:
      json = istream.read()
  icur = icurry_json.loads(json)
  icur.filename = _filenames.curryfilename(jsonfile)
  if cached is not None:
    cached.update(icur)
  return icur

