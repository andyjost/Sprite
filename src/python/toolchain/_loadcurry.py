from ..icurry import readcurry, types as icurry_types
from .. import config
from . import _filenames, _findcurry, _makecurry
from ..utility import formatDocstring
import logging, os

__all__ = ['loadcurry', 'loadicurry']
logger = logging.getLogger(__name__)


def loadicurry(filename):
  """Read the translation record into the Python ICurry model."""
  filename = _filenames.icurryfilename(filename)
  try:
    module = readcurry.load(filename)
  except (AttributeError, TypeError) as exc:
    raise ValueError('invalid ICurry text: %s' % filename) from exc
  module.filename = _filenames.sourcefilename(filename)
  return module


@formatDocstring(config.python_package_name())
def loadcurry(plan, name, currypath=None, **kwds):
  """Build and load a module, attaching interpreted code from its image."""
  from ..backends.cxx import image
  search = currypath or plan.interp.path
  imagepath = _findcurry.import_path(plan.interp, _findcurry.imports_path(
      _findcurry.program_path(name, search, **kwds), **kwds))
  candidate = _findcurry.currentfile(plan, name, currypath, **kwds)
  effective = plan.interp.path if imagepath is None else imagepath
  selected = _makecurry.translation_source(plan, candidate, effective)
  if selected != candidate:
    return loadcurry(plan, selected, effective, is_sourcefile=True)
  if plan.interp.flags['interpret'] == 'off' and not os.path.isdir(candidate) \
      and os.path.isfile(_filenames.icurryfilename(candidate)) \
      and not candidate.endswith(config.module_object_suffix()) \
      and os.path.isfile(_filenames.replacesuffix(
          _filenames.icurryfilename(candidate), config.module_object_suffix())) \
      and _findcurry._installed_library_file(_filenames.curryfilename(candidate)) \
      and _filenames.module_name(candidate) not in _findcurry.reserved_module_names():
    # A library importer can be stale for this interpreter's path alone.
    # Compile its snapshot without changing the installation's products.
    from ..backends.cxx import tiered
    raw = loadicurry(_filenames.icurryfilename(candidate))
    copy, _ = tiered._private_copy(raw)
    return loadcurry(plan, copy, search, is_sourcefile=True)
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
    return image.load(plan.interp, _filenames.icurryfilename(candidate), imagepath)
  return plan.interp.load(filename, from_plan=True)
