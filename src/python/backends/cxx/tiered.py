'''
The C++ compiler backend of the JIT (jit_backend:cxx): compiled execution
through the generated C++ of a module.

With jit:hot,jit_backend:cxx, a module starts interpreted and its private
compile job is armed at load. The runtime starts that job when the first
function reaches SPRITE_JIT_THRESHOLD calls. jit:eager submits and waits
at module load instead. The worker and adoption API keep their internal
"tiered" names for the AOT loader and compile-on-first-use clients too.
Hot adoption runs at the scheduler's JIT safepoint (g_icurry_posted).

The child.  The job of a module runs sprite-make --so on the source file of
the module, with the search path of the import and the flag interpret:off, so
the plan of the toolchain (ICurry2Cpp, Cpp2So) writes the object beside the
image, with its ABI stamp.  One worker thread of the runtime (curryrt/tiered.cpp)
runs the jobs in the order of submission, one at a time.  A module is
registered when its load ends, after the loads of its imports. A hot
importer may compile a cold dependency through its private search path.  The thread needs
no GIL: it spawns processes and waits.  So the swap reaches a running
evaluation: the scheduler applies a finished job at its periodic safepoint
(RuntimeState::check_interrupts), and Interpreter.eval applies the finished
jobs before an evaluation (poll).

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

What is not compiled. Modules without source products and modules whose
functions are all built in. Modules
compiled from text get private snapshots while their source still exists;
nothing is published beside those temporary sources.  The modules of the
Curry library (config.syslibs) are not compiled either: their objects come
with the installation (make stage), and the swap maps the object of such an
import for its importers (above), so a library module an interpreter runs
(interpret:all, or a stale object) runs compiled once an importer swaps.  A
library source in a dependency view must pass the loader-snapshot
namesake check (issue #168), which authenticates the declared name and
installed source bytes. A dependency view belongs to one job.

The check of the swap.  The child compiles the source as it is when the
child runs.  An edit of the source between the import and the compile would
swap in the code of the edited file, and the module would change meaning
without a load (issue #110).  So a job carries the digest of the ICurry
file (.icy) of the module at the import (curryrt.tiered_file_digest), and the
swap refuses the object when the file differs (the result TIERED_EDITED):
the module stays interpreted, and poll logs it.  A new process reads the
edited source. The check uses the ICurry translation record, so a source
comment edit that leaves the translated program unchanged permits the swap.

The load.  curry.load uses the same adoption as a finished compile, so an
object loaded over the tables the interpreter made stays with them.  The
loader waits for any pending compile and checks the registered file before
opening the object.  prepare_adoption checks the source before the load.

The products. Before a job is submitted, _private_copy verifies disk inputs
against the loaded generation, including its imports. A mismatch skips the
job with one INFO message. The child compiles in its job directory, whose
first search root is a verified view of every loaded import in the captured closure. Products are
hard-linked where possible and copied otherwise. Unloaded names retain
ordinary path resolution. Before publication or adoption, the native swap
checks every dependency fingerprint in the child ABI stamps against that
closure. A mismatch leaves the module interpreted with one INFO message.
The swap publishes the generated file, object and ABI stamp beside an outside
source only when its ICurry digest still matches; otherwise it uses the
private object. Foreign optimizer flags always keep products private.

The flags.  An interpreter whose optimizer flags differ from the ones a
child reads from the environment (the inline budget, _foreign_flags) gets
the object of its private copy and nothing beside the source, which another
process would read (issue #116).

Failure.  When the compile or the load fails, the module stays
interpreted, and the failure is logged once per module (poll).  The results
applied at a safepoint are logged by the next poll: before and after an
evaluation, by wait, and at the exit of the process.  Interpreter.stats
reports the functions swapped and the compiles that failed.

Cancel. A reset or reload cancels the owning interpreter's jobs. Process
shutdown (finish, which sprite-exec --stats calls before its line of statistics)
cancels every job, so a short program never waits for compilation.  The object of a program that ends before its
compile is not written; sprite-make --so writes it.
'''

from ...objects.handle import getHandle
from ...objects import CurryPackage
from ...toolchain import _filenames, _str2module
from ...utility import curryname, formatting
from ...utility.locking import native_metadata
from ...utility.procfork import poisoned
from ..generic import compiler as generic
from . import curryrtbindings as curryrt
from ... import common, config
import atexit, json, itertools, logging, os, shutil, sys, tempfile, time, weakref, warnings
from ...exceptions import CurryWarning

logger = logging.getLogger(__name__)

__all__ = [
    'MODE', 'cancel', 'counts', 'enabled', 'finish', 'has_binding'
  , 'module_loaded', 'pending', 'poll', 'status', 'submit', 'wait', 'wait_for'
  ]

MODE = 'cxx'

def enabled(interp):
  '''Whether interpreted functions use the C++ compiler backend.'''
  from .jit import backend
  return interp.flags['interpret'] != 'off' and interp.flags['jit'] != 'off' \
      and backend(interp) == MODE


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
    self.bindings = set() # (registry identity, module name) for runtime tables
    self.pending = {}    # (registry identity, module name) -> the object of a compile not applied
    self.modules = {}    # (registry identity, module name) -> a weak reference to its module object
    self.records = {}    # (registry identity, module name) -> _Record
    self.private = []    # the directories of the private copies, in order
    self.warned = set()  # the keys of the messages logged once
    self.counter = itertools.count()

_state = _State()

def _key(interp, name):
  return (interp._its.registry_id, name)

def _module_key(moduleobj):
  return _key(getattr(moduleobj, '.interp'), moduleobj.__name__)


def _after_fork_in_child():
  global _state
  # No record may carry an actionable parent job or private product path.
  old = _state
  _state = _State()
  _state.bindings = old.bindings.copy()
  _state.inherited = old.modules.copy()

if hasattr(os, 'register_at_fork'):
  os.register_at_fork(after_in_child=_after_fork_in_child)


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

def warn_mapped_name(name, error):
  _warn_once(
      ('mapped', name)
    , 'the compiled object of module %r was not adopted; the module stays '
      'interpreted: %s', name, error
    )

def _environment(interp, currypath=None):
  '''
  The environment of the child: the flags of a compile, and the search path
  of the import.  The child compiles under the inline budget of the
  interpreter, so the code it swaps in is the code the interpreter ran; a
  budget other than the one the environment names compiles a private copy
  of the source (see the module docstring and submit).
  '''
  from . import msvc
  env = msvc.environment()
  env['SPRITE_INTERPRETER_FLAGS'] = \
      'backend:cxx,interpret:off,debug:%s,inline_budget:%d' % (
          'true' if interp.flags['debug'] else 'false'
        , interp.flags['inline_budget']
        )
  if currypath is not None:
    env['CURRYPATH'] = os.pathsep.join(curryname.makeCurryPath(currypath))
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
  Verify the loaded generation and its imports, then copy disk inputs into
  a compile-job directory. Return the private source and dependency search
  directories. Importing a module itself creates no files here.
  '''
  generation = getattr(imodule, '_loaded_generation', None)
  filename = os.path.abspath(generation.source_spelling
      if generation is not None and generation.source_spelling else imodule.filename)
  relpath = imodule.fullname.replace('.', os.sep) + '.curry'
  if filename.endswith(os.sep + relpath):
    root = filename[:-len(relpath) - 1]
  else:
    root, relpath = os.path.split(filename)
  pending = [generation] if generation is not None else []
  seen = set()
  closure = []
  from ...toolchain._findcurry import verify_product
  from ...toolchain import _curry2icurry
  from .image import digest
  while pending:
    item = pending.pop()
    if id(item) in seen:
      continue
    seen.add(id(item))
    closure.append(item)
    if item.source:
      stem = _filenames.icurryfilename(item.source_spelling)[:-4]
      verify_product(item, stem + '.icy')
      if item.source_info is not None and digest(item.source) != item.source_info.digest:
        raise ValueError('the products of module %s changed since it was loaded; reload it' % item.name)
      for suffix, data in item.texts.items():
        try:
          with open(stem + suffix, 'rb') as stream:
            current = stream.read()
        except OSError:
          current = None
        if current != data:
          raise ValueError('the products of module %s changed since it was loaded; reload it' % item.name)
    if item.image:
      verify_product(item, item.image)
    if item.object:
      verify_product(item, item.object)
      verify_product(item, os.path.splitext(item.object)[0] + '.cpp')
      verify_product(item, item.object + '.abi')
    pending.extend(dep for _, dep in item.imports if dep is not None)
  directory = os.path.join(_tmpdir(), 'private%d' % next(_state.counter))
  copy = os.path.join(directory, relpath)
  os.makedirs(os.path.dirname(copy), exist_ok=True)
  if os.path.isfile(filename):
    shutil.copy2(filename, copy)
    os.chmod(copy, 0o644)
  stem = _filenames.icurryfilename(filename)[:-len('.icy')]
  products = [(generation.image if generation is not None and generation.image else stem + suffix)
      if suffix == '.img' else stem + suffix
      for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source', '.img')]
  productdir = os.path.dirname(_filenames.icurryfilename(copy))
  os.makedirs(productdir, exist_ok=True)
  for product in products:
    if os.path.isfile(product):
      destination = os.path.join(productdir, os.path.basename(stem) + '.img'
          if product.endswith('.img') else os.path.basename(product))
      shutil.copy2(product, destination)
      os.chmod(destination, 0o644)
  if _curry2icurry.in_system_library(filename) and \
      _curry2icurry.source_matches(filename, _filenames.icurryfilename(filename)):
    # A job snapshot is outside the installation. Give copied pins a local
    # completion manifest without changing their installation-owned receipt.
    try:
      _curry2icurry.write_source_receipt(_filenames.icurryfilename(copy),
          generation.source_info.digest if generation is not None and
          generation.source_info is not None else _curry2icurry.source_digest(filename))
    except FileNotFoundError:
      _curry2icurry.invalidate_receipt(_filenames.icurryfilename(copy))
  # Each job owns its resolver view. Never search another job's target
  # before a captured loaded dependency.
  for item in closure:
    if item is generation:
      continue
    target = os.path.join(directory, *item.name.split('.')) + '.curry'
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if item.source and os.path.isfile(item.source):
      shutil.copy2(item.source, target)
      os.chmod(target, 0o644)
    stem = _filenames.icurryfilename(item.source_spelling)[:-4] if item.source else None
    output = _filenames.icurryfilename(target)[:-4]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    for suffix in ('.icy', '.fint', '.icurry', '.icy.imports', '.icy.source', '.img',
                   '.cpp', config.module_object_suffix(), config.module_object_suffix() + '.abi'):
      if suffix in ('.cpp', config.module_object_suffix(), config.module_object_suffix() + '.abi') \
          and not item.object:
        continue # only reuse objects actually loaded and verified above
      if suffix == '.img':
        product = item.image
      elif suffix == config.module_object_suffix() and item.object:
        product = item.object
      elif suffix == config.module_object_suffix() + '.abi' and item.object:
        product = item.object + '.abi'
      elif suffix == '.cpp' and item.object:
        product = os.path.splitext(item.object)[0] + '.cpp'
      else:
        product = stem + suffix if stem else None
      if product and os.path.isfile(product):
        try:
          os.link(product, output + suffix)
        except OSError:
          shutil.copyfile(product, output + suffix)
    if item.source_info is not None and _curry2icurry.in_system_library(item.source_spelling):
      try:
        _curry2icurry.write_source_receipt(output + '.icy', item.source_info.digest)
      except FileNotFoundError:
        _curry2icurry.invalidate_receipt(output + '.icy')
  searchdirs = [directory, root]
  _state.private.append(directory)
  return copy, searchdirs

def _runtime(info):
  '''Whether a table or type was made at run time.'''
  if info is None:
    return False
  return not (info.flags & common.F_STATIC_OBJECT)

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
    _state.bindings.add(_module_key(moduleobj))
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
  record = _state.records.get(_key(interp, name))
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
  Whether the C++ compiler backend can compile this module: not a package, not
  loaded from an object, and has source products.
  '''
  if not enabled(interp):
    return False
  h = getHandle(moduleobj)
  if h.is_package:
    return False
  imodule = h.icurry
  if imodule.metadata.get('cxx.shlib') is not None:
    return False
  filename = imodule.filename
  return bool(filename)

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
  from .materialize import jit_threshold
  curryrt.icurry_set_hot_threshold(interp._its,
      jit_threshold() if interp.flags['jit'] == 'hot' else 0, llvm=False)
  queued = submit(interp, moduleobj, currypath, hot=interp.flags['jit'] == 'hot')
  if queued and interp.flags['jit'] == 'eager':
    start = time.monotonic()
    wait(interp=interp)
    if getHandle(moduleobj).backend_handle.shlib is None:
      if getattr(_state.records.get(_module_key(moduleobj)), 'dependency_mismatch', False):
        return False
      from ...exceptions import CompileError
      raise CompileError('cxx eager: module %s compile failed' % moduleobj.__name__)
    n = _state.records[_module_key(moduleobj)].functions
    logger.info('jit eager: module %s, %d functions, %.1f ms',
        moduleobj.__name__, n, 1000 * (time.monotonic() - start))
  return queued

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
    sofile = _filenames.replacesuffix(_filenames.icurryfilename(filename), config.module_object_suffix())
  icyfile = _filenames.icurryfilename(filename)
  if not os.path.isfile(icyfile):
    icyfile = ''
  digest = '' if not icyfile else curryrt.tiered_file_digest(icyfile)
  record = _Record(moduleobj, sofile, icyfile, digest)
  _state.records[_module_key(moduleobj)] = record
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
    record = _state.records.get(_key(interp, name))
    if record is not None and record.module() is moduleobj:
      out.append((
          name, record.sofile, record.icyfile, record.digest
        , record.publish or ''
        ))
  for depname in imodule.imports:
    visit(depname)
  return out

@native_metadata
def submit(interp, moduleobj, currypath, hot=False):
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
  if name in config.syslibs():
    # The library is left to the objects of the installation (the module
    # docstring, "What is not compiled"); its record, made by module_loaded,
    # names the object the swap of an importer maps.
    logger.info(
        'cxx: module %s is a module of the Curry library; it is not compiled '
        'in the background, its object comes with the installation', name
      )
    return False
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
    from ...exceptions import CompileError
    raise CompileError('jit_backend:cxx needs a C++ compiler; on Windows use Visual Studio 2017 or '
        'newer, or its Build Tools, with the workload "Desktop development with C++" '
        'and the component "C++ Clang tools for Windows", or clang-cl on PATH. Sprite '
        'finds it itself.')
  # The child compiles a private copy (the module docstring, "The
  # products"): nothing is written under the source while it runs.  The
  # digest below is still the one of the ICurry file beside the original:
  # the copy is of this moment.
  try:
    source, searchdirs = _private_copy(imodule)
  except ValueError as exc:
    key = (interp._its.registry_id, 'changed-products', name)
    if key not in _state.warned:
      _state.warned.add(key)
      logger.info('%s; skipping background compilation', exc)
    return False
  currypath = searchdirs + list(
      currypath if currypath is not None else interp.path
    )
  envp = _environment(interp, currypath)
  envp.append('_SPRITE_BACKGROUND_MODULE=' + name)
  sofile = _filenames.replacesuffix(_filenames.icurryfilename(source), config.module_object_suffix())
  logfile = os.path.join(
      _tmpdir(), 'compile%d-%s.log' % (next(_state.counter), name)
    )
  argv = [sys.executable, '-m', 'curry.tools.make', '--so', '-q', source]
  # The ICurry file of the module and its digest: the swap refuses an object
  # of another text (see the module docstring).  The record of the module
  # names the object this job writes, for the swap of its importers.
  record = _record(moduleobj, sofile)
  record.hot = hot
  record.functions = len(steps)
  if not _foreign_flags(interp) and not _str2module.is_temporary(filename):
    record.publish = _filenames.replacesuffix(
        _filenames.icurryfilename(filename), config.module_object_suffix()
      )
  if logger.isEnabledFor(logging.DEBUG):
    logger.debug('Compiling %s in the background: %s', name, ' '.join(argv))
  dispatch = curryrt.cxx_arm if hot else curryrt.tiered_submit
  from ...toolchain import _interfaces, _findcurry
  expected = []
  with _findcurry.resolving(interp):
    pending = [(getattr(imodule, '_loaded_generation', None), sofile)]
    seen = set()
    while pending:
      generation, objectfile = pending.pop()
      if generation is None or id(generation) in seen:
        continue
      seen.add(id(generation))
      fingerprints = _interfaces.object_snapshot(
          [depname for depname, _ in generation.imports], currypath)
      expected.extend(objectfile + '.abi' + '\n' + json.dumps(key) + ': ' + json.dumps(value)
          for key, value in sorted(fingerprints.items()))
      for depname, dep in generation.imports:
        if dep is not None and dep.source:
          # The first search directory is this job's view.
          dep_source = os.path.join(searchdirs[0], *depname.split('.')) + '.curry'
          pending.append((dep, _filenames.replacesuffix(
              _filenames.icurryfilename(dep_source), config.module_object_suffix())))
  imports = []
  for depname, objectfile, icyfile, digest, publish in _import_objects(interp, imodule):
    # A cold import can be compiled by this child before its own job runs.
    # Adoption must use the object produced in this job's dependency view.
    dep_source = os.path.join(searchdirs[0], *depname.split('.')) + '.curry'
    if os.path.isfile(dep_source):
      objectfile = _filenames.replacesuffix(
          _filenames.icurryfilename(dep_source), config.module_object_suffix())
    imports.append((depname, objectfile, icyfile, digest, publish))
  dispatch(
      interp._its, name, argv, envp, logfile, sofile, record.publish or '', steps
    , record.icyfile, record.digest, imports, expected
    )
  _state.pending[_key(interp, name)] = sofile
  _state.modules[_key(interp, name)] = weakref.ref(moduleobj)
  return True

@native_metadata
def _refresh(name, interp=None, registry_id=None):
  '''
  Records the object of a swapped module in its ICurry (cxx.shlib), so the
  handle of the module names it (sofilename) and inspect.getimpl reads the
  compiled code from the generated file beside it.  The module is the one
  the job was submitted for, whichever thread polls and whether or not an
  interpreter was given (issue #115: a poll without one left the ICurry
  without the object). The result's registry selects the owner even when
  another interpreter polls.
  '''
  key = (registry_id, name) if registry_id is not None else _key(interp, name)
  ref = _state.modules.pop(key, None)
  candidates = [] if ref is None else [ref()]
  record = _state.records.get(key)
  if record is not None:
    candidates.append(record.module())
  if interp is not None and interp._its.registry_id == key[0]:
    candidates.append(interp.modules.get(name))
  for moduleobj in candidates:
    if moduleobj is None or isinstance(moduleobj, CurryPackage):
      continue
    h = getHandle(moduleobj)
    shlib = h.backend_handle.shlib
    if shlib is not None and h.icurry.metadata.get('cxx.shlib') is None:
      h.icurry.update_metadata({'cxx.shlib': shlib})
      generation = getattr(h.icurry, '_loaded_generation', None)
      if generation is not None:
        generation.acquire_object(shlib.sofilename())
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
  if interp is not None and enabled(interp):
    inherited = getattr(_state, 'inherited', {})
    for key, ref in list(inherited.items()):
      if key[0] == interp._its.registry_id:
        del inherited[key]
        module = ref()
        if module is not None:
          module_loaded(interp, module, interp.path)
  curryrt.tiered_poll()
  results = curryrt.tiered_results()
  for result in results:
    name = result['module']
    key = (result['registry_id'], name)
    record = _state.records.get(key)
    hot = record is not None and getattr(record, 'hot', False)
    _state.pending.pop(key, None)
    if not result['ok']:
      _state.modules.pop(key, None)
      if hot and not result['error'].startswith(('the object is mapped under this name',
          'the compiled dependency fingerprints')):
        output = result['output'].strip()
        logger.info('cxx hot: module %s compile failed: %s', name,
            (output or result['error']).splitlines()[0])
    for imported in result['mapped']:
      # The swap mapped the object of an import (see the module docstring,
      # "The imports") before it loaded the object of the module: the
      # import runs compiled now, whatever came of the load of the module,
      # and its record names its object.
      logger.info(
          'Mapped the object of %s, an import of %s, in the background'
        , imported, name
        )
      _refresh(imported, interp, result['registry_id'])
    if result['ok']:
      logger.info('module %s: background compile finished in %.2f s, swapped',
          name, result['seconds'])
      if hot:
        logger.info('cxx hot: module %s compiled in %.2f s, swapped',
            name, result['seconds'])
      _refresh(name, interp, result['registry_id'])
    elif result['error'].startswith('the compiled dependency fingerprints'):
      if record is not None:
        record.dependency_mismatch = True
      logger.info('module %s: skipping background adoption (%s)', name, result['error'])
    elif result['error'] == 'the module is no longer loaded':
      logger.info('module %s: background compile not applied (%s)', name, result['error'])
    elif result['error'].startswith('the object is mapped under this name'):
      logger.info('module %s: background compile not applied (%s)', name, result['error'])
      warn_mapped_name(name, result['error'])
    elif result['error'] == curryrt.TIERED_EDITED:
      logger.info('module %s: background compile not applied (%s)', name, result['error'])
      _warn_once(
          (key, 'edited')
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
          (key, 'failed')
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
def pending(name, interp=None):
  '''
  Tells whether a background compile of module ``name`` is queued, running,
  or finished and not yet applied.
  '''
  return _key(interp, name) in _state.pending if interp is not None else any(
      key[1] == name for key in _state.pending)

@native_metadata
def _drop_pending(name, interp=None):
  for key in list(_state.pending):
    if key[1] == name and (interp is None or key[0] == interp._its.registry_id):
      _state.pending.pop(key, None)

def wait_for(name, timeout=None, interp=None):
  '''
  Waits until the background compile of module ``name`` ended and its result
  was applied (the compiles queued before it end first), or until
  ``timeout`` seconds passed.  Returns True when no compile of the module is
  pending.
  '''
  deadline = None if timeout is None else time.monotonic() + timeout
  while pending(name, interp):
    if deadline is None:
      slice_ = 0.25
    else:
      slice_ = min(0.25, max(0.0, deadline - time.monotonic()))
    idle = curryrt.tiered_wait(slice_)
    poll(interp)
    if idle:
      # Nothing is queued or running, and the poll applied what finished:
      # a record left here is stale.
      _drop_pending(name, interp)
    elif deadline is not None and time.monotonic() >= deadline:
      return False
  return True

@native_metadata
def has_binding(name, interp=None):
  '''
  Tells whether the interpreter made a table of module ``name`` in this
  process: the module runs, or ran, interpreted, and an object loaded under
  the name binds to those tables (see the module docstring).
  '''
  return _key(interp, name) in _state.bindings if interp is not None else any(
      key[1] == name for key in _state.bindings)

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
def cancel(interp=None):
  '''Cancel the owner's compiles, or all compiles at process shutdown.'''
  if interp is not None and not hasattr(interp, '_its'):
    return
  curryrt.tiered_cancel(None if interp is None else interp._its)
  for entries in (_state.pending, _state.modules):
    for key in list(entries):
      if interp is None or key[0] == interp._its.registry_id:
        del entries[key]

def finish():
  '''
  Ends the background compiles of the process.  The compiles that ended are
  applied and logged, so that a failure reaches the log of a process that
  evaluates once; then the rest is cancelled and the private directory is
  removed.  The exit of the process calls it, and sprite-exec --stats calls
  it before its line of statistics, so the warning of a failed compile
  precedes the line and the line counts the compile.  A later compile
  starts afresh.
  '''
  if poisoned():
    return
  try:
    poll()
  except Exception:  # pragma: no cover
    pass
  cancel()
  if _state.tmpdir is not None:
    shutil.rmtree(_state.tmpdir, ignore_errors=True)
    _state.tmpdir = None
    _state.private.clear()

atexit.register(finish)
