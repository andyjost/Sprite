import threading
from ..utility.locking import synchronized
_rewrite_lock = threading.RLock()
from .. import cache, config
from ..exceptions import CompileError
from . import _filenames, _frontend, _interfaces, _preprocessor, _system
from . import flat2icurry
from .flat2icurry import flatcurry
from ..utility import curryname, filesys
import hashlib, logging, os, re

__all__ = [
    'CONSTR_EQ', 'EQUALITY_NAME', 'PARSE_LIMIT', 'SET0_NAME', 'curry2icurry'
  , 'icurry_is_stale', 'in_system_library', 'pairs_refreshed', 'pairs_served'
  , 'reset_counts', 'rewrite_on_hit', 'translated_before_rewrite'
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
# nothing the pass would replace.  SET0_NAME is the spelling of set0, the
# function the set0 lift lifts (setlift): a FlatCurry file without it has
# nothing the lift would lift.
CONSTR_EQ = b'("Prelude","constrEq"'
EQUALITY_NAME = re.compile(
    rb'\("Prelude","(?:==|===|/=|/==)"\)'
    rb'|_impl#(?:==#Prelude\.Eq|===#Prelude\.Data|/=#Prelude\.Eq)#'
  )
SET0_NAME = b'("Control.SetFunctions","set0")'

# The largest FlatCurry file the check parses, in bytes.  The parse costs
# about 0.3 ms per KB, so a file at the limit costs about 80 ms.  A larger
# file is not judged; a warning says so once per process.
PARSE_LIMIT = 256 * 1024

# The ICurry files this process found stale because they were translated
# before a pass of the rewrite (translated_before_rewrite), by absolute
# path; those of them the route has translated again since; and those the
# ICurry cache served instead (the FlatCurry file then stays as it was).
# sprite-make reports the counts, and the prepare pass of the test runner
# reads them.
stale_pairs = set()
refreshed_pairs = set()
served_pairs = set()

# The counts of the rewrite step over a FlatCurry file, by path, size and
# mtime: a module imported through several plans in one process is parsed
# once.
_counts = {}

# The files this process has warned about, so a warning comes once.
_warned = set()

@synchronized(_rewrite_lock)
def reset_counts():
  '''Forgets the pairs found, made again and served in this process.'''
  stale_pairs.clear()
  refreshed_pairs.clear()
  served_pairs.clear()
  _counts.clear()
  _warned.clear()

@synchronized(_rewrite_lock)
def pairs_refreshed():
  '''The number of pre-rewrite pairs the route translated again in this process.'''
  return len(refreshed_pairs)

@synchronized(_rewrite_lock)
def pairs_served():
  '''
  The number of pre-rewrite pairs the ICurry cache served in this process.
  The cache wrote the ICurry file, and the route ran the rewrite step over
  the FlatCurry file of the front end (``rewrite_on_hit``), so the pair
  agrees as after a translation.
  '''
  return len(served_pairs)

@synchronized(_rewrite_lock)
def _note_refresh(icyfile, served):
  '''Records that the route wrote ``icyfile`` anew, when it was such a pair.'''
  path = os.path.abspath(icyfile)
  if path in stale_pairs:
    (served_pairs if served else refreshed_pairs).add(path)

def _warn_once(fcyfile, message, *args):
  with _rewrite_lock:
    warn = fcyfile not in _warned
    _warned.add(fcyfile)
  if warn:
    logger.warning(message, *args)

@synchronized(_rewrite_lock)
def _rewrite_count(fcyfile, data, stamp):
  '''
  What the rewrite step changes in the text ``data`` of ``fcyfile``: the
  number of equalities the binding optimization replaces, the number of
  calls the set0 lift lifts, and the local names of the lifted functions;
  from the memo when the file has the size and time of ``stamp``.  None
  when the step cannot read the text.
  '''
  key = (fcyfile,) + stamp
  if key not in _counts:
    try:
      prog = flatcurry.read(data.decode('utf-8'))
      lifted, (equalities, calls) = flat2icurry.rewrite_prog(prog)
      names = set(fd.name for fd in prog.functions)
      new = [fd.name[1] for fd in lifted.functions if fd.name not in names]
      result = (equalities, calls, new)
    except Exception as err:
      logger.debug('cannot apply the rewrite step to %s: %s', fcyfile, err)
      result = None
    _counts[key] = result
  return _counts[key]

def _needs_rewrite(data):
  '''
  Which passes of the rewrite step the FlatCurry text ``data`` may need,
  by its spelling alone: the binding optimization when the text has an
  equality name and no ``constrEq`` (a file with ``constrEq`` was
  rewritten by it), the set0 lift when the text names ``set0``.
  '''
  equalities = CONSTR_EQ not in data and EQUALITY_NAME.search(data) is not None
  calls = SET0_NAME in data
  return equalities, calls

def _writable(fcyfile):
  '''Whether the pass can write ``fcyfile`` again (a temporary file beside it).'''
  return os.access(fcyfile, os.W_OK) \
      and os.access(os.path.dirname(fcyfile), os.W_OK)

def rewrite_on_hit(curryfile):
  '''
  Runs the rewrite step (the binding optimization and the set0 lift) over
  the FlatCurry file of the front end beside ``curryfile`` after a hit of
  the ICurry cache, as a translation does (``_frontend.curry2flat``), so
  the file agrees with the ICurry file the cache wrote.  The cost is a
  read, and a parse when the text has an equality name or names ``set0``;
  the file is written again only when a pass changes the program, else it
  keeps its bytes and its time.

  Two files are left as they are.  A file older than the source belongs to
  another version of the source, and a rewrite would make it current by the
  times for the front end; the front end writes it again when it next runs
  for the module.  A file the step cannot rewrite (unreadable, or in a
  read-only directory) is left with one warning per process that names
  ``sprite-make --rewrite-flat``; the hit stands.  A missing file is
  nothing to rewrite.

  Returns the number of changes (equalities replaced and set0 calls
  lifted), or None when the file was not judged.
  '''
  curryfile = os.path.abspath(curryfile)
  fcyfile = _frontend.flatcurryfile(curryfile)
  if not os.path.isfile(fcyfile) or filesys.newer(curryfile, fcyfile):
    return None
  try:
    with open(fcyfile, 'rb') as stream:
      data = stream.read()
    if EQUALITY_NAME.search(data) is None and SET0_NAME not in data:
      return 0
    return sum(_frontend.optimize_flatcurry(fcyfile))
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
  ``curryfile`` before a pass of the rewrite step rewrote the file (issue
  #101; decision D28).  Two rules, one per pass.  The binding optimization:
  the file of the front end (``_frontend.flatcurryfile``) holds a Boolean
  equality the pass would replace, and neither it nor the ICurry file
  holds ``constrEq``.  The set0 lift: the file holds a saturated call of
  ``set0`` whose argument has captured variables, which the pass would
  lift, and the ICurry file lacks the function the lift would make.  Such
  a pair comes from a tree made before the routes rewrote the file with
  that pass, from the overlay archive of the tests, or from a copy of
  either.  It is current by the file times, and its program binds no
  variable through ``==`` in a guard, where PAKCS binds one, or keeps the
  captured variables of a ``set0`` inside the capsule, where the rule of
  the set functions boxes them.

  The check is cheap on an import.  The FlatCurry file is read: a file
  without an equality name and without ``set0`` has nothing to rewrite,
  and a file with ``constrEq`` and without ``set0`` was rewritten, so both
  answer at once (a fraction of a millisecond).  Else the step runs over
  the text in memory and counts (a parse: about 0.3 ms per KB, 1 ms for
  the median module of the test corpus, 10 ms for one of 28 KB; the
  counts are kept for the process by the size and time of the file, so a
  module imported through several plans pays once).  A file larger than
  ``PARSE_LIMIT`` is not judged, with one warning per process: its parse
  would cost a second at 840 KB at every start.  The ICurry file is read
  only when a count is not zero: a file of the front end can be newer
  than the ICurry file and unrewritten beside an ICurry file of the
  rewritten program (the PAKCS oracle of the tests writes such a file;
  section 8 of tests/README), and that product is right.  Nothing is
  written.

  Three files are not judged.  A FlatCurry file older than the source
  belongs to another version of the source (a hit in the ICurry cache
  writes no FlatCurry file; it rewrites a current one, ``rewrite_on_hit``)
  and is not the input of the ICurry file.  A module
  of the Curry library of the installation keeps its committed ICurry
  (``in_system_library``); ``make stage`` makes those products.  A
  FlatCurry file the step cannot write again (the file or its directory is
  read-only) is left as it is, with one warning per process that names
  ``sprite-make --rewrite-flat``: a stale verdict would fail the import
  when the step writes the file.  A file the step cannot read is left to
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
  equalities, calls = _needs_rewrite(data)
  if not (equalities or calls):
    return False
  if len(data) > PARSE_LIMIT:
    _warn_once(
        fcyfile
      , '%s is larger than %d bytes and was not checked against the '
        'rewrite; run sprite-make --rewrite-flat on the module once if the '
        'tree predates the rewrite'
      , fcyfile, PARSE_LIMIT
      )
    return False
  try:
    st = os.stat(fcyfile)
  except OSError:
    return False
  counts = _rewrite_count(fcyfile, data, (st.st_size, st.st_mtime_ns))
  if counts is None:
    return False
  equalities = equalities and counts[0] > 0
  calls = calls and counts[1] > 0
  if not (equalities or calls):
    return False
  try:
    with open(icyfile, 'rb') as stream:
      icy = stream.read()
  except OSError:
    return False
  if equalities and CONSTR_EQ in icy:
    equalities = False
  if calls and all(('"%s"' % name).encode('utf-8') in icy for name in counts[2]):
    calls = False
  if not (equalities or calls):
    return False
  if not _writable(fcyfile):
    _warn_once(
        fcyfile
      , '%s was translated before the rewrite and cannot be written again; '
        'run sprite-make --rewrite-flat on the module where it is writable'
      , icyfile
      )
    return False
  return True

def source_digest(filename):
  with open(filename, 'rb') as stream:
    return hashlib.sha256(stream.read()).hexdigest()


def source_matches(curryfile, icyfile):
  """Whether the product records exactly the current Curry source text."""
  try:
    with open(icyfile + '.source', encoding='ascii') as stream:
      recorded = stream.read().strip()
    return recorded == source_digest(curryfile)
  except OSError:
    return False


def source_changed(curryfile, icyfile):
  """Compare the source with the text the ICurry was made from."""
  if in_system_library(curryfile) or not os.path.isfile(curryfile):
    return False
  return not source_matches(curryfile, icyfile)


def icurry_is_stale(filename, currypath=None):
  '''
  Tells whether an ICurry file must be made again, when its Curry source
  exists, so a conversion can supply the file.  Two states count.  An
  interface file beside it is missing (see ``cache.INTERFACE_SUFFIXES``):
  an ICurry file written before the interface files travelled with it is
  in this state.  Or the file was translated before a pass of the rewrite
  step rewrote the FlatCurry file (``translated_before_rewrite``); the
  file is then noted in ``stale_pairs``.  The plan asks this of the
  ``.curry`` input of the step as well; a source is never refused.  The
  search path ``currypath`` selects the imported interfaces recorded in
  ``M.icy.imports``; a missing record or a changed interface is stale too.
  '''
  if not filename.endswith('.icy'):
    return False
  try:
    curryfile = _filenames.curryfilename(filename)
  except ValueError:
    return False
  if not os.path.isfile(curryfile):
    return False
  if source_changed(curryfile, filename):
    return True
  if not all(os.path.isfile(cache.interface_filename(filename, suffix))
             for suffix in cache.INTERFACE_SUFFIXES):
    return True
  if translated_before_rewrite(curryfile, filename):
    stale_pairs.add(os.path.abspath(filename))
    return True
  return not _interfaces.is_current(filename, currypath)

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
  rewrite step (the binding optimization and the set0 lift) in place to
  every FlatCurry file the run wrote, the module's and those of the
  imports the run compiled again, as PAKCS applies its preprocessing
  before any compiler reads a file; the ``icurry`` program then runs the
  front end again, which finds its files current and leaves the rewritten
  ones as they are, and translates the rewritten program.  So the two
  routes write the same ICurry for a module with a required Boolean
  equality or a ``set0`` over captured variables.

  The cache (see ``curry.cache``) is keyed by the source text and by the
  route, so an entry written by one route is never served to the other.  An
  error the front end reported about the program is taken from the cache
  too.  On a hit the cache writes the ICurry file, and the route runs the
  rewrite step over the FlatCurry file of the front end beside the source
  as well (``rewrite_on_hit``), so the pair on disk agrees as after a
  translation; the pair is counted apart (``pairs_served``).

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
                         and cache.icurry_cache_enabled() and not _frontend.frontend_warnings()
    self.tool = config.curry2icurry_tool(kwds.get('curry2icurry'))

  @_system.updateCheck
  def convert(self, file_in, currypath):
    digest = source_digest(file_in)
    currypath = curryname.makeCurryPath(currypath)
    # Both translators read the interfaces selected by the front end,
    # including those of Sprite's shipped library.
    with _system.bindCurryPath(_frontend.searchdirs(file_in, currypath)):
      file_out = _filenames.icurryfilename(file_in)
      cmd = self.command(file_in, file_out, currypath)
      if source_changed(file_in, file_out) or (
          not in_system_library(file_in)
          and not _interfaces.is_current(file_out, currypath)):
        # Force elaboration against the new imports even when restored
        # interface timestamps are older than the module's FlatCurry.
        # A cache hit must not leave an interface of the old text behind.
        # The file of a module of the shipped library is the stage's and
        # stays, as its source digest is never compared: the front end
        # reads it for every program, and a cache hit would not remake it.
        try:
          os.unlink(_frontend.flatcurryfile(file_in))
        except FileNotFoundError:
          pass
      slot = None
      if self.use_cache:
        slot = cache.Curry2ICurryCache.Slot(
            file_in, file_out, currypath, self.OPTIONS, tool=self.tool
          )
      if slot:
        logger.debug('Found %s in the cache', file_out)
        rewrite_on_hit(file_in)
      elif (slot is not None and slot.error is not None
            and not _preprocessor.preprocessor(file_in)):
        logger.debug('Found the error of %s in the cache', file_in)
        raise CompileError(slot.error, report=slot.error)
      else:
        # A cached preprocessor failure may be resolved by a change to
        # PATH. Retry it; successful cached products remain usable.
        logger.debug('Using CURRYPATH %s', ':'.join(currypath))
        _system.makeOutputDir(file_out)
        try:
          with filesys.remove_file_on_error(file_out):
            if self.tool == 'icurry':
              _frontend.curry2flat(file_in, currypath, self.quiet)
              if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Command: %s', ' '.join(cmd))
              _system.pexec(cmd)
            else:
              _frontend.curry2icurry(file_in, file_out, currypath, self.quiet)
            if logger.isEnabledFor(logging.INFO):
              logger.info('module %s: ICurry written (%s)',
                  _filenames.logging_module_name(file_in), file_out)
            self.place_interfaces(file_in, file_out)
            _interfaces.write(file_out, currypath, frontend=True)
        except CompileError as err:
          if slot is not None and not _preprocessor.missing(file_in):
            slot.update_error(err)
          raise
        if slot is not None:
          slot.update()
      if not in_system_library(file_in):
        cache.write_file(file_out + '.source', digest.encode('ascii'))
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
            'icurry is not configured; set CMake WITH_ICURRY, or '
            'set SPRITE_CURRY2ICURRY=frontend to use the Curry front end'
          )
      if config.curry_frontend() is None:
        raise CompileError(
            'the icurry route needs the Curry front end as well: it runs the '
            'front end first and rewrites its FlatCurry file before icurry '
            'reads it; set SPRITE_FRONTEND or put pakcs-frontend on PATH'
          )
      # '--optvardecls' try to use this
      cmd = [icurry] + list(self.OPTIONS)
      if self.quiet:
        cmd.append('-q')
      cmd += ['-o', file_out, file_in]
      return cmd
    else:
      return _frontend.command(file_in, currypath, self.quiet)
