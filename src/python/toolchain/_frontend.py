'''
The route from Curry to ICurry through the Curry front end.

The front end translates a module and its imports to FlatCurry.  For a
module ``M`` it writes ``M.fcy``, the interface ``M.fint``, and ``M.icurry``
under ``.curry/<subdir>/`` beside the source, where ``<subdir>`` names the
front end (see :func:`config.frontend_subdir`).  The same run writes the
interfaces of the imports beside their sources.  Then
:mod:`curry.toolchain.flat2icurry` translates the FlatCurry to ICurry.  The
``icurry`` program runs the same front end, so its run leaves the same files
(see :func:`interfacefile`).

The command runs in the directory of the module and names the module by its
file name, as ``icurry`` does, so the output lands in the same places.

Between the two steps the binding optimization of
:mod:`curry.toolchain.flat2icurry.bindingopt` rewrites ``M.fcy`` in place
(:func:`optimize_flatcurry`): the Boolean equalities of the conditions
become equational constraints, as the preprocessing of PAKCS makes them
before it compiles a FlatCurry file.  A program that binds free variables
through ``==`` in a guard then runs as it runs under PAKCS.  A file in which
the pass replaces nothing keeps its bytes and its time.  The ``icurry``
route runs the same two steps before the ``icurry`` program, so the file
both routes translate is the optimized one, and the translation itself runs
without the pass (``bindingopt=False``).

A run of the front end on ``M`` compiles more than ``M``: an import whose
files are missing, older than its source, or older than the interface of
one of its own imports is compiled again, and its ``.fcy``, ``.fint`` and
``.icurry`` are written again, in the text of the front end.  The ICurry
of such an import is current by the rule of the toolchain (its source did
not change), so nothing translates it again, and its FlatCurry file would
stay unrewritten beside an ICurry file of the rewritten program.  So the
rewrite covers every FlatCurry file a run wrote (:func:`curry2flat`): the
pass is idempotent, and the pair beside each other agree again.  (Issue
#99; a ``make stage`` that writes the interfaces of the library anew makes
every module of a tree such an import at its next contact.)

An ICurry file translated before the rewrite existed pairs with a FlatCurry
file that still holds the equalities.  Such a pair is stale by the rule of
the toolchain (:func:`_curry2icurry.translated_before_rewrite`), and the
route runs again at the first import of the module.  ``ROUTE_VERSION``
names the steps of this module in the key of the ICurry cache
(:func:`cache.icurry_cache_key`), so an entry of a route without a step is
never served.  A hit of the cache writes the ICurry file and runs the pass
over the FlatCurry file of the front end beside the source as well
(:func:`_curry2icurry.rewrite_on_hit`), so a pair on disk never disagrees
because of the cache.  (Issue #101.)

The front end warns on overlapping rules ("Function f is potentially
non-deterministic due to overlapping rules"), the shape under which
``build 0 = ...; build n = ...`` compiles to a choice with an infinite
alternative.  A run reports those warnings through the log of this module
at the WARNING level, once per module, with the text of the front end
(:func:`report_warnings`); the other warnings of the front end
(non-exhaustive patterns, missing signatures, and so on) stay quiet
(``WARNING_FLAGS``).  The environment variable SPRITE_FRONTEND_WARNINGS set
to ``0`` silences the warnings for a process (:func:`frontend_warnings`);
the test runner, the test library and the benchmark harness set it, so the
suites keep their output.  Issue #96.

The translation runs with ``icurry_compat=False``.  ``icurry`` 3.1.0 loses
the bindings of a let or free declaration under a type annotation at the
root of a rule, and the program then fails at run time.  The port looks
through the annotation here.  Only the oracle tests keep the defect.  Two
probe modules of the oracle hold the construct, and their output differs
from the files ``icurry`` wrote: TypedRoot, and Externals, where
``failed :: Int`` becomes ``IExempt`` instead of a call of ``failed``.  No
other file of the oracle changes.
'''

from .. import config
from . import _system, flat2icurry
from ..exceptions import CompileError
from ..utility import curryname
import logging, os, re, shlex

__all__ = [
    'QUIET_FLAGS', 'ROUTE_VERSION', 'WARNINGS_VARIABLE', 'WARNING_FLAGS'
  , 'command', 'curry2flat', 'curry2icurry', 'flat2icy', 'flatcurry_dirs'
  , 'flatcurryfile', 'frontend_warnings', 'interfacefile'
  , 'optimize_flatcurry', 'report_warnings', 'searchdirs'
  , 'warnings_by_file', 'written_flatcurry'
  ]
logger = logging.getLogger(__name__)

# The version of the steps between the front end and the translation: what
# changes the ICurry of a module without a change to the programs or the
# sources of the route.  It is part of the key of the ICurry cache
# (cache.icurry_cache_key), so a bump makes every entry miss once.  Bump it
# when a step joins the route or changes what it writes.
#   1: the binding optimization rewrites the FlatCurry file in place, the
#      module's own and those of the imports the run compiled again (#85,
#      #99).  The version joined the key with #101.
ROUTE_VERSION = 1

# The options that silence the front end.  They are the ones icurry passes in
# quiet mode.
QUIET_FLAGS = ['--no-verb', '--no-warn', '--no-overlap-warn']

# The options of a run that reports: no status lines, and of the warnings
# the one on overlapping rules alone.  The option -W none turns every
# warning off, and -W overlapping turns that one on again (the front end
# reads the options in order).
WARNING_FLAGS = ['--no-verb', '-W', 'none', '-W', 'overlapping']

# The environment variable that silences the warnings of the front end for
# a process, and the values that mean off (in any case).  Any other value,
# or none, leaves them on; an empty value counts as unset.
WARNINGS_VARIABLE = 'SPRITE_FRONTEND_WARNINGS'
WARNINGS_OFF = frozenset(['0', 'off', 'no', 'false'])

def frontend_warnings():
  '''
  Whether a run of the front end reports its warnings.  SPRITE_FRONTEND_WARNINGS
  set to ``0`` (or ``off``, ``no``, ``false``) says no.
  '''
  value = os.environ.get(WARNINGS_VARIABLE, '')
  return value.strip().lower() not in WARNINGS_OFF

def searchdirs(file_in, currypath):
  '''
  The directories in which the front end and the translation look for
  modules: the directory of ``file_in``, the Curry path, and the system
  library, without repeats.
  '''
  moduledir = os.path.dirname(os.path.abspath(file_in))
  dirs = [moduledir] + curryname.makeCurryPath(currypath)
  dirs.append(config.system_curry_path())
  seen = set()
  unique = []
  for dirname in dirs:
    if dirname not in seen:
      seen.add(dirname)
      unique.append(dirname)
  return unique

def flatcurryfile(file_in):
  '''The FlatCurry file that the front end writes for ``file_in``.'''
  path, name = os.path.split(os.path.abspath(file_in))
  assert name.endswith('.curry')
  return os.path.join(
      path, '.curry', config.frontend_subdir(), name[:-len('.curry')] + '.fcy'
    )

def interfacefile(file_in, suffix):
  '''
  The interface file with ``suffix`` (``.fint`` or ``.icurry``; see
  ``cache.INTERFACE_SUFFIXES``) that the front end writes for ``file_in``,
  beside its FlatCurry file.
  '''
  fcyfile = flatcurryfile(file_in)
  return fcyfile[:-len('.fcy')] + suffix

def flatcurry_dirs(file_in, currypath):
  '''
  The directories into which a run of the front end on ``file_in`` may
  write FlatCurry: ``.curry/<subdir>/`` under each search directory (see
  :func:`searchdirs`), the system library left out.  The products of the
  library belong to the installation, which ``make stage`` makes, and
  their committed ICurry pairs with the text of the front end.
  '''
  system = os.path.abspath(config.system_curry_path())
  return [
      os.path.join(dirname, '.curry', config.frontend_subdir())
          for dirname in searchdirs(file_in, currypath)
          if os.path.abspath(dirname) != system
    ]

def _flatcurry_stamps(dirs):
  '''The FlatCurry files under ``dirs``, each with its size and time.'''
  stamps = {}
  for top in dirs:
    for dirpath, _, files in os.walk(top):
      for name in files:
        if name.endswith('.fcy'):
          path = os.path.join(dirpath, name)
          try:
            st = os.stat(path)
          except OSError:
            continue
          stamps[path] = (st.st_size, st.st_mtime_ns)
  return stamps

def written_flatcurry(before, after):
  '''
  The FlatCurry files of ``after`` that are new or changed since ``before``
  (two results of ``_flatcurry_stamps``), sorted.
  '''
  return sorted(
      path for path, stamp in after.items() if before.get(path) != stamp
    )

def command(file_in, currypath, quiet=False):
  '''
  The front-end command line for the Curry file ``file_in``.  The output
  directory is relative, so it is resolved against the directory of each
  module the front end compiles.  A front end that is not configured raises
  ``CompileError``; both routes need it (see ``_curry2icurry``).  A quiet
  command, and every command while SPRITE_FRONTEND_WARNINGS says off, has
  QUIET_FLAGS; the other commands have WARNING_FLAGS.
  '''
  if config.curry_frontend() is None:
    raise CompileError(
        'the Curry front end is not configured; rerun configure with '
        '--with-curry-frontend'
      )
  name = os.path.basename(file_in)
  assert name.endswith('.curry')
  cmd = [
      config.curry_frontend(), '--flat'
    , '-o', os.path.join('.curry', config.frontend_subdir())
    ]
  if quiet or not frontend_warnings():
    cmd.extend(QUIET_FLAGS)
  else:
    cmd.extend(WARNING_FLAGS)
  cmd.extend(shlex.split(config.frontend_flags()))
  for dirname in searchdirs(file_in, currypath):
    cmd.extend(['-i', dirname])
  cmd.append(name[:-len('.curry')])
  return cmd

def curry2flat(file_in, currypath, quiet=False, rewrite=True):
  '''
  Runs the front end on ``file_in``.  Returns the name of the FlatCurry file.
  A failure of the front end raises ``CompileError`` with its messages; the
  warnings of a run that succeeded are reported (:func:`report_warnings`).

  The run compiles the module and every import whose files are stale for
  the front end (see the module docstring).  With ``rewrite`` the binding
  optimization runs over every FlatCurry file the run wrote: the file of
  ``file_in`` and the files of those imports, so that no file of the front
  end's text is left beside an ICurry file of the rewritten program.  A
  file of an import that cannot be read is reported and left; the module's
  own file raises.  A caller that needs the text of the front end passes
  ``rewrite=False``.
  '''
  cmd = command(file_in, currypath, quiet)
  logger.debug('Command: %s', ' '.join(cmd))
  moduledir = os.path.dirname(os.path.abspath(file_in))
  dirs = flatcurry_dirs(file_in, currypath)
  before = _flatcurry_stamps(dirs)
  stdout, stderr = _system.pexec(cmd, cwd=moduledir, with_stderr=True)
  if stdout:
    logger.debug('Front end output:\n%s', stdout)
  report_warnings(stderr, moduledir)
  fcyfile = flatcurryfile(file_in)
  if not os.path.isfile(fcyfile):
    raise CompileError('the front end did not write %s' % fcyfile)
  if rewrite:
    optimize_flatcurry(fcyfile)
    own = os.path.realpath(fcyfile)
    for written in written_flatcurry(before, _flatcurry_stamps(dirs)):
      if os.path.realpath(written) == own:
        continue
      try:
        optimize_flatcurry(written)
      except Exception as err:
        logger.warning(
            'cannot rewrite %s, which the front end wrote for an import of '
            '%s: %s', written, file_in, err
          )
  return fcyfile

def optimize_flatcurry(fcyfile):
  '''
  Applies the binding optimization to the FlatCurry file in place, as PAKCS
  does before any compiler reads it.  Returns the number of equalities
  replaced; the file is written again only when that is not zero.
  '''
  n = flat2icurry.optimize_file(fcyfile)
  if n:
    logger.debug('Rewrote %s: %d equalities replaced by constrEq', fcyfile, n)
  return n

# A warning of the front end: the file, the position, the word Warning.
# The lines of its text follow, and a blank line ends it.
WARNING_HEAD = re.compile(r'^(?P<file>\S.*?):\d+:\d+(?:-\d+:\d+)? Warning:')

def warnings_by_file(text):
  '''
  Splits the standard error of a run of the front end into its warnings and
  groups them by the source file they name: a list of pairs of the file
  (as the front end spells it) and the text of its warnings, in the order
  of the first warning of each file.  Text of another shape is grouped
  under None.
  '''
  groups = {}
  for block in re.split(r'\n\s*\n', text.strip('\n')):
    if not block.strip():
      continue
    match = WARNING_HEAD.match(block.lstrip('\n'))
    key = match.group('file') if match else None
    groups.setdefault(key, []).append(block.strip('\n'))
  return [(key, '\n\n'.join(blocks)) for key, blocks in groups.items()]

def report_warnings(stderr, moduledir):
  '''
  Reports the warnings of a run of the front end through the log at the
  WARNING level, once per module: the warnings on one source file make one
  record, which names the module and its path and keeps the text of the
  front end.  The front end names a file of the directory of the run
  (``moduledir``) by its name alone.  Text of another shape makes one
  record of its own.  An empty text reports nothing.
  '''
  for filename, text in warnings_by_file(stderr):
    if filename is None:
      logger.warning('the Curry front end says:\n%s', text)
      continue
    path = os.path.normpath(os.path.join(moduledir, filename))
    name = os.path.basename(filename)
    if name.endswith('.curry'):
      name = name[:-len('.curry')]
    logger.warning(
        'the Curry front end warns on module %s (%s):\n%s', name, path, text
      )

def flat2icy(fcyfile, file_out, searchdirs):
  '''
  Translates the FlatCurry file ``fcyfile`` to ICurry and writes ``file_out``.
  The interfaces of the imports are searched under ``searchdirs``.  The
  translation applies no pass of its own: the file is the optimized program
  (see :func:`optimize_flatcurry`).
  '''
  finder = flat2icurry.InterfaceFinder(searchdirs, [config.frontend_subdir()])
  iprog = flat2icurry.translate_file(fcyfile, finder, icurry_compat=False)
  flat2icurry.write_icurry(iprog, file_out)

def curry2icurry(file_in, file_out, currypath, quiet=False):
  '''
  Converts the Curry file ``file_in`` to the ICurry file ``file_out``: the
  front end, the rewrite of its FlatCurry files, and the translation.
  '''
  fcyfile = curry2flat(file_in, currypath, quiet)
  flat2icy(fcyfile, file_out, searchdirs(file_in, currypath))
