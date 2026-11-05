'''
The route from Curry to ICurry through the Curry front end.

The front end translates a module and its imports to FlatCurry.  For a
module ``M`` it writes ``M.fcy``, the interface ``M.fint``, and ``M.icurry``
under ``.curry/<subdir>/`` at the hierarchy root, where ``<subdir>`` names the
front end (see :func:`config.frontend_subdir`).  Qualified names supply the
subdirectories below that product directory. The same run writes the
interfaces of the imports under their hierarchy roots. Then
:mod:`curry.toolchain.flat2icurry` translates the FlatCurry to ICurry.  The
``icurry`` program runs the same front end, so its run leaves the same files
(see :func:`interfacefile`).

The front end normally runs in an empty directory with an absolute source
input, so its implicit current-directory search cannot shadow the effective
path. Misplaced explicit files retain their physical output layout.
Translations outside the installation search private generations newest first
and replace installed source roots with a temporary interface-only view. The
external translator's source-first reader also gets private source copies.
Dependencies
requiring private destinations are elaborated before the requested module;
the external front end can never rebuild an installed source through that
view. In-place installed translations keep the ordinary search path.

Between the two steps the rewrite step of the routes
(:func:`curry.toolchain.flat2icurry.rewrite_file`) rewrites ``M.fcy`` in
place (:func:`optimize_flatcurry`), with two passes.  The binding optimization
(:mod:`curry.toolchain.flat2icurry.bindingopt`) turns the Boolean
equalities of the conditions into equational constraints, as the
preprocessing of PAKCS makes them before it compiles a FlatCurry file; a
program that binds free variables through ``==`` in a guard then runs as
it runs under PAKCS.  The set0 lift
(:mod:`curry.toolchain.flat2icurry.setlift`) turns ``set0 e`` over the
captured variables of ``e`` into ``setk L xs``, so the captured variables
are arguments of the capsule, boxed at the entry (decision D28 of
2026-10-12).  A file in which neither pass changes anything keeps its
bytes and its time.  The ``icurry`` route runs the same two steps before
the ``icurry`` program, so the file both routes translate is the rewritten
one, and the translation itself runs without the step (``rewrite=False``).

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

An ICurry file translated before a pass of the rewrite existed pairs with
a FlatCurry file that still holds the equalities, or the unlifted ``set0``
calls.  Such a pair is stale by the rule of the toolchain
(:func:`_curry2icurry.translated_before_rewrite`), and the route runs
again at the first import of the module.  ``ROUTE_VERSION`` names the
steps of this module in the key of the ICurry cache
(:func:`cache.icurry_cache_key`), so an entry of a route without a step is
never served.  A hit of the cache writes the ICurry file and runs the
step over the FlatCurry file of the front end beside the source as well
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
other file of the pinned oracle changes.
With front end 3.1.0, the runtime also keeps the front end's completed case
order, while compatibility mode sorts it as icurry 3.3.0 does. This retains
the existing runtime answer order. The archive checks use compatibility
mode; on-disk checks distinguish the two translations.
'''

from .. import config
from . import _preprocessor, _system, flat2icurry
from ..exceptions import CompileError, CurryWarning
from contextlib import contextmanager
from contextvars import ContextVar
import warnings
from ..utility import curryname
import logging, os, re, shlex, sys, time

__all__ = [
    'QUIET_FLAGS', 'ROUTE_VERSION', 'WARNINGS_VARIABLE', 'WARNING_FLAGS'
  , 'command', 'curry2flat', 'curry2icurry', 'flat2icy', 'flatcurry_dirs'
  , 'flatcurryfile', 'frontend_warnings', 'interfacefile'
  , 'optimize_flatcurry', 'report_warnings', 'searchdirs', 'source_root'
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
#   2: 2026-10-12, the set0 lift joins the rewrite step (decision D28): a
#      call set0 e over the captured variables of e becomes setk L xs in
#      the FlatCurry file, so the ICurry of a module with such a call
#      changes.
#   3: 2026-10-24, typed FlatCurry locals and front end version in the key;
#      library products are rebuilt separately for front end 3.1.0.
#   4: 2026-10-25, the external icurry route reads the shipped library's
#      interfaces through the same full search path as the front end.
#   5: imported interface provenance travels with ICurry (#164).
#   6: the default pair is front end 3.1.0 with PAKCS 3.10.0.
#   7: 2026-10-30, the community corpus resolves Test.Prop to the installed
#      library, not to the compile-only module of community/support (#168);
#      products made with the support module name other arities.
#   8: hierarchical modules search from their hierarchy root; an import
#      can resolve to a different module than a sibling of the source.
#   9: primitive wrappers remain opaque to optimization.
#  10: weak rewrite observers preserve captured variables at the caller.
ROUTE_VERSION = 10

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

def source_root(file_in):
  '''The declared hierarchy root, or the directory of a misplaced source.'''
  from ._filenames import module_name
  source = os.path.abspath(file_in)
  directory = os.path.dirname(source)
  parts = module_name(file_in).split('.')
  root = directory
  for _ in parts[:-1]:
    root = os.path.dirname(root)
  if os.path.relpath(source, root) != os.path.join(*parts) + '.curry':
    # PAKCS accepts a physical source path outside its declared hierarchy.
    return directory
  return root

_effective_imports = ContextVar('effective_imports', default=False)


@contextmanager
def effective_imports():
  token = _effective_imports.set(True)
  try:
    yield
  finally:
    _effective_imports.reset(token)


def searchdirs(file_in, currypath):
  '''
  The directories in which the front end and the translation look for
  modules: the effective Curry path, then the system library, without
  repeats. Plan callers establish explicit-file scope with program_path;
  direct file APIs establish that scope here.
  '''
  dirs = curryname.makeCurryPath(currypath)
  from . import _findcurry
  if not _effective_imports.get() and _findcurry._translation_interp.get() is None:
    # A direct file API establishes source-file scope. Pipeline callers
    # already supplied the resolved path, including any explicit-file root.
    dirs.insert(0, source_root(file_in))
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
  root = source_root(file_in)
  name = os.path.relpath(os.path.abspath(file_in), root)
  assert name.endswith('.curry')
  return os.path.join(
      root, '.curry', config.frontend_subdir(), name[:-len('.curry')] + '.fcy'
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

def command(file_in, currypath, quiet=False, search=None, library=None):
  '''
  The front-end command line for the Curry file ``file_in``.  The output
  directory is relative, so it is resolved against the hierarchy root of
  each module the front end compiles. A front end that is not configured raises
  ``CompileError``; both routes need it (see ``_curry2icurry``).  A quiet
  command, and every command while SPRITE_FRONTEND_WARNINGS says off, has
  QUIET_FLAGS; the other commands have WARNING_FLAGS.
  '''
  if config.curry_frontend() is None:
    raise CompileError(
        'no Curry front end found; set SPRITE_FRONTEND or put '
        'pakcs-frontend on PATH'
      )
  name = os.path.relpath(os.path.abspath(file_in), source_root(file_in))
  assert name.endswith('.curry')
  cmd = [
      config.curry_frontend(), '--flat'
    , '-o', os.path.join('.curry', config.frontend_subdir())
    ]
  if quiet or not frontend_warnings():
    cmd.extend(QUIET_FLAGS)
  else:
    cmd.extend(WARNING_FLAGS)
  cmd.extend(resolve_option_paths(shlex.split(config.frontend_flags()), source_root(file_in)))
  if library is not None:
    cmd.extend(['-P', library])
  for dirname in searchdirs(file_in, currypath) if search is None else search:
    cmd.extend(['-i', dirname])
  cmd.append(name[:-len('.curry')])
  return cmd

def resolve_option_paths(options, directory):
  """Keep path options relative to their source context across chdir."""
  path_options = {'-i', '-P', '-o', '--import-dir', '--lib-dir', '--outdir', '--htmldir', '--pgmF'}
  list_options = {'-i', '-P', '--import-dir', '--lib-dir'}
  argument_options = path_options | {'--optF', '-v', '--verbosity', '-c', '--case-mode',
                                    '-X', '-W', '-d', '-O', '-D'}
  result = []
  pending = None
  def resolve(value, option):
    if option not in path_options:
      return value
    if option == '--pgmF' and not os.path.dirname(value):
      return value # bare commands still use PATH
    return os.pathsep.join(os.path.abspath(os.path.join(directory, part))
        for part in (value.split(os.pathsep) if option in list_options else [value]))
  for option in options:
    if pending is not None:
      result.append(resolve(option, pending))
      pending = None
    elif option in argument_options:
      result.append(option)
      pending = option
    elif len(option) > 2 and option[:2] in argument_options:
      result.append(option[:2] + resolve(option[2:], option[:2]))
    elif '=' in option and option.partition('=')[0] in path_options:
      key, _, value = option.partition('=')
      result.append(key + '=' + resolve(value, key))
    else:
      result.append(option)
  return result


def frontend_environment():
  """Use UTF-8 for Haskell source input when no UTF-8 locale is selected."""
  env = os.environ.copy()
  locale = next((env[key] for key in ('LC_ALL', 'LC_CTYPE', 'LANG')
                 if env.get(key)), '')
  if 'utf8' not in locale.lower().replace('-', ''):
    # CPython uses UTF-8 on Darwin, where C.UTF-8 is unavailable.
    env['LC_ALL'] = 'UTF-8' if sys.platform == 'darwin' else 'C.UTF-8'
  return env

def curry2flat(file_in, currypath, quiet=False, rewrite=True):
  """Hide installed sources unless translating in place in the installation.

  Installed dependencies with outside prerequisites are elaborated first,
  following the same destination rule as the requested module. User products
  stay beside their source; in-place installed translations keep their path.
  """
  with protected_translation(file_in, currypath, quiet, rewrite) as context:
    selected, search, library = context
    return _run_frontend(selected, currypath, quiet, rewrite, search, library)


@contextmanager
def protected_translation(file_in, currypath, quiet=False, rewrite=True, external=False):
  """Resolve only this translation's private prerequisites and interface view."""
  from . import _destination, _findcurry
  from ._interfaceview import interface_view, loaded_interface_view
  original = os.path.abspath(file_in)
  selected = _destination.select(original,
      _destination.interfaces(original, currypath))
  if selected == original and _findcurry._installed_library_file(selected) \
      and _findcurry._translation_interp.get() is None:
    yield selected, None, None
    return
  outdir = os.path.join('.curry', config.frontend_subdir())
  view = interface_view(outdir, sources=True) if external else interface_view(outdir)
  with view as library, \
      loaded_interface_view(outdir, searchdirs(selected, currypath), sources=external) as loaded:
    roots = []
    def include(source):
      root = source_root(source)
      if root not in roots:
        roots.append(root)
    if selected != original:
      include(selected)
    def search():
      return list(dict.fromkeys(([loaded] if loaded else []) + roots + [
          directory for directory in searchdirs(selected, currypath)
          if not _findcurry._installed_library_file(directory)] + [library]))

    seen = {original, selected}
    def prepare(source):
      dependencies = []
      _destination.interfaces(source, currypath, dependencies)
      for dependency in dependencies:
        if dependency in seen:
          continue
        seen.add(dependency)
        prepare(dependency)
        products = _destination.interfaces(dependency, currypath)
        if _destination.needs_private(dependency, products):
          if _destination._importing.get() and _findcurry._installed_library_file(dependency):
            from . import _curry2icurry, _filenames
            icy = _filenames.icurryfilename(dependency)
            in_place = all(path is None or _findcurry._installed_library_file(path)
                           for path in products)
            if in_place and _destination.writable(icy) and os.path.isfile(icy) \
                and not _curry2icurry.icurry_is_stale(icy, currypath):
              continue # current installed interfaces need no private elaboration
          copy = _destination.select(dependency, products)
          include(copy)
          _run_frontend(copy, currypath, quiet, rewrite, search(), library)
    prepare(original)
    yield selected, search(), library


def _run_frontend(file_in, currypath, quiet=False, rewrite=True,
                  search=None, library=None):
  '''
  Runs the front end on ``file_in``.  Returns the name of the FlatCurry file.
  A failure of the front end raises ``CompileError`` with its messages; the
  warnings of a run that succeeded are reported (:func:`report_warnings`).

  The run compiles the module and every import whose files are stale for
  the front end (see the module docstring).  With ``rewrite`` the rewrite
  step (the binding optimization and the set0 lift) runs over every
  FlatCurry file the run wrote: the file of ``file_in`` and the files of
  those imports, so that no file of the front end's text is left beside an
  ICurry file of the rewritten program.  A file of an import that cannot
  be read is reported and left; the module's own file raises.  A caller
  that needs the text of the front end passes ``rewrite=False``.
  '''
  reason = _preprocessor.missing(file_in)
  if reason:
    raise CompileError(reason)
  cmd = command(file_in, currypath, quiet, search, library)
  if logger.isEnabledFor(logging.DEBUG):
    logger.debug('Command: %s', ' '.join(cmd))
  moduledir = source_root(file_in)
  roots = searchdirs(file_in, currypath) if search is None else search
  dirs = (flatcurry_dirs(file_in, currypath) if search is None else
          [os.path.join(directory, '.curry', config.frontend_subdir())
           for directory in roots])
  before = _flatcurry_stamps(dirs)
  started = time.monotonic()
  # The front end searches its working directory before explicit imports.
  # A misplaced explicit file needs its physical spelling for output layout.
  from ._filenames import module_name
  declared = module_name(file_in).replace('.', os.sep)
  relative = os.path.relpath(os.path.abspath(file_in), moduledir)[:-6]
  if relative != declared:
    stdout, stderr = _system.pexec(
        cmd, cwd=moduledir, with_stderr=True, env=frontend_environment())
  else:
    import tempfile
    from . import _destination
    cmd[-1] = os.path.join(moduledir, cmd[-1])
    with tempfile.TemporaryDirectory(prefix='sprite-frontend-') as work:
      # Pragmas override command-line options. Normalize their paths in a
      # private view of every selected source the run may compile, including
      # dependencies. Keep the working directory empty for implicit lookup.
      dependencies = []
      # A previous ICurry file may predate imports added to today's source.
      _destination.interfaces(file_in, roots, dependencies, source_imports=True)
      copies = []
      view = os.path.join(work, 'inputs')
      for source in dict.fromkeys([os.path.abspath(file_in)] + dependencies):
        with open(source, encoding='utf-8') as stream:
          text = stream.read()
        def normalize(match):
          options = shlex.split(match.group(1))
          resolved = resolve_option_paths(options, source_root(source))
          return match.group(0) if options == resolved else (
              '{-# OPTIONS_FRONTEND ' + shlex.join(resolved) + ' #-}')
        normalized = _preprocessor.PRAGMA.sub(normalize, text)
        if normalized != text:
          target = os.path.join(view, module_name(source).replace('.', os.sep) + '.curry')
          os.makedirs(os.path.dirname(target), exist_ok=True)
          with open(target, 'w', encoding='utf-8') as stream:
            stream.write(normalized)
          copies.append((source, target))
          if source == os.path.abspath(file_in):
            cmd[-1] = target
      if copies:
        cmd[1:1] = ['-i', view]
      stdout, stderr = _system.pexec(
          cmd, cwd=work, with_stderr=True, env=frontend_environment())
      import shutil
      for source, target in copies:
        for suffix in ('.fcy', '.fint', '.icurry'):
          generated = flatcurryfile(target)[:-4] + suffix
          destination = flatcurryfile(source)[:-4] + suffix
          if os.path.isfile(generated):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copyfile(generated, destination)
  if logger.isEnabledFor(logging.INFO):
    from ._filenames import logging_module_name
    logger.info('module %s: front end ran in %.2f s (%d warnings)',
        logging_module_name(file_in), time.monotonic() - started,
        sum(bool(WARNING_HEAD.match(line)) for line in stderr.splitlines()))
  if stdout:
    logger.debug('Front end output:\n%s', stdout)
  report_warnings(stderr, moduledir)
  fcyfile = flatcurryfile(file_in)
  if not os.path.isfile(fcyfile):
    raise CompileError('the front end did not write %s' % fcyfile)
  if rewrite:
    optimize_flatcurry(fcyfile, roots)
    own = os.path.realpath(fcyfile)
    for written in written_flatcurry(before, _flatcurry_stamps(dirs)):
      if os.path.realpath(written) == own:
        continue
      try:
        optimize_flatcurry(written, roots)
      except Exception as err:
        logger.warning(
            'cannot rewrite %s, which the front end wrote for an import of '
            '%s: %s', written, file_in, err
          )
  return fcyfile

def optimize_flatcurry(fcyfile, searchdirs=()):
  '''
  Applies the rewrite step to the FlatCurry file in place, as PAKCS applies
  its preprocessing before any compiler reads a file: the binding
  optimization, then the set0 lift (:func:`flat2icurry.rewrite_file`).
  Returns the pair of counts (equalities replaced, set0 calls lifted); the
  file is written again only when one of them is not zero.
  '''
  counts = flat2icurry.rewrite_file(fcyfile, searchdirs=searchdirs)
  n, m = counts
  if n:
    logger.debug('Rewrote %s: %d equalities replaced by constrEq', fcyfile, n)
  if m:
    logger.debug('Rewrote %s: %d set0 calls lifted', fcyfile, m)
  return counts

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
  text = text.replace('\r\n', '\n')
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
    warnings.warn(text, CurryWarning, stacklevel=2)
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
  translation applies no pass of its own: the file is the rewritten program
  (see :func:`optimize_flatcurry`).
  '''
  finder = flat2icurry.InterfaceFinder(searchdirs, [config.frontend_subdir()])
  iprog = flat2icurry.translate_file(fcyfile, finder, icurry_compat=False)
  flat2icurry.write_icurry(iprog, file_out)

def curry2icurry(file_in, file_out, currypath, quiet=False):
  '''
  Converts the Curry file ``file_in`` to the ICurry file ``file_out``: the
  front end, the rewrite step over its FlatCurry files, and the translation.
  '''
  with protected_translation(file_in, currypath, quiet) as context:
    selected, search, library = context
    fcyfile = _run_frontend(selected, currypath, quiet,
                            search=search, library=library)
    roots = searchdirs(selected, currypath) if search is None else search
    flat2icy(fcyfile, file_out, roots)
