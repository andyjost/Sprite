from . import _findcurry, _curry2icurry, _icurry2json
from ..utility import formatDocstring
import logging, os, shutil

__all__ = ['makecurry']
logger = logging.getLogger(__name__)

@formatDocstring(__package__[:__package__.find('.')])
def makecurry(name, currypath=None, **kwds):
  '''
  Run the build toolchain for a Curry target.

  Following this, the specified file is up-to-date and can be loaded.  This
  function uses the timestamps of prerequisite files to avoid repeating steps.

  Parameters:
  -----------
  ``name``
      The module or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').  By default,
      ``{0}.path`` is used.
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.
  ``kwds``
      See documentation for sprite-make.

  Returns:
  --------
  The JSON file name if json=True (the default) was supplied, else None.
  '''
  if currypath is None:
    from .. import path as currypath
  do_json = kwds.pop('json', True)
  do_icy = do_json or kwds.pop('icy', True)
  do_tidy = kwds.pop('tidy', False)
  currentfile = None
  intermediates = []
  try:
    if do_icy:
      currentfile = _findcurry.currentfile(
          name, currypath, json=do_json, **kwds
        )
      if os.path.isdir(currentfile):
        return currentfile
      # suffix = .curry, .icy, .json, or .json.z.
      if currentfile.endswith('.curry'):
        currentfile = _curry2icurry.curry2icurry(currentfile, currypath, **kwds)
        assert currentfile.endswith('.icy')
        if do_json:
          intermediates.append(currentfile)
      # suffix = .icy, .json, or .json.z.
      if do_json:
        currentfile = _icurry2json.icurry2json(currentfile, currypath, **kwds)
        # suffix = .json, or .json.z.
        return currentfile
  finally:
    # Move the file if "output" was specified.
    output = kwds.pop('output', None)
    if output is not None and currentfile is not None and \
        not (os.path.exists(output) and os.path.samefile(output, currentfile)):
      shutil.copy(currentfile, output)
      if currentfile not in intermediates:
        intermediates.append(currentfile)
    # Remove intermediates.
    if do_tidy:
      for intermediate in intermediates:
        logger.debug('Removing intermediate %r', intermediate)
        os.unlink(intermediate)

