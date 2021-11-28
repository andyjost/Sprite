from ..icurry import json as icurry_json, types as icurry_types
from .. import cache, config
from . import _filenames, _makecurry
from ..utility import formatDocstring
import logging, os, zlib

__all__ = ['loadicurry', 'loadjson']

logger = logging.getLogger(__name__)

@formatDocstring(__package__[:__package__.find('.')])
def loadicurry(name, currypath=None, **kwds):
  '''
  Loads into Python the ICurry for a Curry module or source file, building if
  necessary.

  Parameters:
  -----------
  ``name``
      The source file, module, or package name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').  By default,
      ``{0}.path`` is used.
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
    package = icurry_types.IPackage(name)
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
  json = json.decode('utf-8')
  icur = icurry_json.loads(json)
  icur.filename = _filenames.curryfilename(jsonfile)
  if cached is not None:
    cached.update(icur)
  return icur

