from .. import cache, config
from ..exceptions import CompileError
from . import _filenames, _system
from ..utility import curryname, filesys
import logging, os

__all__ = ['curry2icurry']
logger = logging.getLogger(__name__)

def curry2icurry(curryfile, currypath, **kwds):
  '''
  Calls "icurry" to produce an ICurry file from a Curry file.

  Args:
    curryfile:
        The name of the Curry file to convert.
    currypath:
        The list of Curry code search paths.
    **kwds:
        Additional keywords.  See :class:`Curry2ICurryConverter`.

  Returns:
    The ICurry file name.
  '''
  return Curry2ICurryConverter(**kwds).convert(curryfile, currypath)

class Curry2ICurryConverter(object):
  '''
  Runs the Curry front end, or takes its output from the ICurry cache.  An
  error the front end reported about the program is taken from the cache too.

  Keywords:
    quiet:
        Passes -q to the front end.
    use_cache:
        Whether to use the ICurry cache (see ``curry.cache``).  True by
        default.  The cache must also be enabled
        (``cache.icurry_cache_enabled``).
  '''
  # The options of the front end that change its output.  They are part of
  # the cache key.  The quiet option is not one of them.
  OPTIONS = ()

  def __init__(self, **kwds):
    self.quiet = kwds.get('quiet', False)
    self.use_cache = bool(kwds.get('use_cache', True)) \
                         and cache.icurry_cache_enabled()

  @_system.updateCheck
  def convert(self, file_in, currypath):
    currypath = curryname.makeCurryPath(currypath)
    with _system.bindCurryPath(currypath):
      file_out = _filenames.icurryfilename(file_in)
      # '--optvardecls' try to use this
      cmd = [config.icurry_tool()] + list(self.OPTIONS)
      if self.quiet:
        cmd.append('-q')
      cmd += ['-o', file_out, file_in]
      slot = None
      if self.use_cache:
        slot = cache.Curry2ICurryCache.Slot(
            file_in, file_out, currypath, self.OPTIONS
          )
      if slot:
        logger.debug('Found %s in the cache', file_out)
      elif slot is not None and slot.error is not None:
        logger.debug('Found the error of %s in the cache', file_in)
        raise CompileError(_system.pexec_message(cmd, slot.error))
      else:
        logger.debug('Using CURRYPATH %s', os.environ['CURRYPATH'])
        _system.makeOutputDir(file_out)
        logger.debug('Command: %s', ' '.join(cmd))
        try:
          with filesys.remove_file_on_error(file_out):
            _system.pexec(cmd)
        except CompileError as err:
          if slot is not None:
            slot.update_error(err)
          raise
        if slot is not None:
          slot.update()
      return file_out
