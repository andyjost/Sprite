from .. import cache, config
from ..exceptions import CompileError
from . import _filenames, _frontend, _system
from ..utility import curryname, filesys
import logging, os

__all__ = ['curry2icurry', 'icurry_is_stale']
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

def icurry_is_stale(filename):
  '''
  Tells whether an ICurry file must be made again: an interface file beside
  it is missing (see ``cache.INTERFACE_SUFFIXES``), and its Curry source
  exists, so a conversion can supply the file.  An ICurry file written before
  the interface files travelled with it is in this state.  The plan asks
  this of the ``.curry`` input of the step as well; a source is never
  refused.
  '''
  if not filename.endswith('.icy'):
    return False
  if all(os.path.isfile(cache.interface_filename(filename, suffix))
         for suffix in cache.INTERFACE_SUFFIXES):
    return False
  try:
    curryfile = _filenames.curryfilename(filename)
  except ValueError:
    return False
  return os.path.isfile(curryfile)

# The plan asks the step that made an .icy file whether the file is usable;
# see ``plans.Plan.is_stale``.
curry2icurry.is_stale = icurry_is_stale

class Curry2ICurryConverter(object):
  '''
  Converts Curry to ICurry, or takes the result from the ICurry cache.

  Two routes do the conversion.  ``frontend`` runs the Curry front end to
  produce FlatCurry and then the built-in translation
  :mod:`curry.toolchain.flat2icurry`.  ``icurry`` runs the ``icurry``
  program.  :func:`config.curry2icurry_tool` picks the route.  Both routes
  run the front end first (``_frontend.curry2flat``), which applies the
  binding optimization in place to every FlatCurry file the run wrote, the
  module's and those of the imports the run compiled again, as PAKCS does
  before any compiler reads a file; the ``icurry`` program then runs the
  front end again, which finds its files current and leaves the rewritten
  ones as they are, and translates the optimized program.  So the two
  routes write the same ICurry for a module with a required Boolean
  equality.

  The cache (see ``curry.cache``) is keyed by the source text and by the
  route, so an entry written by one route is never served to the other.  An
  error the front end reported about the program is taken from the cache
  too.

  The two interface files of the module travel with its ICurry (see
  ``cache.INTERFACE_SUFFIXES``).  Both routes run the front end, which writes
  them beside the FlatCurry.  On a miss ``convert`` copies them to the places
  beside the ICurry file (``place_interfaces``); on a hit the cache writes
  them there.  Readers of the types use those copies only.

  Keywords:
    quiet:
        Whether to silence the messages of the tool, the warnings of the
        front end among them (``_frontend.report_warnings``; the
        environment variable SPRITE_FRONTEND_WARNINGS silences those for a
        whole process).
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
              _frontend.curry2flat(file_in, currypath, self.quiet)
              logger.debug('Command: %s', ' '.join(cmd))
              _system.pexec(cmd)
            else:
              _frontend.curry2icurry(file_in, file_out, currypath, self.quiet)
            self.place_interfaces(file_in, file_out)
        except CompileError as err:
          if slot is not None:
            slot.update_error(err)
          raise
        if slot is not None:
          slot.update()
      return file_out

  def place_interfaces(self, file_in, file_out):
    '''
    Copies the interface files the front end wrote for ``file_in`` (see
    ``_frontend.interfacefile``) to the places beside ``file_out`` (see
    ``cache.interface_filename``).  When the route left no such file, an
    empty file takes its place, with a warning: the module then has no types,
    and the empty file keeps the ICurry from being made again for it (see
    ``icurry_is_stale``).
    '''
    for suffix in cache.INTERFACE_SUFFIXES:
      source = _frontend.interfacefile(file_in, suffix)
      try:
        with open(source, 'rb') as stream:
          content = stream.read()
      except FileNotFoundError:
        logger.warning(
            'the %s route left no %s for %s; the module has no types'
          , self.tool, os.path.basename(source), file_in
          )
        content = b''
      cache.write_file(cache.interface_filename(file_out, suffix), content)

  def command(self, file_in, file_out, currypath):
    '''
    The command line of the route: the icurry program, or the Curry front
    end, which the built-in translation follows in this process.  A message
    about a failure names this command.  A route whose program is not
    configured raises CompileError.  The ``icurry`` route needs the front
    end as well, which it runs first (see ``convert``); a missing one is
    reported here, before any program runs.
    '''
    if self.tool == 'icurry':
      icurry = config.icurry_tool()
      if icurry is None:
        raise CompileError(
            'icurry is not configured; rerun configure with --with-icurry, or '
            'set SPRITE_CURRY2ICURRY=frontend to use the Curry front end'
          )
      if config.curry_frontend() is None:
        raise CompileError(
            'the icurry route needs the Curry front end as well: it runs the '
            'front end first and rewrites its FlatCurry file before icurry '
            'reads it; rerun configure with --with-curry-frontend'
          )
      # '--optvardecls' try to use this
      cmd = [icurry] + list(self.OPTIONS)
      if self.quiet:
        cmd.append('-q')
      cmd += ['-o', file_out, file_in]
      return cmd
    else:
      return _frontend.command(file_in, currypath, self.quiet)
