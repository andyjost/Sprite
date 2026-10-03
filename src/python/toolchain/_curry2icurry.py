from .. import cache, config
from ..exceptions import CompileError
from . import _filenames, _frontend, _system
from ..utility import curryname, filesys
import logging, os

__all__ = ['curry2icurry']
logger = logging.getLogger(__name__)

def curry2icurry(curryfile, currypath, **kwds):
  '''
  Produces an ICurry file from a Curry file.

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
  Converts Curry to ICurry, or takes the result from the ICurry cache.

  Two routes do the conversion.  ``frontend`` runs the Curry front end to
  produce FlatCurry and then the built-in translation
  :mod:`curry.toolchain.flat2icurry`.  ``icurry`` runs the ``icurry``
  program.  :func:`config.curry2icurry_tool` picks the route.

  The cache (see ``curry.cache``) is keyed by the source text and by the
  route, so an entry written by one route is never served to the other.  An
  error the front end reported about the program is taken from the cache
  too.

  Keywords:
    quiet:
        Whether to silence the messages of the tool.
    use_cache:
        Whether to use the ICurry cache.  True by default.  The cache must
        also be enabled (``cache.icurry_cache_enabled``).
    curry2icurry:
        The name of the route, ``frontend`` or ``icurry``.  The default comes
        from the environment and the configuration.
  '''
  # The options of the icurry program that change its output.  They are part
  # of the cache key.  The quiet option is not one of them.  The flags of the
  # Curry front end reach the key through the digest of the route (see
  # ``cache.frontend_digest``).
  OPTIONS = ()

  def __init__(self, **kwds):
    self.quiet = kwds.get('quiet', False)
    self.use_cache = bool(kwds.get('use_cache', True)) \
                         and cache.icurry_cache_enabled()
    self.tool = config.curry2icurry_tool(kwds.get('curry2icurry'))

  @_system.updateCheck
  def convert(self, file_in, currypath):
    currypath = curryname.makeCurryPath(currypath)
    with _system.bindCurryPath(currypath):
      file_out = _filenames.icurryfilename(file_in)
      cmd = self.command(file_in, file_out, currypath)
      slot = None
      if self.use_cache:
        slot = cache.Curry2ICurryCache.Slot(
            file_in, file_out, currypath, self.OPTIONS, tool=self.tool
          )
      if slot:
        logger.debug('Found %s in the cache', file_out)
      elif slot is not None and slot.error is not None:
        logger.debug('Found the error of %s in the cache', file_in)
        raise CompileError(_system.pexec_message(cmd, slot.error))
      else:
        logger.debug('Using CURRYPATH %s', os.environ['CURRYPATH'])
        _system.makeOutputDir(file_out)
        try:
          with filesys.remove_file_on_error(file_out):
            if self.tool == 'icurry':
              logger.debug('Command: %s', ' '.join(cmd))
              _system.pexec(cmd)
            else:
              _frontend.curry2icurry(file_in, file_out, currypath, self.quiet)
        except CompileError as err:
          if slot is not None:
            slot.update_error(err)
          raise
        if slot is not None:
          slot.update()
      return file_out

  def command(self, file_in, file_out, currypath):
    '''
    The command line of the route: the icurry program, or the Curry front
    end, which the built-in translation follows in this process.  A message
    about a failure names this command.  A route whose program is not
    configured raises CompileError.
    '''
    if self.tool == 'icurry':
      icurry = config.icurry_tool()
      if icurry is None:
        raise CompileError(
            'icurry is not configured; rerun configure with --with-icurry, or '
            'set SPRITE_CURRY2ICURRY=frontend to use the Curry front end'
          )
      # '--optvardecls' try to use this
      cmd = [icurry] + list(self.OPTIONS)
      if self.quiet:
        cmd.append('-q')
      cmd += ['-o', file_out, file_in]
      return cmd
    else:
      return _frontend.command(file_in, currypath, self.quiet)
