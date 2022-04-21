from ..icurry import json as icurry_json, types as icurry_types
from .. import cache, config, exceptions
from . import _filenames, _makecurry
from ..utility import formatDocstring
import logging, os, zlib

__all__ = ['loadcurry', 'loadjson']

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
  elif filename.endswith('.py'):
    return plan.interp.load(filename)
  else:
    raise exceptions.PrerequisiteError('unknown file type: %r' % filename)

def loadjson(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  assert os.path.exists(jsonfile)
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
