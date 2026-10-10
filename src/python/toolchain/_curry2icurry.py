from .. import cache, config
from ..exceptions import CompileError
from . import _filenames, _frontend, _system
from .flat2icurry import bindingopt, flatcurry
from ..utility import curryname, filesys
import logging, os, re

__all__ = [
    'PARSE_LIMIT', 'curry2icurry', 'icurry_is_stale', 'in_system_library'
  , 'pairs_refreshed', 'pairs_served', 'reset_counts', 'rewrite_on_hit'
  , 'translated_before_rewrite'
  ]
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

# The spelling, in a FlatCurry or ICurry text, of the constraint the binding
# optimization writes, and of the Boolean equalities it replaces: the class
# methods of the Prelude and the instance methods of any module
# (bindingopt.is_equality_name).  A FlatCurry file without such a name has
# nothing the pass would replace.
CONSTR_EQ = b'("Prelude","constrEq"'
EQUALITY_NAME = re.compile(
    rb'\("Prelude","(?:==|===|/=|/==)"\)'
    rb'|_impl#(?:==#Prelude\.Eq|===#Prelude\.Data|/=#Prelude\.Eq)#'
  )

# The largest FlatCurry file the check parses, in bytes.  The parse costs
# about 0.3 ms per KB, so a file at the limit costs about 80 ms.  A larger
# file is not judged; a warning says so once per process.
PARSE_LIMIT = 256 * 1024

# The ICurry files this process found stale because they were translated
# before the binding rewrite (translated_before_rewrite), by absolute path;
# those of them the route has translated again since; and those the ICurry
# cache served instead (the FlatCurry file then stays as it was).
# sprite-make reports the counts, and the prepare pass of the test runner
# reads them.
stale_pairs = set()
refreshed_pairs = set()
served_pairs = set()

# The count of the pass over a FlatCurry file, by path, size and mtime: a
# module imported through several plans in one process is parsed once.
_counts = {}

# The files this process has warned about, so a warning comes once.
_warned = set()

def reset_counts():
  '''Forgets the pairs found, made again and served in this process.'''
  stale_pairs.clear()
  refreshed_pairs.clear()
  served_pairs.clear()
  _counts.clear()
  _warned.clear()

def pairs_refreshed():
  '''The number of pre-rewrite pairs the route translated again in this process.'''
  return len(refreshed_pairs)

def pairs_served():
  '''
  The number of pre-rewrite pairs the ICurry cache served in this process.
  The cache wrote the ICurry file, and the route ran the binding
  optimization over the FlatCurry file of the front end
  (``rewrite_on_hit``), so the pair agrees as after a translation.
  '''
  return len(served_pairs)

def _note_refresh(icyfile, served):
  '''Records that the route wrote ``icyfile`` anew, when it was such a pair.'''
  path = os.path.abspath(icyfile)
  if path in stale_pairs:
    (served_pairs if served else refreshed_pairs).add(path)

def _warn_once(fcyfile, message, *args):
  if fcyfile not in _warned:
    _warned.add(fcyfile)
    logger.warning(message, *args)

def _rewrite_count(fcyfile, data, stamp):
  '''
  The number of equalities the pass replaces in the text ``data`` of
  ``fcyfile``, from the memo when the file has the size and time of
  ``stamp``.  None when the pass cannot read the text.
  '''
  key = (fcyfile,) + stamp
  if key not in _counts:
    try:
      _, count = bindingopt.transform_prog(flatcurry.read(data.decode('utf-8')))
    except Exception as err:
      logger.debug('cannot apply the binding optimization to %s: %s', fcyfile, err)
      count = None
    _counts[key] = count
  return _counts[key]

def _writable(fcyfile):
  '''Whether the pass can write ``fcyfile`` again (a temporary file beside it).'''
  return os.access(fcyfile, os.W_OK) \
      and os.access(os.path.dirname(fcyfile), os.W_OK)

def rewrite_on_hit(curryfile):
  '''
  Runs the binding optimization over the FlatCurry file of the front end
  beside ``curryfile`` after a hit of the ICurry cache, as a translation
  does (``_frontend.curry2flat``), so the file agrees with the ICurry file
  the cache wrote.  The cost is a read, and a parse when the text has an
  equality name; the file is written again only when the pass replaces an
  equality, else it keeps its bytes and its time.

  Two files are left as they are.  A file older than the source belongs to
  another version of the source, and a rewrite would make it current by the
  times for the front end; the front end writes it again when it next runs
  for the module.  A file the pass cannot rewrite (unreadable, or in a
  read-only directory) is left with one warning per process that names
  ``sprite-make --rewrite-flat``; the hit stands.  A missing file is
  nothing to rewrite.

  Returns the number of equalities replaced, or None when the file was not
  judged.
  '''
  curryfile = os.path.abspath(curryfile)
  fcyfile = _frontend.flatcurryfile(curryfile)
  if not os.path.isfile(fcyfile) or filesys.newer(curryfile, fcyfile):
    return None
  try:
    with open(fcyfile, 'rb') as stream:
      data = stream.read()
    if EQUALITY_NAME.search(data) is None:
      return 0
    return _frontend.optimize_flatcurry(fcyfile)
  except Exception as err:
    _warn_once(
        fcyfile
      , 'cannot rewrite %s after a hit of the ICurry cache: %s; run '
        'sprite-make --rewrite-flat on the module to make the file agree '
        'with its ICurry'
      , fcyfile, err
      )
    return None

def in_system_library(curryfile):
  '''Tells whether ``curryfile`` lies in the Curry library of the installation.'''
  root = os.path.realpath(config.system_curry_path())
  path = os.path.realpath(curryfile)
  return path == root or path.startswith(root + os.sep)

def translated_before_rewrite(curryfile, icyfile):
  '''
  Tells whether ``icyfile`` was translated from the FlatCurry file of
  ``curryfile`` before the binding optimization rewrote the file (issue
  #101): the file of the front end (``_frontend.flatcurryfile``) holds a
  Boolean equality the pass would replace, and neither it nor the ICurry
  file holds ``constrEq``.  Such a pair comes from a tree made before the
  routes rewrote the file, from the overlay archive of the tests, or from
  a copy of either.  It is current by the file times, and its program
  binds no variable through ``==`` in a guard, where PAKCS binds one.

  The check is cheap on an import.  The FlatCurry file is read: a file
  with ``constrEq`` was rewritten, and a file without an equality name has
  nothing to replace, so both answer at once (a fraction of a
  millisecond).  Else the pass runs over the text in memory and counts (a
  parse: about 0.3 ms per KB, 1 ms for the median module of the test
  corpus, 10 ms for one of 28 KB; the count is kept for the process by
  the size and time of the file, so a module imported through several
  plans pays once).  A file larger than ``PARSE_LIMIT`` is not judged,
  with one warning per process: its parse would cost a second at 840 KB
  at every start.  The ICurry file is read only when the count is not
  zero: a file of the front end can be newer than the ICurry file and
  unrewritten beside an ICurry file of the rewritten program (the PAKCS
  oracle of the tests writes such a file; section 8 of tests/README), and
  that product is right.  Nothing is written.

  Three files are not judged.  A FlatCurry file older than the source
  belongs to another version of the source (a hit in the ICurry cache
  writes no FlatCurry file; it rewrites a current one, ``rewrite_on_hit``)
  and is not the input of the ICurry file.  A module
  of the Curry library of the installation keeps its committed ICurry
  (``in_system_library``); ``make stage`` makes those products.  A
  FlatCurry file the pass cannot write again (the file or its directory is
  read-only) is left as it is, with one warning per process that names
  ``sprite-make --rewrite-flat``: a stale verdict would fail the import
  when the pass writes the file.  A file the pass cannot read is left to
  the translation, which reports it.
  '''
  if in_system_library(curryfile):
    return False
  fcyfile = _frontend.flatcurryfile(curryfile)
  if filesys.newer(curryfile, fcyfile):
    return False
  try:
    with open(fcyfile, 'rb') as stream:
      data = stream.read()
  except OSError:
    return False
  if CONSTR_EQ in data or EQUALITY_NAME.search(data) is None:
    return False
  if len(data) > PARSE_LIMIT:
    _warn_once(
        fcyfile
      , '%s is larger than %d bytes and was not checked against the binding '
        'rewrite; run sprite-make --rewrite-flat on the module once if the '
        'tree predates the rewrite'
      , fcyfile, PARSE_LIMIT
      )
    return False
  try:
    st = os.stat(fcyfile)
  except OSError:
    return False
  if not _rewrite_count(fcyfile, data, (st.st_size, st.st_mtime_ns)):
    return False
  try:
    with open(icyfile, 'rb') as stream:
      if CONSTR_EQ in stream.read():
        return False
  except OSError:
    return False
  if not _writable(fcyfile):
    _warn_once(
        fcyfile
      , '%s was translated before the binding rewrite and cannot be written '
        'again; run sprite-make --rewrite-flat on the module where it is '
        'writable'
      , icyfile
      )
    return False
  return True

def icurry_is_stale(filename, currypath=None):
  '''
  Tells whether an ICurry file must be made again, when its Curry source
  exists, so a conversion can supply the file.  Two states count.  An
  interface file beside it is missing (see ``cache.INTERFACE_SUFFIXES``):
  an ICurry file written before the interface files travelled with it is
  in this state.  Or the file was translated before the binding
  optimization rewrote the FlatCurry file (``translated_before_rewrite``);
  the file is then noted in ``stale_pairs``.  The plan asks this of the
  ``.curry`` input of the step as well; a source is never refused.  The
  search path ``currypath`` is not needed here.
  '''
  if not filename.endswith('.icy'):
    return False
  try:
    curryfile = _filenames.curryfilename(filename)
  except ValueError:
    return False
  if not os.path.isfile(curryfile):
    return False
  if not all(os.path.isfile(cache.interface_filename(filename, suffix))
             for suffix in cache.INTERFACE_SUFFIXES):
    return True
  if translated_before_rewrite(curryfile, filename):
    stale_pairs.add(os.path.abspath(filename))
    return True
  return False

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
  too.  On a hit the cache writes the ICurry file, and the route runs the
  binding optimization over the FlatCurry file of the front end beside the
  source as well (``rewrite_on_hit``), so the pair on disk agrees as after
  a translation; the pair is counted apart (``pairs_served``).

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
        rewrite_on_hit(file_in)
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
      _note_refresh(file_out, served=bool(slot))
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
