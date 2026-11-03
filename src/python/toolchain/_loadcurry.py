from ..icurry import readcurry, types as icurry_types
from .. import config
from . import _curry2icurry, _filenames, _findcurry, _interfaces, _makecurry
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
  if not os.path.isdir(candidate) and candidate.endswith('.curry') \
      and _findcurry._installed_library_file(candidate):
    icyfile = _filenames.icurryfilename(candidate)
    effective = plan.interp.path if imagepath is None else imagepath
    with open(candidate, encoding='utf-8') as stream:
      tokens = list(_filenames._header_tokens(stream.read()))
    imports = [tokens[i + 1] for i, token in enumerate(tokens[:-1])
               if token == 'import']
    outside = any(not _findcurry._installed_library_file(path)
        for dep in imports
        for path in list(_findcurry._modulefiles(plan, dep, effective))[:1])
    directory = os.path.dirname(icyfile)
    while not os.path.exists(directory):
      directory = os.path.dirname(directory)
    writable = os.access(directory, os.W_OK) and bool(os.stat(directory).st_mode & 0o222)
    if (not os.path.isfile(icyfile) or
        _curry2icurry.icurry_is_stale(icyfile, effective)) and (outside or not writable):
      # Translation depends on this interpreter's interfaces. Remake the
      # installed source in a private snapshot, including its interfaces.
      from ..backends.cxx import tiered
      raw = icurry_types.IModule(_filenames.module_name(candidate), [], [], [],
                                 filename=candidate)
      copy, _ = tiered._private_copy(raw)
      _findcurry.record_snapshot(copy, candidate)
      return loadcurry(plan, copy, effective, is_sourcefile=True)
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
