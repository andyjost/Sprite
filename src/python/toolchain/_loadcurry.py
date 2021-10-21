from ..icurry import json as icurry_json, types as icurry_types
from .. import cache
from . import _filenames, _makecurry
import logging, os, zlib

__all__ = ['loadicurry', 'loadjson']

logger = logging.getLogger(__name__)

def loadicurry(name, currypath, **kwds):
  '''
  Loads into Python the ICurry for a Curry module or source file, building if
  necessary.

  Parameters:
  -----------
  ``name``
      The source file, module, or package name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.

  Raises:
  -------
  ``ModuleLookupError`` if the module is not found.

  Returns:
  --------
  A Python object containing the ICurry for the given name.
  '''
  filename = _makecurry.makecurry(name, currypath, **kwds)
  logger.debug('Found module %s at %s', name, filename)
  if os.path.isdir(filename):
    package = icurry_types.IPackage(name, [])
    package.filename = filename
    return package
  else:
    return loadjson(filename)

def loadjson(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  assert os.path.exists(jsonfile)
  cached = cache.ParsedJsonCache.Slot(jsonfile)
  if cached:
    logger.info('Loading cached ICurry-JSON for %s', jsonfile)
    return cached.icur
  else:
    logger.info('Reading ICurry-JSON from %s', jsonfile)
  if jsonfile.endswith('.z'):
    json = open(jsonfile, 'rb').read()
    json = zlib.decompress(json)
  else:
    json = open(jsonfile).read()
  icur = icurry_json.parse(json)
  icur.filename = _filenames.curryfilename(jsonfile)
  cached.update(icur)
  return icur

