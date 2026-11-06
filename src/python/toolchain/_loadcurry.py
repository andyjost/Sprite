from ..icurry import readcurry, types as icurry_types
from .. import config
from . import _filenames, _findcurry, _makecurry, _curry2icurry
from ..utility import formatDocstring
import hashlib, io, logging, os

__all__ = ['loadcurry', 'loadicurry']
logger = logging.getLogger(__name__)


def loadicurry(filename):
  """Read the translation record into the Python ICurry model."""
  filename = _filenames.icurryfilename(filename)
  source = _filenames.sourcefilename(filename)
  generation = _findcurry.generation_for_source(source)
  if generation is not None:
    _findcurry.verify_product(generation, filename)
  _findcurry.verify_loaded_product(filename)
  try:
    with open(filename, 'rb') as stream:
      data = stream.read()
    module = readcurry.load(io.StringIO(data.decode('utf-8')))
  except (AttributeError, TypeError) as exc:
    raise ValueError('invalid ICurry text: %s' % filename) from exc
  module.filename = source
  module._source_digest = hashlib.sha256(data).hexdigest()
  return module


@_curry2icurry.with_completion_checks
@_findcurry.with_resolution
@formatDocstring(config.python_package_name())
def loadcurry(plan, name, currypath=None, **kwds):
  """Build and load a module, attaching interpreted code from its image."""
  from ..backends.cxx import image
  search = currypath or plan.interp.path
  imagepath = _findcurry.import_path(plan.interp, _findcurry.imports_path(
      _findcurry.program_path(name, search, **kwds), **kwds))
  candidate = _findcurry.currentfile(plan, name, currypath, **kwds)
  effective = plan.interp.path if imagepath is None else imagepath
  if plan.interp.flags['interpret'] != 'off' and not os.path.isdir(candidate) \
      and not candidate.endswith(config.module_object_suffix()):
    icyfile = _filenames.icurryfilename(candidate)
    if os.path.isfile(icyfile) and not plan.is_stale(icyfile, imagepath):
      module = image.current(plan.interp, icyfile, imagepath)
      if module is not None:
        return module
      if not image.writable(icyfile):
        return image.load(plan.interp, icyfile, imagepath)
  filename = _makecurry.makecurry(plan, name, currypath,
      **dict(kwds, image_importing=True))
  logger.debug('Found module %s at %s', name, filename)
  if os.path.isdir(filename):
    package = icurry_types.IPackage(name)
    package.filename = filename
    return package
  if filename.endswith(('.img', '.icy', '.cpp')):
    translation = (filename.original_icyfile
        if isinstance(filename, _filenames.ImageProduct)
        else _filenames.icurryfilename(filename))
    return image.load(plan.interp, translation, imagepath)
  return plan.interp._load(filename, from_plan=True)
