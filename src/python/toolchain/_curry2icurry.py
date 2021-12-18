from .. import cache, config
from . import _filenames, _system
from ..utility.binding import binding
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
  -------
  The ICurry file name.
  '''
  return Curry2ICurryConverter(**kwds).convert(curryfile, currypath)

class Curry2ICurryConverter(object):
  def __init__(self, **kwds):
    self.quiet      = kwds.get('quiet', False)
    self.use_cache  = kwds.get('use_cache', True) \
                          if config.enable_icurry_cache() else False

  @_system.updateCheck
  def convert(self, file_in, currypath):
    with _system.bindCurryPath(currypath):
      file_out = _filenames.icurryfilename(file_in)
      cached = self.use_cache and \
          cache.Curry2ICurryCache.Slot(file_in, file_out)
      if not cached:
        logger.debug('Using CURRYPATH %s', os.environ['CURRYPATH'])
        _system.makeOutputDir(file_out)
        # '--optvardecls' try to use this
        cmd = [config.icurry_tool(), '-o', file_out, file_in]
        if self.quiet:
          cmd.insert(1, '-q')
        logger.debug('Command: %s', ' '.join(cmd))
        with filesys.remove_file_on_error(file_out):
          _system.popen(cmd)
        if self.use_cache:
          cached.update()
      else:
        logger.debug('Found %s in the cache', file_out)
      return file_out

