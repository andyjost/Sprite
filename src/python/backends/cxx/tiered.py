'''
Tiered execution of the C++ backend.

Under the interpreter flag ``interpret`` set to 'tiered', a module without a
current compiled object is interpreted from its ICurry at once (see
materialize.py and curryrt/icurry.hpp), a child process compiles it in the
background, and the runtime replaces the step pointer of every function of
the module by the compiled one when the object is ready.  A step in flight
finishes on the bytecode; the next step of that function runs compiled.  The
values and the rewrite steps are the same in both tiers.  A module with a
current object loads compiled, as under 'new': the Prelude, which make stage
prebuilds, is never interpreted unless its object is missing.

The child.  The job of a module runs sprite-make --so on the source file of
the module, with the search path of the import and the flag interpret:off, so
the plan of the toolchain (Json2Cpp, Cpp2So) writes the object beside the
JSON, with its ABI stamp.  One worker thread of the runtime (curryrt/tiered.cpp)
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

The binding.  The code of a compiled object reads every info table and data
type it names through a slot of the object, a static pointer the load fills
(the binding in curryrt/dynload.hpp): a symbol of the module takes the table
the module of that name has in the registry of the runtime, which is the
table the interpreter made when the module runs or ran interpreted in this
process, and a symbol of an import takes the table of the import.  So an
object binds every reference to the tables the nodes, the bytecode of other
modules, and the Python objects already hold, and one table serves a symbol
for the life of the process, on every platform.  The runtime compares
tables by address (the equality, the bindings of free variables,
curry.inspect.isa), so a second table per symbol is not an option.  The
swap is the load of the object and Module::adopt, which writes the compiled
step of each function into its table.  The runtime keeps the tables of an
interpreted module for the life of the process and gives them back to a
module of the same name made after a reset (Module::create_infotable for a
module interpreted again, Module::bind_infotable for one loaded from its
object; the reset hands them over at once through Module::retire, whether
or not a Python object of the module is alive, issue #114), so a table
keeps its address across a reload.  This module records the modules whose
tables the interpreter made (_register_binding, has_binding): the loader
adopts an object of such a module through the swap, which keeps the object
with the tables.  The object of an earlier incarnation of a module stays
mapped under its path; the runtime loads the new file through a link of its
own name (see the load in curryrt/tiered.hpp).

The imports.  A compiled object names the objects of its imports as needed
libraries, by their SONAMEs (toolchain.soname), which the dynamic linker
satisfies with the objects of those names the process has mapped.  So the
toolchain loads an object only when every import of the module was loaded
from its object (Cpp2So.is_stale imports them first; the loader imports the
modules an object needs before it opens it); a module whose import is
interpreted is interpreted too, and its compile waits in the queue behind
the compile of the import.  The swap maps the objects of the imports before
the importer's: a job carries the objects of the imports the interpreter
runs (direct and indirect, in dependency order, each with the ICurry digest
of its import; see _record and _import_objects), and the swap maps each one
whose module has no object yet, under the same check of its ICurry, so an
importer swaps whenever the objects are ready: when the job of an import
runs later, or when an import has no job (a module without a function to
swap, one of type synonyms alone, say, whose object the child of the
importer compiles).  An import mapped that way is swapped, with no step to
count, whatever comes of the load of the importer after it (poll refreshes
its record either way); its own job, if any, then adopts the mapped object.

What is not compiled.  An expression module (curry.compile in mode 'expr'),
an interactive module, and a module compiled from a string (str2module): the
source lives in a temporary directory the interpreter removes, and an
expression is evaluated once.  A module whose functions are all built in has
nothing to swap.

The check of the swap.  The child compiles the source as it is when the
child runs.  An edit of the source between the import and the compile would
swap in the code of the edited file, and the module would change meaning
without a load (issue #110).  So a job carries the digest of the ICurry
file (.icy) of the module at the import (curryrt.tiered_file_digest), and the
swap refuses the object when the file differs (the result TIERED_EDITED):
the module stays interpreted, and poll logs it.  A new process reads the
edited source.  The .icy and not the JSON the import read: a touch or an
edit of a comment makes the child run the front end again, which writes the
same .icy for the same program, while its JSON differs from the one of the
import in its spacing (sprite-make writes the plain form, the import the
compact one), so a digest of the JSON refused the swap for an edit that
changed nothing.

The load.  curry.load uses the same adoption as a finished compile, so an
object loaded over the tables the interpreter made stays with them.  The
loader waits for any pending compile and checks the registered file before
opening the object.  prepare_adoption checks the source before the load.

The products.  The child compiles a private copy of the module, made in a
directory of the process with the ICurry file, the interface files and the
JSON of the import beside it (_private_copy), so nothing is written under
the source while the compile runs: a search path entry that goes meanwhile,
the temporary directory of a test, say, never finds a half-written product
(issue #173).  The object lands in the private directory and the swap loads
it from there.  Before it opens the object, the swap publishes the
generated file, the ABI stamp and the object beside the source
(publish_products in curryrt/tiered.cpp), each under a temporary name and
renamed into place, when the source and its ICurry file are still there and
the file is the one of the import, and opens the published object, so the
module is loaded from the file beside its source, as before, and the next
process loads it; else it opens the private object.  The swap runs on the
thread that evaluates, at a safepoint, so the files beside a source change
on that thread alone.  Under foreign flags (below) nothing is published.
Since the child compiles the ICurry of the import, an edit of the source
after the import no longer reaches the swap: the module swaps to the code
the import read.  The check of the swap (below) stays for an ICurry file
that another import or process wrote again.

The flags.  An interpreter whose optimizer flags differ from the ones a
child reads from the environment (the inline budget, _foreign_flags) gets
the object of its private copy and nothing beside the source, which another
process would read (issue #116).

Failure.  When the compile or the load fails, the module stays
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
from ...objects import CurryPackage
from ...toolchain import _filenames, _str2module
from ...utility import curryname, formatting
from ...utility.locking import native_metadata
from ..generic import compiler as generic
from . import curryrtbindings as curryrt
from ... import common, config
import atexit, itertools, logging, os, shutil, tempfile, time, weakref, warnings
from ...exceptions import CurryWarning

logger = logging.getLogger(__name__)

__all__ = [
    'MODE', 'cancel', 'counts', 'enabled', 'has_binding'
  , 'module_loaded', 'pending', 'poll', 'status', 'submit', 'wait', 'wait_for'
  ]

MODE = 'tiered'

def enabled(interp):
  '''Tells whether ``interp`` runs tiered execution.'''
  return interp.flags['interpret'] == MODE


class _Record(object):
  '''
  The object of a module the interpreter runs, for the swap of its importers
  (see "The imports" in the module docstring): the file the compile of the
  module writes, the ICurry file of the module at the import and its digest
  then, and a weak reference to the module object.
  '''
  def __init__(self, moduleobj, sofile, icyfile, digest):
    self.module = weakref.ref(moduleobj)
    self.sofile = sofile
    self.icyfile = icyfile
    self.digest = digest
    # The object beside the source that the swap publishes (_publish), or
    # None when nothing is published: a compile under foreign flags.
    self.publish = None


class _State(object):
  '''The state of the process: the bindings and the logged failures.'''
  def __init__(self):
    self.tmpdir = None
    self.bindings = set() # the names of the modules whose tables the interpreter made
    self.pending = {}    # module name -> the object of a compile not applied
    self.modules = {}    # module name -> a weak reference to its module object
    self.records = {}    # module name -> _Record
    self.private = []    # the directories of the private copies, in order
    self.warned = set()  # the keys of the messages logged once
    self.counter = itertools.count()

_state = _State()

@native_metadata
def _tmpdir():
  if _state.tmpdir is None:
    _state.tmpdir = tempfile.mkdtemp(prefix='sprite-tiered-')
  return _state.tmpdir

@native_metadata
def _warn_once(key, message, *args):
  if key not in _state.warned:
    _state.warned.add(key)
    logger.warning(message, *args)
    warnings.warn(message % args, CurryWarning, stacklevel=2)

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

@native_metadata
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
  # A module without a source file (one built by hand from its ICurry) gets
  # its products alone; the child then fails as it did on the original.
  if os.path.isfile(filename):
    shutil.copy2(filename, copy)
  stem = _filenames.icurryfilename(filename)[:-len('.icy')]
  products = [
      stem + suffix
      for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source')
    ]
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

@native_metadata
def _register_binding(moduleobj):
  '''
  Records that the interpreter made a table or a type of ``moduleobj`` in
  this process (see "The binding" in the module docstring), when it did.
  Returns True then.  Call it for a module whose symbols are loaded.
  '''
  h = getHandle(moduleobj)
  imodule = h.icurry
  M = h.backend_handle
  made = False
  for itype in imodule.types.values():
    if _runtime(M.get_type(itype.name)):
      made = True
    for ictor in itype.constructors:
      if _runtime(M.get_infotable(ictor.name)):
        made = True
  for ifun in imodule.functions.values():
    if _runtime(M.get_infotable(ifun.name)):
      made = True
  if made:
    _state.bindings.add(imodule.fullname)
  return made

@native_metadata
def prepare_adoption(interp, name):
  '''
  The checks of a foreground swap, before any object opens: the module
  keeps its tables and its binding goes on record, and its source is as it
  was at the import.  Returns the steps to swap, the functions the
  interpreter runs or the trap holds.
  '''
  from ...exceptions import LoadError
  module = interp.modules.get(name)
  if isinstance(module, CurryPackage):
    module = None # a namespace has no function tables to adopt
  if module is not None:
    h = getHandle(module)
    h.backend_handle.keep_tables()
    _register_binding(module)
  record = _state.records.get(name)
  if record is not None and record.module() is module and module is not None \
      and record.icyfile \
      and curryrt.tiered_file_digest(record.icyfile) != record.digest:
    raise LoadError('cannot swap module %r: %s' % (name, curryrt.TIERED_EDITED))
  if module is None:
    return []
  M = getHandle(module).backend_handle
  return [
      (ifun.name, generic.mangle(ifun.splitname(), generic.STEP_FUNCTION), info)
      for ifun in getHandle(module).icurry.functions.values()
      if (info := M.get_infotable(ifun.name)) is not None
         and (curryrt.icurry_is_interpreted(info) or curryrt.is_trapped(info))
    ]


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

@native_metadata
def module_loaded(interp, moduleobj, currypath):
  '''
  Called when the import of a module ends (IBackend.module_loaded).
  Records the binding of the module, records its object for the swap of
  its importers (_record) and queues its background compile.  Returns True
  when a job was queued.  ``currypath`` is the search path of the imports
  of the module (IBackend.module_loaded), the CURRYPATH of the child.
  '''
  if not _compiles(interp, moduleobj):
    return False
  # Every module the interpreter runs is on record, a module without a
  # table made at run time too (one of type synonyms alone, say): its
  # importers name its object all the same.
  _record(moduleobj)
  _register_binding(moduleobj)
  return submit(interp, moduleobj, currypath)

@native_metadata
def _record(moduleobj, sofile=None):
  '''
  Records the object of a module the interpreter runs (see _Record): by
  default the object beside its source, which its own job and the child of
  an importer write; ``sofile`` names another (a private copy).  The digest
  is of the ICurry file beside the source at this moment, as the check of
  the swap takes it.  Returns the record.
  '''
  imodule = getHandle(moduleobj).icurry
  filename = imodule.filename
  if sofile is None:
    sofile = _filenames.replacesuffix(_filenames.icurryfilename(filename), '.so')
  icyfile = _filenames.icurryfilename(filename)
  if not os.path.isfile(icyfile):
    icyfile = ''
  digest = '' if not icyfile else curryrt.tiered_file_digest(icyfile)
  record = _Record(moduleobj, sofile, icyfile, digest)
  _state.records[imodule.fullname] = record
  return record

@native_metadata
def _import_objects(interp, imodule):
  '''
  The objects of the imports of ``imodule`` that the swap maps before the
  object of the module, as tuples (module, sofile, icurryfile, digest,
  publish), in
  dependency order, an import before the modules that import it, each
  once: the imports the interpreter runs in this process, direct and
  indirect, that have a record (_record) for their module object.  A module
  loaded from its object is mapped already, and so are its imports, so the
  walk stops at it.
  '''
  out = []
  seen = set()
  def visit(name):
    if name in seen:
      return
    seen.add(name)
    moduleobj = interp.modules.get(name)
    if moduleobj is None:
      return
    h = getHandle(moduleobj)
    if h.icurry.metadata.get('cxx.shlib') is not None:
      return
    for depname in h.icurry.imports:
      visit(depname)
    record = _state.records.get(name)
    if record is not None and record.module() is moduleobj:
      out.append((
          name, record.sofile, record.icyfile, record.digest
        , record.publish or ''
        ))
  for depname in imodule.imports:
    visit(depname)
  return out

@native_metadata
def submit(interp, moduleobj, currypath):
  '''
  Queues the background compile of a module the interpreter runs.  Returns
  True when a job was queued.  ``currypath`` is the search path of the
  import.
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
    if info is not None and curryrt.icurry_is_interpreted(info):
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
  # The child compiles a private copy (the module docstring, "The
  # products"): nothing is written under the source while it runs.  The
  # digest below is still the one of the ICurry file beside the original:
  # the copy is of this moment.
  source, searchdirs = _private_copy(imodule)
  currypath = searchdirs + list(
      currypath if currypath is not None else interp.path
    )
  envp = _environment(interp, currypath)
  envp.append('_SPRITE_BACKGROUND_MODULE=' + name)
  sofile = _filenames.replacesuffix(_filenames.icurryfilename(source), '.so')
  logfile = os.path.join(
      _tmpdir(), 'compile%d-%s.log' % (next(_state.counter), name)
    )
  argv = [config.sprite_make(), '--so', '-z', '-q', source]
  # The ICurry file of the module and its digest: the swap refuses an object
  # of another text (see the module docstring).  The record of the module
  # names the object this job writes, for the swap of its importers.
  record = _record(moduleobj, sofile)
  if not _foreign_flags(interp):
    record.publish = _filenames.replacesuffix(
        _filenames.icurryfilename(filename), '.so'
      )
  if logger.isEnabledFor(logging.DEBUG):
    logger.debug('Compiling %s in the background: %s', name, ' '.join(argv))
  curryrt.tiered_submit(
      name, argv, envp, logfile, sofile, record.publish or '', steps
    , record.icyfile, record.digest, _import_objects(interp, imodule)
    )
  _state.pending[name] = sofile
  _state.modules[name] = weakref.ref(moduleobj)
  return True

@native_metadata
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
  record = _state.records.get(name)
  if record is not None:
    candidates.append(record.module())
  if interp is not None:
    candidates.append(interp.modules.get(name))
  for moduleobj in candidates:
    if moduleobj is None or isinstance(moduleobj, CurryPackage):
      continue
    h = getHandle(moduleobj)
    shlib = h.backend_handle.shlib
    if shlib is not None and h.icurry.metadata.get('cxx.shlib') is None:
      h.icurry.update_metadata({'cxx.shlib': shlib})
    # The record names the object the module runs from now, published or
    # private, for the swap of its importers.
    if shlib is not None and record is not None and record.module() is moduleobj:
      record.sofile = shlib

@native_metadata
def poll(interp=None):
  '''
  Applies the compiled objects that finished in the background, logs the
  results, and returns them (see curryrtbindings.tiered_results).  Call it from
  the thread that evaluates.
  '''
  curryrt.tiered_poll()
  results = curryrt.tiered_results()
  for result in results:
    name = result['module']
    _state.pending.pop(name, None)
    if not result['ok']:
      _state.modules.pop(name, None)
    for imported in result['mapped']:
      # The swap mapped the object of an import (see the module docstring,
      # "The imports") before it loaded the object of the module: the
      # import runs compiled now, whatever came of the load of the module,
      # and its record names its object.
      logger.info(
          'Mapped the object of %s, an import of %s, in the background'
        , imported, name
        )
      _refresh(imported, interp)
    if result['ok']:
      logger.info('module %s: background compile finished in %.2f s, swapped',
          name, result['seconds'])
      logger.info(
          'Compiled %s in the background in %.2f s; %d function%s swapped%s'
        , name, result['seconds'], result['swapped']
        , '' if result['swapped'] == 1 else 's'
        , ' during an evaluation' if result['in_evaluation'] else ''
        )
      _refresh(name, interp)
    elif result['error'] == 'the module is no longer loaded':
      logger.info('module %s: background compile not applied (%s)', name, result['error'])
    elif result['error'] == curryrt.TIERED_EDITED:
      logger.info('module %s: background compile not applied (%s)', name, result['error'])
      _warn_once(
          ('edited', name)
        , 'the background compile of module %r is not applied: its source '
          'changed after the import, and the swap never changes what a '
          'loaded module means; the module stays interpreted in this '
          'process, and a new process reads the edited file', name
        )
    else:
      output = result['output'].strip()
      if logger.isEnabledFor(logging.INFO):
        logger.info('module %s: background compile failed: %s', name,
            next((line for line in output.splitlines()
                  if 'error:' in line.lower() or line.startswith('sprite-make:')),
                 result['error'].splitlines()[0]))
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
    idle = curryrt.tiered_wait(slice_)
    poll(interp)
    if idle:
      return True
    if deadline is not None and time.monotonic() >= deadline:
      return False

@native_metadata
def pending(name):
  '''
  Tells whether a background compile of module ``name`` is queued, running,
  or finished and not yet applied.
  '''
  return name in _state.pending

@native_metadata
def _drop_pending(name):
  _state.pending.pop(name, None)

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
    idle = curryrt.tiered_wait(slice_)
    poll(interp)
    if idle:
      # Nothing is queued or running, and the poll applied what finished:
      # a record left here is stale.
      _drop_pending(name)
    elif deadline is not None and time.monotonic() >= deadline:
      return False
  return True

@native_metadata
def has_binding(name):
  '''
  Tells whether the interpreter made a table of module ``name`` in this
  process: the module runs, or ran, interpreted, and an object loaded under
  the name binds to those tables (see the module docstring).
  '''
  return name in _state.bindings

@native_metadata
def status():
  '''
  The counts of tiered execution in this process: queued, running,
  swapped_functions, swapped_modules, failed_modules, applied_in_evaluation,
  and bindings, the modules whose tables the interpreter made.
  '''
  counts = curryrt.tiered_status()
  counts['bindings'] = len(_state.bindings)
  return counts

def counts():
  '''
  The two counts Interpreter.stats reports: the functions swapped to
  compiled code and the background compiles that failed.
  '''
  s = curryrt.tiered_status()
  return s['swapped_functions'], s['failed_modules']

@native_metadata
def cancel():
  '''Drops the queued compiles and kills the running one.'''
  curryrt.tiered_cancel()
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
