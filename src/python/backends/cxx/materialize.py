'''
Code for converting the intermediate representation to executable code.

A module loaded from its compiled object carries its info tables and data
types in its metadata (cxx.material; see loader.py), and the materializer
returns them.  A module imported from its ICurry gets info tables and data
types made at run time (Module::create_infotable, Module::create_type).  Under
the interpreter flag ``interpret`` the functions of such a module are
interpreted: the materializer compiles the body of each function into the
bytecode of the runtime (bytecode.py) and attaches it to the info table
(cyrt/icurry.hpp).

With the flag 'off' the plan of the toolchain compiles every module it
loads, but a module imported from an ICurry object (curry.import_(imodule))
never goes through the plan, and its functions got no step: the first
evaluation of one crashed the process (issue #102).  Now such a function
gets the trap step of the runtime (cyrt/module.hpp), and the module compiles
on its first use: the trap calls ``first_use``, which generates the C++ of
the ICurry object in hand and compiles it with the step of the toolchain
that sprite-make --so runs (Cpp2So), loads the object over the shim of the
module (tiered.py) and swaps the steps (cyrt.tiered_adopt); then the step
runs compiled.  So a user who asked for compiled code gets it, and the
plan's own import of an ICurry object, which only generates code
(Json2TargetSource), compiles nothing.

Where the products go (``compile_pending``).  The products beside a source
and the entries of the product cache belong to the translation of the
texts on disk: a later import of the module by name loads them.  So the
C++ goes beside the source, and the object into the product cache, only
when the object in hand is that translation (``is_translation``: the JSON
beside the source, read again and taken through the merge and the passes
of an import, has the structure of the object).  There a current object
whose generated file has the same text is adopted without a compile, and
the product cache is asked before the compiler, as the plan does.  A
transformed object (an experiment of the optimizer, a test), a module
without a source file, and every module of a process whose inline budget
is not the environment's (tiered._foreign_flags; issue #116) compile into a
directory of the process (tiered._tmpdir), which the product cache leaves
out.  A function that still has no code when it is called raises
EvaluationError that names the function and its module and the reason: the
compile failed, or COMPILE_ON_FIRST_USE is False (the hook of the tests).

The body of a function may name a function of its module that the loader has
not reached yet.  The resolver makes the info table of such a function on
demand; the loader finds it and attaches the body when it reaches it.
'''

from ...common import T_FUNC
from ...exceptions import CompileError
from . import bytecode, cyrtbindings as cyrt
from ..generic import compiler as generic
from ... import config, icurry, objects
from ...objects import handle
from ...toolchain import _filenames, _productlock
from ...utility import visitation
import logging, os, time, weakref, zlib

logger = logging.getLogger(__name__)

# The bytecode of every interpreted function, by full name, for
# inspect.getimpl (implementation.py).  An interpreted table lives for the
# life of the process (Module::clear keeps it), so its code is kept as long.
BYTECODE = {}

# Whether a module imported from an ICurry object compiles on its first use
# under interpret:off (first_use).  A test sets it to False to reach the
# error of the trap step.
COMPILE_ON_FIRST_USE = True

def materialize(interp, iobj, moduleobj):
  materializer = Materializer(interp, moduleobj)
  return materializer.materialize(iobj)

class Materializer(object):
  def __init__(self, interp, moduleobj):
    self.interp = interp
    self.moduleobj = moduleobj
    h = handle.getHandle(moduleobj)
    self.M = h.backend_handle
    self.imodule = h.icurry
    self.interpret = interp.flags['interpret'] != 'off'
    if self.interpret:
      # The bytecode of other modules, and a compiled object loaded over a
      # shim (tiered.py), name the tables of this module by address.
      self.M.keep_tables()

  def materialize(self, iobj):
    info = iobj.metadata.get('cxx.material')
    if info is not None:
      assert isinstance(info, (cyrt.DataType, cyrt.InfoTable))
      return info
    else:
      return self.materializeEx(iobj)

  @visitation.dispatch.on('iobj')
  def materializeEx(self, iobj):
    assert False

  @materializeEx.when(icurry.IType)
  def materializeEx(self, itype):
    typeobj = self.M.get_builtin_type(itype.name)
    if typeobj is None:
      infos = [
          self.M.create_infotable(
              ictor.name, ictor.arity, tag
            , ictor.metadata.get('all.flags', 0)
            )
            for tag,ictor in enumerate(itype.constructors)
        ]
      typeobj = self.M.create_type(
          itype.name, infos, itype.metadata.get('all.flags', 0)
        )
    return typeobj

  @materializeEx.when(icurry.IFunction)
  def materializeEx(self, ifun):
    info = self.M.get_builtin_symbol(ifun.name)
    if info is not None and info.tag == T_FUNC:
      return info
    info = self.M.get_infotable(ifun.name)
    if info is None:
      info = self.create_function(ifun)
    # A table with a step keeps it: the function of a module of this name
    # that is still loaded, interpreted or swapped to compiled code (see
    # tiered.py), runs as it did.
    if not info.has_step:
      if self.interpret:
        self.attach(ifun, info)
      else:
        self.trap(info)
    return info

  def create_function(self, ifun):
    '''A function table made at run time, without a step.'''
    return self.M.create_infotable(
        ifun.name, ifun.arity, T_FUNC, ifun.metadata.get('all.flags', 0)
      )

  def attach(self, ifun, info):
    '''Compiles the body of ``ifun`` and attaches it to ``info``.'''
    code = bytecode.compile_function(ifun, self)
    logger.debug(
        'Interpreting %s: %d units, %d constants', ifun.fullname
      , len(code.code), len(code.consts)
      )
    cyrt.icurry_attach(
        info, code.code, code.consts, code.nregs, code.nvars, code.nstack
      )
    BYTECODE[ifun.fullname] = code

  def trap(self, info):
    '''
    Gives ``info`` the trap step and records the module as pending its
    compile on first use (see the module docstring).
    '''
    cyrt.install_trap(info)
    name = self.imodule.fullname
    entry = _PENDING.get(name)
    if entry is None or entry.module() is not self.moduleobj:
      _PENDING[name] = Pending(self.interp, self.moduleobj)

  # The resolver of the emitter (see bytecode.compile_function).
  def symbol(self, fullname):
    '''
    The info table of a function or constructor.  A function of this module
    not yet materialized gets its table now; the loader attaches its body
    when it reaches it.
    '''
    prefix = self.imodule.fullname + '.'
    if fullname.startswith(prefix):
      name = fullname[len(prefix):]
      info = self.M.get_infotable(name)
      if info is not None:
        return info
      ifun = self.imodule.functions.get(name)
      if ifun is not None:
        return self.create_function(ifun)
    try:
      return self.interp.symbol(fullname).info
    except Exception as exc:
      raise CompileError(
          'cannot resolve symbol %r in module %r: %s'
          % (fullname, self.imodule.fullname, exc)
        )

  def tag(self, fullname):
    return self.symbol(fullname).tag

  def datatype(self, fullname):
    typedef = self.symbol(fullname).typedef
    if typedef is None:
      raise CompileError(
          'symbol %r has no data type in module %r'
          % (fullname, self.imodule.fullname)
        )
    return typedef


# The compile on first use
# ========================

class Pending(object):
  '''
  A module imported from an ICurry object under interpret:off: its function
  tables carry the trap step until its first use compiles it.  The module
  and its interpreter are held weakly; a module that was unloaded compiles
  nothing.  ``currypath`` is the search path of the imports of the module
  (module_loaded),
  which the compile of the module needs for its imports.
  '''
  def __init__(self, interp, moduleobj):
    self.interp = weakref.ref(interp)
    self.module = weakref.ref(moduleobj)
    self.currypath = None
    self.compiled = False

  @property
  def name(self):
    moduleobj = self.module()
    return None if moduleobj is None else moduleobj.__name__

# The pending modules by full name.  A module of a name made again replaces
# the entry; an entry whose module is gone is dropped when it is met.
_PENDING = {}

def module_loaded(interp, moduleobj, currypath):
  '''
  Called when the import of a module ends (IBackend.module_loaded).  Records
  the search path of the import for the compile on first use of a pending
  module.
  '''
  entry = _PENDING.get(moduleobj.__name__)
  if entry is not None and entry.module() is moduleobj:
    entry.currypath = list(currypath)

def is_pending(moduleobj):
  '''Tells whether ``moduleobj`` waits for its compile on first use.'''
  entry = _PENDING.get(moduleobj.__name__)
  return entry is not None and entry.module() is moduleobj \
      and not entry.compiled

def _owner(info):
  '''The pending entry of the module that owns the table ``info``, or None.'''
  for name, entry in list(_PENDING.items()):
    moduleobj = entry.module()
    if moduleobj is None:
      del _PENDING[name]
      continue
    M = handle.getHandle(moduleobj).backend_handle
    owned = M.get_infotable(info.name)
    if owned is not None and owned.address == info.address:
      return entry
  return None

def first_use(info):
  '''
  The hook of the trap step (cyrt.set_trap_hook): compiles the module of the
  table ``info`` and swaps its steps, so that the trap runs the compiled
  step.  Returns None when the table has its code now, else the reason it
  has not, which the error of the trap names.  Runs inside a rewrite step,
  on the thread that evaluates.
  '''
  entry = _owner(info)
  if entry is None:
    return 'its module is no longer loaded'
  if entry.compiled:
    # The object was adopted and left this table trapped: the object has
    # no step of this name.  A second compile would not give it one.
    return 'the compiled object has no step for it'
  if not COMPILE_ON_FIRST_USE:
    return 'the compile on first use is turned off ' \
           '(curry.backends.cxx.materialize.COMPILE_ON_FIRST_USE)'
  try:
    compile_pending(entry)
  except (KeyboardInterrupt, SystemExit):
    raise
  except BaseException as exc:
    # CompileError and EvaluationError derive from BaseException.
    logger.warning(
        'cannot compile module %r on its first use: %s', entry.name, exc
      )
    return 'the compile failed: %s' % exc
  if cyrt.is_trapped(info):
    return 'the compiled object has no step for it'
  return None

def compile_pending(entry):
  '''
  Compiles a pending module and swaps its steps: the compile on first use.
  The pending imports of the module compile first, because an object names
  the objects of its imports.  The tables of the module are kept for the
  process and its shim is linked and loaded (tiered.py), so that the object
  binds its tables to the tables the nodes and the Python objects hold.
  The C++ of the ICurry object in hand goes beside the source when the
  object is the translation on disk (is_translation) under the optimizer
  flags of the environment (tiered._foreign_flags), else into a directory
  of the process (see the module docstring); a current object beside the
  source is adopted as it is (current_object), else Cpp2So compiles the
  file, as sprite-make --so does; the runtime loads the object and swaps the
  steps (cyrt.tiered_adopt).  Raises CompileError when a step fails; the
  module then stays trapped.
  '''
  from . import tiered, toolchain
  interp = entry.interp()
  moduleobj = entry.module()
  if interp is None or moduleobj is None:
    raise CompileError('the module is no longer loaded')
  h = handle.getHandle(moduleobj)
  imodule = h.icurry
  M = h.backend_handle
  name = imodule.fullname
  for depname in imodule.imports:
    dep = _PENDING.get(depname)
    if dep is not None and not dep.compiled \
        and dep.module() is interp.modules.get(depname):
      compile_pending(dep)
  cxx = config.cxx_tool()
  if cxx is None:
    raise CompileError(
        'no C++ compiler is installed at %r'
      % config.installed_path('tools', 'cxx')
      )
  currypath = entry.currypath
  if currypath is None:
    currypath = list(interp.path)
  t0 = time.monotonic()
  # Compiled code binds to the tables: they live for the process, as the
  # tables of an interpreted module do (Module::clear), and a module of this
  # name made again takes them back.
  M.keep_tables()
  shim = tiered._register_shim(moduleobj)
  if shim is None:
    raise CompileError(
        'the tables of module %r changed after compiled code bound to them'
      % name
      )
  envp = tiered._environment(interp, currypath)
  if not tiered._load_shim(shim, cxx, envp):
    raise CompileError('the shim of module %r cannot be linked or loaded' % name)
  text = interp.save(moduleobj, None, module_main=False)
  cpp2so = toolchain.Cpp2So(interp)
  # The products go beside the source when the optimizer flags are the
  # environment's and the object in hand is the translation on disk: a
  # budget of the process alone shapes code the ABI stamp does not tell
  # apart (tiered._foreign_flags; issue #116).  The cheap test comes first:
  # is_translation reads the JSON again and runs the passes.
  cppfile = None
  if not tiered._foreign_flags(interp) and is_translation(interp, imodule):
    cppfile = product_file(imodule)
  sofile = None
  if cppfile is not None:
    sofile = current_object(cpp2so, cppfile, text, currypath)
    if sofile is not None:
      logger.info('Adopting the object of %s on its first use: %s', name, sofile)
  else:
    cppfile = process_file(imodule)
  if sofile is None:
    # Under the lock of the products (toolchain._productlock): another
    # process may compile the same module into the same directory.  After
    # a wait the object there may be current.
    with _productlock.locked(cppfile) as waited:
      if waited:
        sofile = current_object(cpp2so, cppfile, text, currypath)
      if sofile is None:
        logger.info('Compiling %s on its first use: %s', name, cppfile)
        with open(cppfile, 'w', encoding='utf-8') as stream:
          stream.write(text)
        # The compile of the source of the module on the path of its
        # imports (is_sourcefile; _findcurry.imports_path).
        sofile = cpp2so(cppfile, currypath, is_sourcefile=True)
  steps = []
  for ifun in imodule.functions.values():
    info = M.get_infotable(ifun.name)
    if info is not None and cyrt.is_trapped(info):
      steps.append((
          ifun.name, generic.mangle(ifun.splitname(), generic.STEP_FUNCTION)
        , info
        ))
  result = cyrt.tiered_adopt(name, [], sofile, steps)
  if not result['ok']:
    output = result['output'].strip()
    raise CompileError(
        'cannot load the object of module %r: %s%s'
      % (name, result['error'], '\n' + output if output else '')
      )
  entry.compiled = True
  shlib = M.shlib
  if shlib is not None and imodule.metadata.get('cxx.shlib') is None:
    imodule.update_metadata({'cxx.shlib': shlib})
  logger.info(
      'Compiled %s on its first use in %.2f s; %d function%s swapped'
    , name, time.monotonic() - t0, result['swapped']
    , '' if result['swapped'] == 1 else 's'
    )

def is_translation(interp, imodule):
  '''
  Tells whether the ICurry object ``imodule`` is the translation of its
  source as it stands on disk.  The JSON beside the source is read again
  (the file, not the parsed cache) and taken through the merge and the
  passes of an import; the object is the translation when the two have one
  structure (icurry.json.dumps, which leaves the metadata out).  False for
  an object without a source file or without a JSON beside it.  The
  products beside a source and the product cache belong to that
  translation, so the products of any other object stay out of both.
  '''
  from ...icurry import json as icurry_json
  from ...toolchain import _loadcurry, _mergecurry
  filename = imodule.filename
  if not filename or not filename.endswith('.curry'):
    return False
  jsonfile = _loadcurry.json_beside(_filenames.replacesuffix(filename, '.cpp'))
  if jsonfile is None:
    return False
  try:
    with open(jsonfile, 'rb') as stream:
      data = stream.read()
    if jsonfile.endswith('.z'):
      data = zlib.decompress(data)
    fresh = icurry_json.loads(data)
  except (OSError, ValueError, zlib.error) as exc:
    logger.debug('cannot read %r (%s)', jsonfile, exc)
    return False
  fresh.filename = filename
  _mergecurry.mergebuiltins(fresh, interp.backend)
  interp.optimize(fresh)
  return icurry_json.dumps(fresh) == icurry_json.dumps(imodule)

def current_object(cpp2so, cppfile, text, currypath):
  '''
  The current object of the module beside ``cppfile``, the generated file
  beside the source, for the generated code ``text``: the object there,
  when its generated file has the text and the object is not stale
  (Cpp2So.is_stale: its stamp and the objects of its imports); else the
  object the product cache places for the texts on disk (Cpp2So.restore),
  when the generated file it places has the text.  None when there is
  neither: the module compiles.  ``currypath`` is the search path of the
  imports of the module (module_loaded).
  '''
  sofile = _filenames.replacesuffix(cppfile, '.so')
  if _text_of(cppfile) == text and os.path.isfile(sofile) \
      and not cpp2so.is_stale(sofile, currypath):
    return sofile
  restored = cpp2so.restore(cppfile, currypath, is_sourcefile=True)
  if restored is not None and _text_of(cppfile) == text:
    return restored
  return None

def _text_of(filename):
  '''The text of a file, or None when it cannot be read.'''
  try:
    with open(filename, 'r', encoding='utf-8') as stream:
      return stream.read()
  except (OSError, UnicodeDecodeError):
    return None

def product_file(imodule):
  '''
  The generated file of the module in the product directory beside its
  source, as the plan writes it, when the module has a source file and the
  directory can be written; else None.
  '''
  filename = imodule.filename
  if filename and filename.endswith('.curry'):
    cppfile = _filenames.replacesuffix(filename, '.cpp')
    directory = os.path.dirname(cppfile)
    try:
      os.makedirs(directory, exist_ok=True)
    except OSError:
      pass
    else:
      if os.access(directory, os.W_OK):
        return cppfile
  return None

def process_file(imodule):
  '''
  The generated file of the module in the directory of the process
  (tiered._tmpdir), in the layout of a product directory, which the
  toolchain reads the module name from.  The product cache leaves the
  directory out (_productcache.excluded).
  '''
  from . import tiered
  directory = os.path.join(
      tiered._tmpdir(), 'firstuse', imodule.fullname, '.curry'
    , config.intermediate_subdir()
    )
  os.makedirs(directory, exist_ok=True)
  return os.path.join(directory, imodule.name + '.cpp')

cyrt.set_trap_hook(first_use)
