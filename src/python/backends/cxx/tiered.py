'''
Tiered execution of the C++ backend.

Under the interpreter flag ``interpret`` set to 'tiered', a module without a
current compiled object is interpreted from its ICurry at once (see
materialize.py and cyrt/icurry.hpp), a child process compiles it in the
background, and the runtime replaces the step pointer of every function of
the module by the compiled one when the object is ready.  A step in flight
finishes on the bytecode; the next step of that function runs compiled.  The
values and the rewrite steps are the same in both tiers.  A module with a
current object loads compiled, as under 'new': the Prelude, which make stage
prebuilds, is never interpreted unless its object is missing.

The child.  The job of a module runs sprite-make --so on the source file of
the module, with the search path of the import and the flag interpret:off, so
the plan of the toolchain (Json2Cpp, Cpp2So) writes the object beside the
JSON, with its ABI stamp.  One worker thread of the runtime (cyrt/tiered.cpp)
runs the jobs in the order of submission, one at a time.  A module is
submitted when its load ends, after the loads of its imports, so the object
of an import exists when a module that imports it compiles.  The thread needs
no GIL: it spawns processes and waits.  So the swap reaches a running
evaluation: the scheduler applies a finished job at its periodic safepoint
(RuntimeState::check_interrupts), and Interpreter.eval applies the finished
jobs before an evaluation (poll).

The flags.  The child compiles under the inline budget of the interpreter,
so the code it swaps in is the code the interpreter ran.  The budget shapes
the generated code, and the ABI stamp of an object does not record it, so a
compile beside the source under a budget other than the one the environment
names would leave an object that every later process of that tree takes for
current (issue #116).  Such a process compiles a copy of the source in a
directory of its own (_foreign_flags, _private_copy): the generated file and
the object land there, the product cache leaves them out
(_productcache.excluded), and they go with the process.  An import compiled
that way is found by the compile of its importer through the search path of
the child, before the original.

The shim.  A compiled object names its info tables and data types by ELF
symbol, its own included, and the dynamic linker binds a reference to the
first definition in the global scope.  When the load of a module ends, this
module registers a shim for it if the interpreter made any of its tables: a
library of absolute symbols, one per table and type made at run time, with
the address of the table (g++ -shared -nostdlib over an empty file with
--defsym; see Shim).  A job carries the shims not yet loaded, and the swap
loads them before the object; the loader loads them before any object it
loads (ensure_shims).  So an object binds every reference to the tables the
nodes, the bytecode of other modules, and the Python objects already hold,
and one table serves a symbol for the life of the process.  The runtime
compares tables by address (the equality, the bindings of free variables,
curry.inspect.isa), so a second table per symbol is not an option.  The load
itself is the swap: the dynamic initializer of a static table of the object
constructs it at the address its symbol resolves to, which is the table the
interpreter uses, so the table carries the compiled step when dlopen returns
(Module::adopt counts the functions and takes the rest from the object).  A
shim is made for the process: the addresses belong to it.  The runtime keeps
the tables of an interpreted module for the life of the process and gives
them back to a module of the same name made after a reset
(Module::create_infotable), so a shim stays valid across a reload.  A module
whose tables changed shape after its shim was made stays interpreted, and so
does every module that imports it, because their objects would bind to the
old tables; one warning says so.  The object of an earlier incarnation of a
module stays mapped under its path; the runtime loads the new file through a
link of its own name (see the load in cyrt/tiered.hpp).

The imports.  A compiled object names the objects of its imports as needed
libraries, by their SONAMEs (toolchain.soname), which the dynamic linker
satisfies with the objects of those names the process has mapped.  So the
toolchain loads an object only when every import of the module was loaded
from its object (Cpp2So.is_stale imports them first; the loader imports the
modules an object needs before it opens it); a module whose import is
interpreted is interpreted too, and its compile waits in the queue behind
the compile of the import, whose object the swap maps before the importer's.

What is not compiled.  An expression module (curry.compile in mode 'expr'),
an interactive module, and a module compiled from a string (str2module): the
source lives in a temporary directory the interpreter removes, and an
expression is evaluated once.  A module whose functions are all built in has
nothing to swap.

The check of the swap.  The child compiles the source as it is when the
child runs.  An edit of the source between the import and the compile would
swap in the code of the edited file, and the module would change meaning
without a load (issue #110).  So a job carries the digest of the ICurry
file (.icy) of the module at the import (cyrt.tiered_file_digest), and the
swap refuses the object when the file differs (the result TIERED_EDITED):
the module stays interpreted, and poll logs it.  A new process reads the
edited source.  The .icy and not the JSON the import read: a touch or an
edit of a comment makes the child run the front end again, which writes the
same .icy for the same program, while its JSON differs from the one of the
import in its spacing (sprite-make writes the plain form, the import the
compact one), so a digest of the JSON refused the swap for an edit that
changed nothing.

The load.  curry.load of the object of a module that runs interpreted here
is a swap as well: the object binds to the live tables through the shim, and
an object dropped after such a load leaves the tables pointing into unmapped
memory (issue #109).  The loader (loader.py) asks the registry by the module
name before it opens an object, waits for a pending compile of the module
(wait_for) and loads the object the compile wrote, and refuses the object of
a module that stays interpreted (has_shim).

Failure.  When the compile, the shim, or the load fails, the module stays
interpreted, and the failure is logged once per module (poll).  The results
applied at a safepoint are logged by the next poll: before and after an
evaluation, by wait, and at the exit of the process.  Interpreter.stats
reports the functions swapped and the compiles that failed.

Cancel.  A reset, a reload, and the exit of the process drop the queue and
kill the running compile, so no compiler outlives the interpreter and a short
program never waits for one.  The object of a program that ends before its
compile is not written; sprite-make --so writes it.
'''

from ...objects.handle import getHandle
from ...toolchain import _filenames, _str2module
from ...utility import curryname, formatting
from ..generic import compiler as generic
from . import cyrtbindings as cyrt
from ... import common, config
import atexit, itertools, logging, os, shutil, tempfile, time, weakref

logger = logging.getLogger(__name__)

__all__ = [
    'MODE', 'cancel', 'counts', 'enabled', 'ensure_shims', 'has_shim'
  , 'module_loaded', 'pending', 'poll', 'status', 'submit', 'wait', 'wait_for'
  ]

MODE = 'tiered'

def enabled(interp):
  '''Tells whether ``interp`` runs tiered execution.'''
  return interp.flags['interpret'] == MODE


class Shim(object):
  '''
  The shim of a module: the symbols of its tables and types made at run time,
  each with the address of the object in this process, and the file of the
  library.  See the module docstring.
  '''
  def __init__(self, name, path, symbols):
    self.name = name
    self.path = path
    self.symbols = symbols
    # Set once the runtime loaded the shim.  A hint: the runtime loads a
    # shim once, whatever this says.
    self.loaded = False
    # Set when a module of this name was made again with other tables: the
    # shim names the old ones, and no object may bind to it.
    self.blocked = False

  def argv(self, cxx):
    '''
    The command that links the shim.  It writes the file under a temporary
    name; the runtime moves it into place (tiered_build_shim).
    '''
    return [
        cxx, '-shared', '-nostdlib', '-x', 'c++', os.devnull
      , '-o', self.path + '.tmp'
      ] + [
        '-Wl,--defsym=%s=0x%x' % item for item in sorted(self.symbols.items())
      ]


class _State(object):
  '''The state of the process: the shims and the logged failures.'''
  def __init__(self):
    self.tmpdir = None
    self.shims = {}      # module name -> Shim
    self.pending = {}    # module name -> the object of a compile not applied
    self.modules = {}    # module name -> a weak reference to its module object
    self.private = []    # the directories of the private copies, in order
    self.warned = set()  # the keys of the messages logged once
    self.counter = itertools.count()

_state = _State()

def _tmpdir():
  if _state.tmpdir is None:
    _state.tmpdir = tempfile.mkdtemp(prefix='sprite-tiered-')
  return _state.tmpdir

def _warn_once(key, message, *args):
  if key not in _state.warned:
    _state.warned.add(key)
    logger.warning(message, *args)

def _environment(interp, currypath=None):
  '''
  The environment of the child: the flags of a compile, and the search path
  of the import.  The child compiles under the inline budget of the
  interpreter, so the code it swaps in is the code the interpreter ran; a
  budget other than the one the environment names compiles a private copy
  of the source (see the module docstring and submit).
  '''
  env = dict(os.environ)
  env['SPRITE_INTERPRETER_FLAGS'] = \
      'backend:cxx,interpret:off,debug:%s,inline_budget:%d' % (
          'true' if interp.flags['debug'] else 'false'
        , interp.flags['inline_budget']
        )
  if currypath is not None:
    env['CURRYPATH'] = ':'.join(curryname.makeCurryPath(currypath))
  return ['%s=%s' % item for item in env.items()]

def _foreign_flags(interp):
  '''
  Tells whether ``interp`` runs under optimizer flags other than the ones a
  child reads from the environment: the inline budget, which shapes the
  generated code and which the ABI stamp of an object does not record.  The
  compiled products of such an interpreter go into a directory of the
  process, never beside a source that another process reads (issue #116).
  '''
  from ...interpreter import flags as _flags
  environment = dict(_flags.get_default_flags())
  environment.update(_flags.getflags())
  return interp.flags['inline_budget'] != environment['inline_budget']

def _private_copy(imodule):
  '''
  Copies the source of ``imodule`` into a directory of the process, with
  its current ICurry file, interface files and JSON beside it, in the
  layout of a search path entry.  Returns the copy and the search
  directories of the child: the private directories made before this one,
  the newest first, so an import compiled this way is found with its
  object, and the copy of the live module before an older copy of the same
  name, then the root of the original, so the other imports are found in
  place.  The child
  compiles the copy, so its generated file and its object land in the
  private directory (see the module docstring).
  '''
  filename = os.path.abspath(imodule.filename)
  relpath = imodule.fullname.replace('.', os.sep) + '.curry'
  if filename.endswith(os.sep + relpath):
    root = filename[:-len(relpath) - 1]
  else:
    root, relpath = os.path.split(filename)
  directory = os.path.join(_tmpdir(), 'private%d' % next(_state.counter))
  copy = os.path.join(directory, relpath)
  os.makedirs(os.path.dirname(copy), exist_ok=True)
  shutil.copy2(filename, copy)
  stem = _filenames.icurryfilename(filename)[:-len('.icy')]
  products = [stem + suffix for suffix in ('.icy', '.fint', '.icurry')]
  products += list(_filenames.jsonfilenames(filename))
  productdir = os.path.dirname(_filenames.icurryfilename(copy))
  os.makedirs(productdir, exist_ok=True)
  for product in products:
    if os.path.isfile(product):
      shutil.copy2(
          product, os.path.join(productdir, os.path.basename(product))
        )
  searchdirs = list(reversed(_state.private)) + [root]
  _state.private.append(directory)
  return copy, searchdirs

def _runtime(info):
  '''Whether a table or type was made at run time.'''
  if info is None:
    return False
  flags = info.flags
  if isinstance(flags, str):
    # The flags of a DataType are a char.
    flags = ord(flags)
  return not (flags & common.F_STATIC_OBJECT)

def _register_shim(moduleobj):
  '''
  The shim of a module, made on the first call.  None when the module has no
  table made at run time, or when its tables changed since its shim was
  made: the shim names the old ones, and a compiled object would bind to
  them.  Call it for a module whose symbols are loaded.
  '''
  h = getHandle(moduleobj)
  imodule = h.icurry
  name = imodule.fullname
  M = h.backend_handle
  symbols = {}
  for itype in imodule.types.values():
    typedef = M.get_type(itype.name)
    if _runtime(typedef):
      symbols[generic.mangle(itype.splitname(), generic.DATA_TYPE)] = \
          typedef.address
    for ictor in itype.constructors:
      info = M.get_infotable(ictor.name)
      if _runtime(info):
        symbols[generic.mangle(ictor.splitname(), generic.INFO_TABLE)] = \
            info.address
  for ifun in imodule.functions.values():
    info = M.get_infotable(ifun.name)
    if _runtime(info):
      symbols[generic.mangle(ifun.splitname(), generic.INFO_TABLE)] = \
          info.address
  shim = _state.shims.get(name)
  if shim is not None:
    # A shim is final once made: compiled code bound to its addresses.  A
    # module of the same name made again takes its tables back (see
    # Module::create_infotable), so the addresses agree unless the shape of
    # a symbol changed.
    if shim.symbols == symbols:
      return shim
    shim.blocked = True
    _warn_once(
        ('replaced', name)
      , 'the tables of module %r changed after compiled code bound to them; '
        'the module and the modules that import it stay interpreted in this '
        'process', name
      )
    return None
  if not symbols:
    return None
  path = os.path.join(
      _tmpdir(), 'shim%d-%s.so' % (next(_state.counter), name)
    )
  shim = Shim(name, path, symbols)
  _state.shims[name] = shim
  return shim

def _load_shim(shim, cxx, envp):
  '''Links a shim, unless it exists, and loads it.  False on failure.'''
  if shim.loaded:
    return True
  try:
    cyrt.tiered_build_shim(shim.path, shim.argv(cxx), envp)
    cyrt.tiered_load_shim(shim.path)
  except RuntimeError as exc:
    _warn_once(('shim', shim.name), '%s', exc)
    return False
  shim.loaded = True
  return True

def _pending_shims(cxx):
  '''The shims not yet loaded, as (file, argv) pairs for a job.'''
  return [
      (shim.path, shim.argv(cxx)) for shim in _state.shims.values()
        if not shim.loaded and not shim.blocked
    ]

def ensure_shims(interp):
  '''
  Loads every registered shim.  The loader calls this before it loads a
  compiled object, so that the object binds its references to the tables in
  use.
  '''
  if not enabled(interp):
    return
  cxx = None
  for shim in list(_state.shims.values()):
    if shim.loaded or shim.blocked:
      continue
    if cxx is None:
      cxx = config.cxx_tool()
      if cxx is None:
        return
    _load_shim(shim, cxx, _environment(interp))

def _compiles(interp, moduleobj):
  '''
  Tells whether a module takes part in tiered execution: not a package, not
  loaded from an object, not anonymous, not compiled from a string.
  '''
  if not enabled(interp):
    return False
  h = getHandle(moduleobj)
  if h.is_package:
    return False
  imodule = h.icurry
  if imodule.metadata.get('cxx.shlib') is not None:
    return False
  if config.is_anonymous_modname(imodule.fullname):
    return False
  filename = imodule.filename
  return bool(filename) and not _str2module.is_temporary(filename)

def _blocked_import(interp, imodule):
  '''
  The name of an import, direct or indirect, whose shim is blocked (see
  Shim), or None.  An object of the module would bind to the old tables of
  that import.
  '''
  seen = set()
  pending = list(imodule.imports)
  while pending:
    name = pending.pop()
    if name in seen:
      continue
    seen.add(name)
    shim = _state.shims.get(name)
    if shim is not None and shim.blocked:
      return name
    moduleobj = interp.modules.get(name)
    if moduleobj is not None:
      pending.extend(getHandle(moduleobj).icurry.imports)
  return None

def _prelude_compiled(interp):
  '''Tells whether the Prelude of ``interp`` was loaded from its object.'''
  prelude = interp.modules.get('Prelude')
  return prelude is not None \
      and getHandle(prelude).icurry.metadata.get('cxx.shlib') is not None

def _current_source(imodule):
  '''
  Tells whether a current generated file (.cpp) lies beside the ICurry of
  ``imodule``.  Under the flag set to 'new' such a module is compiled from
  that file, not interpreted (toolchain.Json2Cpp.ends_plan), which fails
  without a compiler.
  '''
  from . import toolchain
  cppfile = _filenames.replacesuffix(
      _filenames.icurryfilename(imodule.filename), '.cpp'
    )
  return os.path.isfile(cppfile) and not toolchain.source_is_stale(cppfile)

def _interpreter_setting(interp, imodule):
  '''
  The setting of the flag ``interpret`` that the notice of a missing
  compiler names: the one that selects the interpreter without a compile.
  'all' never compiles.  'new' keeps the compiled library, so the bytecode
  of the Prelude costs nothing, but it compiles a module whose object is
  stale and whose generated file is current; so it is named only where the
  Prelude loaded from its object and ``imodule`` has no current generated
  file.
  '''
  if _prelude_compiled(interp) and not _current_source(imodule):
    return 'new'
  return 'all'

def module_loaded(interp, moduleobj, currypath):
  '''
  Called when the import of a module ends (IBackend.module_loaded).
  Registers the shim of the module and queues its background compile.
  Returns True when a job was queued.  ``currypath`` is the search path of
  the import.
  '''
  if not _compiles(interp, moduleobj):
    return False
  shim = _register_shim(moduleobj)
  if shim is None and _state.shims.get(getHandle(moduleobj).icurry.fullname):
    # The shape changed: blocked.
    return False
  return submit(interp, moduleobj, currypath)

def submit(interp, moduleobj, currypath):
  '''
  Queues the background compile of a module the interpreter runs.  Returns
  True when a job was queued.  ``currypath`` is the search path of the
  import.  The shim of the module must be registered (module_loaded).
  '''
  if not _compiles(interp, moduleobj):
    return False
  h = getHandle(moduleobj)
  imodule = h.icurry
  name = imodule.fullname
  filename = imodule.filename
  M = h.backend_handle
  steps = []
  for ifun in imodule.functions.values():
    info = M.get_infotable(ifun.name)
    if info is not None and cyrt.icurry_is_interpreted(info):
      steps.append((
          ifun.name, generic.mangle(ifun.splitname(), generic.STEP_FUNCTION)
        , info
        ))
  if not steps:
    return False
  cxx = config.cxx_tool()
  if cxx is None:
    # The notice of an installation without a compiler: once per process,
    # at the first module that stays interpreted for the lack of one.  It
    # names the setting of the flag that selects the interpreter without a
    # compile (_interpreter_setting; the page "Installing and running
    # without a C++ compiler" of the documentation).
    _warn_once(
        'nocxx'
      , 'no C++ compiler is installed at %s; module %r and the modules after '
        'it run interpreted (add interpret:%s to SPRITE_INTERPRETER_FLAGS to '
        'select the interpreter without this notice)'
      , config.installed_path('tools', 'cxx'), name
      , _interpreter_setting(interp, imodule)
      )
    return False
  shim = _state.shims.get(name)
  if shim is None or shim.blocked:
    return False
  blocked = _blocked_import(interp, imodule)
  if blocked is not None:
    logger.debug(
        'Module %s stays interpreted: its import %s changed shape', name
      , blocked
      )
    return False
  source = filename
  if _foreign_flags(interp):
    # The object goes into a directory of the process (the module
    # docstring, "The flags").  The digest below is still the one of the
    # ICurry file beside the original: the copy is of this moment.
    source, searchdirs = _private_copy(imodule)
    currypath = searchdirs + list(
        currypath if currypath is not None else interp.path
      )
  envp = _environment(interp, currypath)
  sofile = _filenames.replacesuffix(_filenames.icurryfilename(source), '.so')
  logfile = os.path.join(
      _tmpdir(), 'compile%d-%s.log' % (next(_state.counter), name)
    )
  argv = [config.installed_path('bin', 'sprite-make'), '--so', '-z', '-q', source]
  # The ICurry file of the module and its digest: the swap refuses an object
  # of another text (see the module docstring).
  icyfile = _filenames.icurryfilename(filename)
  if not os.path.isfile(icyfile):
    icyfile = ''
  digest = '' if not icyfile else cyrt.tiered_file_digest(icyfile)
  logger.debug('Compiling %s in the background: %s', name, ' '.join(argv))
  cyrt.tiered_submit(
      name, _pending_shims(cxx), argv, envp, logfile, sofile, steps
    , icyfile, digest
    )
  _state.pending[name] = sofile
  _state.modules[name] = weakref.ref(moduleobj)
  return True

def _refresh(name, interp=None):
  '''
  Records the object of a swapped module in its ICurry (cxx.shlib), so the
  handle of the module names it (sofilename) and inspect.getimpl reads the
  compiled code from the generated file beside it.  The module is the one
  the job was submitted for, whichever thread polls and whether or not an
  interpreter was given (issue #115: a poll without one left the ICurry
  without the object); the module of that name in ``interp``, when it is
  another object, learns of it too.
  '''
  ref = _state.modules.pop(name, None)
  candidates = [] if ref is None else [ref()]
  if interp is not None:
    candidates.append(interp.modules.get(name))
  for moduleobj in candidates:
    if moduleobj is None:
      continue
    h = getHandle(moduleobj)
    shlib = h.backend_handle.shlib
    if shlib is not None and h.icurry.metadata.get('cxx.shlib') is None:
      h.icurry.update_metadata({'cxx.shlib': shlib})

def poll(interp=None):
  '''
  Applies the compiled objects that finished in the background, logs the
  results, and returns them (see cyrtbindings.tiered_results).  Call it from
  the thread that evaluates.
  '''
  cyrt.tiered_poll()
  results = cyrt.tiered_results()
  for result in results:
    name = result['module']
    _state.pending.pop(name, None)
    if not result['ok']:
      _state.modules.pop(name, None)
    if result['ok']:
      logger.info(
          'Compiled %s in the background in %.2f s; %d function%s swapped%s'
        , name, result['seconds'], result['swapped']
        , '' if result['swapped'] == 1 else 's'
        , ' during an evaluation' if result['in_evaluation'] else ''
        )
      shim = _state.shims.get(name)
      if shim is not None:
        shim.loaded = True
      _refresh(name, interp)
    elif result['error'] == 'the module is no longer loaded':
      logger.debug('The background compile of %s is not needed', name)
    elif result['error'] == cyrt.TIERED_EDITED:
      logger.warning(
          'the background compile of module %r is not applied: its source '
          'changed after the import, and the swap never changes what a '
          'loaded module means; the module stays interpreted in this '
          'process, and a new process reads the edited file', name
        )
    else:
      output = result['output'].strip()
      _warn_once(
          ('failed', name)
        , 'the background compile of module %r failed; the module stays '
          'interpreted: %s%s'
        , name, result['error']
        , '\n' + formatting.indent(output, 8) if output else ''
        )
  return results

def wait(timeout=None, interp=None):
  '''
  Waits until every queued compile ended and its result was applied, or
  until ``timeout`` seconds passed.  Returns True when the worker is idle.
  '''
  deadline = None if timeout is None else time.monotonic() + timeout
  while True:
    if deadline is None:
      slice_ = 0.25
    else:
      slice_ = min(0.25, max(0.0, deadline - time.monotonic()))
    idle = cyrt.tiered_wait(slice_)
    poll(interp)
    if idle:
      return True
    if deadline is not None and time.monotonic() >= deadline:
      return False

def pending(name):
  '''
  Tells whether a background compile of module ``name`` is queued, running,
  or finished and not yet applied.
  '''
  return name in _state.pending

def wait_for(name, timeout=None, interp=None):
  '''
  Waits until the background compile of module ``name`` ended and its result
  was applied (the compiles queued before it end first), or until
  ``timeout`` seconds passed.  Returns True when no compile of the module is
  pending.
  '''
  deadline = None if timeout is None else time.monotonic() + timeout
  while pending(name):
    if deadline is None:
      slice_ = 0.25
    else:
      slice_ = min(0.25, max(0.0, deadline - time.monotonic()))
    idle = cyrt.tiered_wait(slice_)
    poll(interp)
    if idle:
      # Nothing is queued or running, and the poll applied what finished:
      # a record left here is stale.
      _state.pending.pop(name, None)
    elif deadline is not None and time.monotonic() >= deadline:
      return False
  return True

def has_shim(name):
  '''
  Tells whether a shim names the tables of module ``name``: the module runs,
  or ran, interpreted in this process, and an object loaded under the name
  binds to those tables (see the module docstring).
  '''
  return name in _state.shims

def status():
  '''
  The counts of tiered execution in this process: queued, running,
  swapped_functions, swapped_modules, failed_modules, applied_in_evaluation,
  and shims.
  '''
  counts = cyrt.tiered_status()
  counts['shims'] = len(_state.shims)
  return counts

def counts():
  '''
  The two counts Interpreter.stats reports: the functions swapped to
  compiled code and the background compiles that failed.
  '''
  s = cyrt.tiered_status()
  return s['swapped_functions'], s['failed_modules']

def cancel():
  '''Drops the queued compiles and kills the running one.'''
  cyrt.tiered_cancel()
  _state.pending.clear()
  _state.modules.clear()

def _at_exit():
  # The compiles that ended are applied and logged, so that a failure
  # reaches the log of a process that evaluates once; then the rest is
  # cancelled.
  try:
    poll()
  except Exception:  # pragma: no cover
    pass
  cancel()
  if _state.tmpdir is not None:
    shutil.rmtree(_state.tmpdir, ignore_errors=True)

atexit.register(_at_exit)
