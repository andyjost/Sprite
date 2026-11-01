'''
The JIT of the C++ backend: LLVM code from the bytecode of an interpreted
function, compiled in process on llvmlite (the spike of issue #65).

The JIT plugs in where the interpreter plugs in.  The materializer builds
the info tables of a module and attaches the bytecode of each function
(materialize.py, bytecode.py); under the flag ``jit`` set to 'eager' it
queues each function (:func:`enqueue`), and when the module is loaded the
backend compiles the queue (:func:`flush`): one LLVM module whose
functions are read back from the runtime (``icurry_bytecode``, the
constants as link-time symbols), one step function each,
linked with the bitcode of the helpers (src/curryrt/jit/helpers.cpp,
``lib/curryrt-helpers.bc``), optimized, emitted as a relocatable object,
linked with the ORC JIT, and each table swapped to the code
(``icurry_set_step``). Every helper is inlined, so the step holds the
inline code of the runtime headers as compiled code does: the allocation
fast path, the reads of the successors, the rewrite of the redex.  What the
headers declare out of line is a call into the runtime library, resolved
against the library loaded in this process.

The emitter follows the interpreter opcode by opcode (curryrt/icurry.hpp):
a register is an SSA value, a variable is storage of the stack of the step
that the helpers manage, the operand stack of the bytecode is tracked at
emission time, and a case is a head-normalization and a switch over the
branch table; every block of the bytecode ends in a return, an exempt or
a case, so no block has a join.

The JIT is unavailable without llvmlite or without the bitcode, which CMake
builds when it finds clang (WITH_CLANG); the materializer then leaves the
function interpreted and logs the reason once.
'''
from ... import config
from . import bytecode
from . import curryrtbindings as curryrt
import atexit, hashlib, json, logging, os, struct, tempfile, threading, time

__all__ = [
    'Unavailable', 'available', 'compile', 'enqueue', 'flush', 'start_hot_tier'
  , 'statistics'
  ]

logger = logging.getLogger(__name__)

class Unavailable(Exception):
  '''The JIT cannot run in this installation or this process.'''

# A tag below T_CTOR is a status, not a constructor.
T_CTOR = curryrt.T_CTOR

_lock = threading.Lock()
_jit = None       # the JIT of the process, made at the first compile
_reason = None    # why the JIT is unavailable, once known

def available():
  '''Whether the JIT can compile in this process.'''
  try:
    _get()
  except Unavailable:
    return False
  return True

def compile(info, name):
  '''
  Compiles the interpreted function of ``info`` and swaps its step to the
  code.  ``name`` is the full name of the function.  Raises Unavailable when
  the JIT cannot run; any other error is a bug of the emitter.
  '''
  jit = _get()
  with _lock:
    jit.compile_batch([(info, name)])

def enqueue(info, name):
  '''
  Queues the interpreted function of ``info`` for the next :func:`flush`.
  The function runs interpreted until then.  Raises Unavailable when the
  JIT cannot run.
  '''
  jit = _get()
  with _lock:
    jit.pending.append((info, name))

def flush():
  '''
  Compiles the queued functions in one LLVM module and swaps their steps:
  the backend calls it when a module is loaded and before an evaluation.
  One module amortizes the fixed cost of the optimizer and the code
  generator over the functions of a Curry module.
  '''
  jit = _jit
  if jit is None:
    return
  with _lock:
    pending, jit.pending = jit.pending, []
    if pending:
      start = time.perf_counter()
      jit.compile_batch(pending)
      name = pending[0][1].rsplit('.', 1)[0]
      logger.info('jit eager: module %s, %d functions, %.1f ms',
          name, len(pending), 1000 * (time.perf_counter() - start))
  # The swaps the hot tier posted since the last evaluation.
  curryrt.icurry_apply_posted()

_hot_thread = None
_hot_enabled = False

def start_hot_tier(threshold):
  '''
  Starts the hot tier once: the runtime counts the calls of every
  interpreted function, and a thread of this process compiles the functions
  that reach ``threshold`` calls while the evaluation runs (which holds no
  GIL) and posts the swaps, which the scheduler applies at the head of its
  loop, where no step of its state is on the C stack, or the backend before
  the next evaluation.  Raises Unavailable when the JIT cannot run.
  '''
  global _hot_thread, _hot_enabled
  _hot_enabled = True
  _get()
  with _lock:
    curryrt.icurry_set_hot_threshold(int(threshold))
    if _hot_thread is not None:
      return
    _hot_thread = threading.Thread(target=_hot_loop, name='curry-jit', daemon=True)
    _hot_thread.start()
    atexit.register(_stop_hot_tier)

def _stop_hot_tier():
  # Wait for native compilation before Python destroys its LLVM context.
  global _hot_enabled
  _hot_enabled = False
  with _lock:
    pass

def _after_fork_in_child():
  # The threads of the parent do not exist in the child, and a lock that
  # one of them held at the fork would never open: the child starts with a
  # fresh lock and no hot thread, and the next start_hot_tier starts one.
  global _lock, _hot_thread
  _lock = threading.Lock()
  _hot_thread = None

if hasattr(os, "register_at_fork"):
  os.register_at_fork(after_in_child=_after_fork_in_child)

def _hot_loop():
  jit = _jit
  while True:
    if not _hot_enabled:
      time.sleep(0.005)
      continue
    hot = curryrt.icurry_take_hot()
    if not hot:
      time.sleep(0.005)
      continue
    with _lock:
      if not _hot_enabled:
        continue
      try:
        # The names through a binding without the heap lock: an attribute
        # of the table would wait for the evaluation to end.
        start = time.perf_counter()
        jit.compile_batch([(info, jit.names.get(info.address)
            or curryrt.icurry_name(info)) for info in hot], post=True)
        logger.info('jit hot: compiled %s in %.1f ms',
            ', '.join(curryrt.icurry_name(info) for info in hot),
            1000 * (time.perf_counter() - start))
        jit.hot += len(hot)
      except Exception as exc:
        jit.errors += 1
        jit.last_error = '%s: %s' % (type(exc).__name__, exc)
        logger.exception('The hot tier of the JIT failed; the functions stay interpreted')

def statistics():
  '''The counts and the seconds of the JIT of this process.'''
  jit = _jit
  if jit is None:
    return {'functions': 0, 'batches': 0, 'hot': 0, 'errors': 0, 'last_error': None, 'seconds': 0.0, 'linked': 0}
  return {
      'functions': jit.functions, 'batches': jit.batches, 'hot': jit.hot
    , 'errors': jit.errors, 'last_error': jit.last_error, 'seconds': jit.seconds
    , 'linked': jit.linked
    }

def _get():
  global _jit, _reason
  with _lock:
    if _jit is not None:
      return _jit
    if _reason is not None:
      raise Unavailable(_reason)
    try:
      _jit = _JIT()
    except Unavailable as exc:
      _reason = str(exc)
      raise
    return _jit


class _JIT(object):
  '''The LLVM state of the process: the target, the helpers, the ORC JIT.'''
  def __init__(self):
    try:
      import llvmlite.binding as llvm
      from llvmlite import ir
    except ImportError as exc:
      raise Unavailable('llvmlite is not installed (%s)' % exc)
    bitcode = config.jit_bitcode()
    if bitcode is None:
      raise Unavailable(
          'the installation has no bitcode of the JIT helpers '
          '(lib/curryrt-helpers.bc; CMake builds it when it finds clang)'
        )
    self.llvm, self.ir = llvm, ir
    # The headers carry inline assembly (a compiler barrier), so the code
    # generator needs the assembly parser of the target as well.
    for init in ('initialize_native_target', 'initialize_native_asmprinter'
        , 'initialize_native_asmparser'):
      getattr(llvm, init)()
    with open(bitcode, 'rb') as stream:
      self.helpers = llvm.parse_bitcode(stream.read())
    self.helpers.verify()
    # The symbols of the runtime library, for the ORC JIT (the extension
    # loaded the library for itself; the JIT needs it in the process table).
    llvm.load_library_permanently(
        config.installed_path('lib', config.curryrt_lib_name())
      )
    # The target of the bitcode is the target of the JIT: the two must share
    # one data layout, and on Windows the default triple of llvmlite names
    # an ELF layout where clang's bitcode names the COFF one.
    self.triple = self.helpers.triple or llvm.get_default_triple()
    self.target = llvm.Target.from_triple(self.triple)
    self.machine = self.target.create_target_machine(
        cpu=llvm.get_host_cpu_name(), opt=2
      )
    self.data_layout = str(self.machine.target_data)
    # JITLink preserves unwind registration across independently linked objects.
    self.lljit = llvm.create_lljit_compiler(
        self.machine, use_jit_link=os.name != 'nt')
    self.sizes = curryrt.jit_sizes()
    self.trackers = []   # code without an image context
    self.module_keys = {}
    self.object_generations = {}
    self.generations = {}  # key -> linked objects and records
    self.names = {}        # info address -> qualified function name
    self.pending = []    # (info, name) queued for the next flush
    self.modules = {}  # info address -> image batch, replaced on attachment
    self.linked = 0
    self.serial = 0
    self.functions = 0
    self.batches = 0
    self.hot = 0
    self.errors = 0        # the batches of the hot tier that failed
    self.last_error = None
    self.seconds = 0.0

  def compile_batch(self, items, post=False):
    '''
    Compiles the functions of ``items`` in one LLVM module and swaps their
    steps; with ``post`` the swaps are posted for a scheduler to apply at
    its safepoint (the thread of the hot tier), else set at once (the
    thread that loads a module, with no evaluation of its own running).
    '''
    # A hot queue can contain several modules. Each owns one cache entry.
    groups = {}
    for info, name in items:
      context = self.modules.get(info.address)
      groups.setdefault(id(context), (context, []))[1].append((info, name))
    if len(groups) > 1:
      for _, group in groups.values():
        self.compile_batch(group, post=post)
      return
    context = next(iter(groups.values()))[0] if groups else None
    start = time.perf_counter()
    batch = _Batch(self, 'jit%d' % self.serial)
    self.serial += 1
    items = [(info, name) for info, name in items if not curryrt.icurry_is_jit(info)]
    if not items:
      return
    symbols = []
    for info, name in items:
      bc = curryrt.icurry_bytecode(info)
      if bc is None:
        raise ValueError('%s is not an interpreted function' % name)
      if curryrt.icurry_is_jit(info):
        continue   # queued twice, or compiled by an earlier flush
      symbols.append((info, name, batch.emit(name, bc)))
    if not symbols:
      return
    llmod = self.llvm.parse_assembly(str(batch.module))
    t_ir = time.perf_counter()
    llmod.link_in(self.helpers, preserve=True)
    # The helpers are internal to the module once linked: the inliner folds
    # the ones the steps call into them, and the dead-code pass drops the
    # rest, so the optimizer and the code generator see the steps alone.
    for fn in llmod.functions:
      if fn.name.startswith('jit_') and not fn.is_declaration:
        fn.linkage = 'internal'
    llmod.verify()
    t_link = time.perf_counter()
    options = self.llvm.create_pipeline_tuning_options(speed_level=2)
    builder = self.llvm.create_pass_builder(self.machine, options)
    builder.getModulePassManager().run(llmod, builder)
    t_opt = time.perf_counter()
    dump = os.environ.get('SPRITE_JIT_DUMP')
    if dump:
      # The optimized IR and the assembly of each batch, for the study of
      # the code (the spike).
      os.makedirs(dump, exist_ok=True)
      with open(os.path.join(dump, batch.name + '.ll'), 'w') as stream:
        stream.write(str(llmod))
      with open(os.path.join(dump, batch.name + '.s'), 'w') as stream:
        stream.write(self.machine.emit_assembly(llmod))
    records = [(name, symbol, batch.constants[symbol]) for _, name, symbol in symbols]
    obj = self.machine.emit_object(llmod)
    tracker = self.link_object(obj, records, batch.addresses, batch.name)
    if context is None:
      self.trackers.append(tracker)
    else:
      context.objects.append((records, obj))
      self.generations.setdefault(context.key, []).append((tracker, records))
    swap = curryrt.icurry_post_step if post else curryrt.icurry_set_step
    swapped = 0
    for info, name, symbol in symbols:
      if not curryrt.icurry_is_jit(info):
        swap(info, tracker[symbol])
        swapped += 1
    self.functions += swapped
    if context is not None:
      context.store()
    self.batches += 1
    end = time.perf_counter()
    self.seconds += end - start
    logger.debug(
        'JIT batch %s: %d functions, %.1f ms (IR %.1f, link %.1f, optimize %.1f, code %.1f)'
      , batch.name, len(symbols), 1000 * (end - start), 1000 * (t_ir - start)
      , 1000 * (t_link - t_ir), 1000 * (t_opt - t_link), 1000 * (end - t_opt)
      )


  def link_object(self, obj, records, addresses, name):
    library = self.llvm.JITLibraryBuilder().add_object_img(obj).add_current_process()
    for symbol, address in addresses.items():
      library.import_symbol(symbol, address)
    for _, symbol, _ in records:
      library.export_symbol(symbol)
    return library.link(self.lljit, name)


# A single envelope keeps the small index and the native object in one atomic
# publication. No address or path is serialized. Objects are trusted local code,
# like the generated shared objects beside them.
_CACHE_MAGIC = b'SPRTJIT2'
_CACHE_PREFIX = struct.Struct('<8sI')


def _abi_digest():
  from .toolchain import object_digest
  from .image import digest
  return [object_digest(), digest(config.jit_bitcode()), digest(__file__)]


def _cache_key(jit, header):
  import llvmlite
  from .image import VERSION
  facts = [header['name'], header['body'], _abi_digest(),
      llvmlite.__version__, VERSION,
      list(jit.llvm.llvm_version_info), str(jit.llvm.get_host_cpu_name()), jit.triple]
  return hashlib.sha256(json.dumps(facts, sort_keys=True).encode('ascii')).hexdigest()


def _read_cache(path, key):
  with open(path, 'rb') as stream:
    magic, size = _CACHE_PREFIX.unpack(stream.read(_CACHE_PREFIX.size))
    if magic != _CACHE_MAGIC or size > 16 * 1024 * 1024:
      raise ValueError('invalid JIT cache header')
    index = json.loads(stream.read(size))
    payload = stream.read()
  if index['key'] != key:
    raise ValueError('stale JIT object')
  objects = []
  offset = 0
  for entry in index['objects']:
    end = offset + entry['size']
    obj = payload[offset:end]
    if len(obj) != entry['size'] or hashlib.sha256(obj).hexdigest() != entry['digest']:
      raise ValueError('corrupt JIT object')
    objects.append((entry['functions'], obj))
    offset = end
  if offset != len(payload):
    raise ValueError('trailing JIT object data')
  return objects


class _CachedModule:
  '''An attached image's cache slot and independently linked batch objects.'''
  def __init__(self, jit, path, header, items):
    self.jit, self.header, self._key = jit, header, None
    self.path = path
    self.name = header['name']
    self.items = dict((name, info) for info, name in items)
    self.objects = []
    self.local = os.path.splitext(path)[0] + '.jit'
    root = os.environ.get('SPRITE_JIT_CACHE')
    self.root = os.path.expanduser(root) if root else None

  @property
  def key(self):
    if self._key is None:
      self._key = _cache_key(self.jit, self.header)
    return self._key

  @property
  def private(self):
    return os.path.join(self.root, self.name, self.key + '.jit') if self.root else None

  def _install(self, linked):
    count = 0
    for tracker, records in linked:
      for name, symbol, _ in records:
        info = self.items.get(name)
        if info is not None and curryrt.icurry_is_interpreted(info):
          curryrt.icurry_set_step(info, tracker[symbol])
          count += 1
    self.jit.linked += count
    logger.info('jit cache: module %s, linked %d functions', self.name, count)

  def load(self, jit):
    # Reuse linked code across resets, without rereading or hashing its object.
    if jit.generations:
      linked = jit.generations.get(self.key)
      if linked is not None:
        self.objects = jit.object_generations[self.key]
        self._install(linked)
        return True
    paths = [self.local]
    if self.root and os.path.isdir(self.root):
      paths.append(self.private)
    for path in paths:
      if not os.path.isfile(path):
        continue
      linked = []
      try:
        objects = _read_cache(path, self.key)
        for records, obj in objects:
          addresses = {}
          for name, symbol, constants in records:
            bc = curryrt.icurry_bytecode(self.items[name])
            if bc is None:
              raise ValueError('cached function has no bytecode')
            for k in constants:
              addresses[_constant_symbol(symbol, k)] = bc['consts'][k]
          tracker = jit.link_object(obj, records, addresses, 'cached%d' % jit.serial)
          jit.serial += 1
          linked.append((tracker, records))
        self._install(linked)
        self.objects = objects
        jit.generations[self.key] = linked
        jit.object_generations[self.key] = self.objects
        return True
      except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, RuntimeError) as exc:
        for tracker, _ in linked:
          tracker.close()
        logger.debug('jit cache: module %s: %s', self.name, exc)
    logger.info('jit cache: module %s, miss', self.name)
    return False

  def store(self):
    from ...toolchain import _productlock
    from . import image
    entries = [dict(functions=records, size=len(obj),
        digest=hashlib.sha256(obj).hexdigest()) for records, obj in self.objects]
    index = dict(key=self.key, objects=entries)
    encoded = json.dumps(index, sort_keys=True, separators=(',', ':')).encode('ascii')
    data = (_CACHE_PREFIX.pack(_CACHE_MAGIC, len(encoded)) + encoded
        + b''.join(obj for _, obj in self.objects))
    self.jit.object_generations[self.key] = self.objects
    self.jit.module_keys[self.name] = self.key
    names = {r[0] for records, _ in self.objects for r in records}
    for path in (self.local, self.private):
      if path is None:
        continue
      tmp = None
      try:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        if not os.stat(directory).st_mode & 0o222:
          continue
        lockpath = (os.path.join(directory, 'cache.py') if path == self.private
            else os.path.splitext(path)[0] + '.py')
        with _productlock.locked(lockpath):
          # A process must never overwrite a slot belonging to another image.
          if path == self.local and image.read(self.path) != self.header:
            continue
          try:
            existing = _read_cache(path, self.key)
            if {r[0] for records, _ in existing for r in records} >= names:
              return
          except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error):
            pass
          # Writers in this directory use the same module lock. Only remove
          # temporaries whose creating process has gone away.
          for entry in os.scandir(directory):
            if not entry.name.startswith('.jit-'):
              continue
            try:
              pid = int(entry.name.split('-')[1])
              os.kill(pid, 0)
            except ProcessLookupError:
              os.unlink(entry.path)
            except (ValueError, PermissionError):
              pass
          fd, tmp = tempfile.mkstemp(prefix='.jit-%d-' % os.getpid(), dir=directory)
          with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
          os.chmod(tmp, 0o644)
          os.replace(tmp, path)
          tmp = None
          if path == self.private:
            for entry in os.scandir(directory):
              if entry.name.endswith('.jit') and entry.path != path:
                os.unlink(entry.path)
        logger.info('jit cache: module %s, stored %d functions', self.name, len(names))
        return
      except (OSError, ValueError) as exc:
        logger.debug('jit cache: cannot store module %s: %s', self.name, exc)
      finally:
        if tmp is not None:
          os.unlink(tmp)


def attach_cache(path, header, items):
  '''Register an image and link its current object before evaluation.'''
  if os.name == 'nt':
    return  # Persistent objects on Windows belong to the Windows lane.
  jit = _get()
  with _lock:
    context = _CachedModule(jit, path, header, items)
    for info, name in items:
      jit.modules[info.address] = context
      jit.names[info.address] = name
    context.load(jit)
    # A replaced image generation no longer owns any attached steps.
    old = jit.module_keys.get(context.name)
    key = context.key if context.objects else None
    if old is not None and old != key:
      for tracker, _ in jit.generations.pop(old, []):
        tracker.close()
      jit.object_generations.pop(old, None)
    jit.module_keys[context.name] = key


def _constant_symbol(symbol, k):
  return '%s_const_%d' % (symbol, k)


def _identifier(name):
  return ''.join(c if c.isalnum() else '_' for c in name)


# The helpers of src/curryrt/jit/helpers.cpp: name, result, arguments.
# p: a pointer; i: a 32-bit count or index; t: a tag; q: a 64-bit integer;
# d: a double; v: void.
_HELPERS = {
    'jit_cursor': ('v', 'pp'), 'jit_redex': ('p', 'p')
  , 'jit_root_succ': ('p', 'pi'), 'jit_var_succ': ('p', 'pi')
  , 'jit_var_init': ('v', 'p'), 'jit_var_destroy': ('v', 'p')
  , 'jit_var_copy': ('v', 'pp')
  , 'jit_bind_root': ('v', 'ppi'), 'jit_bind_var': ('v', 'ppi')
  , 'jit_freshvar': ('p', 'p'), 'jit_rvalue': ('p', 'p')
  , 'jit_make': ('p', 'ppi'), 'jit_make_partial': ('p', 'ppi')
  , 'jit_cstring': ('p', 'p')
  , 'jit_store_var': ('v', 'ppp'), 'jit_set_succ': ('v', 'pip')
  , 'jit_exempt': ('t', 'p'), 'jit_ret_ref': ('t', 'pp')
  , 'jit_ret_node': ('t', 'pppi'), 'jit_ret_string': ('t', 'pp')
  , 'jit_hnf': ('t', 'pppp'), 'jit_var_target': ('p', 'p')
  , 'jit_is_bigint': ('i', 'p'), 'jit_int_value': ('q', 'p')
  , 'jit_char_value': ('i', 'p'), 'jit_float_value': ('d', 'p')
  , 'jit_integer_compare': ('i', 'pp')
  }

OP = bytecode.OP
ROOT_VAR = bytecode.ROOT_VAR
NO_BRANCH = bytecode.NO_BRANCH


class _Batch(object):
  '''One LLVM module: the helper declarations and the steps of a flush.'''
  def __init__(self, jit, name):
    ir = jit.ir
    self.jit, self.ir, self.name = jit, ir, name
    self.ptr = ir.PointerType()
    self.i8, self.i16 = ir.IntType(8), ir.IntType(16)
    self.i32, self.i64 = ir.IntType(32), ir.IntType(64)
    self.f64 = ir.DoubleType()
    self.types = {
        'p': self.ptr, 'i': self.i32, 't': self.i16, 'q': self.i64
      , 'd': self.f64, 'v': ir.VoidType()
      }
    self.module = ir.Module(name=name)
    self.module.triple = jit.triple
    self.module.data_layout = jit.data_layout
    self.helpers = {}
    for hname, (result, args) in _HELPERS.items():
      fnty = ir.FunctionType(self.types[result], [self.types[a] for a in args])
      self.helpers[hname] = ir.Function(self.module, fnty, name=hname)
    self.count = 0
    self.constants = {}
    self.addresses = {}

  def emit(self, name, bc):
    '''Adds the step of ``name`` to the module; returns its symbol.'''
    symbol = 'step_' + hashlib.sha256(name.encode('utf-8')).hexdigest()
    self.count += 1
    self.constants[symbol] = []
    _Emitter(self, symbol, bc).emit()
    return symbol


class _Emitter(object):
  '''Writes the LLVM function of one bytecode into the module of a batch.'''
  def __init__(self, batch, symbol, bc):
    self.batch, self.jit, self.ir = batch, batch.jit, batch.ir
    self.symbol = symbol
    self.code = list(bc['code'])
    self.consts = list(bc['consts'])
    self.nregs, self.nvars, self.nstack = bc['nregs'], bc['nvars'], bc['nstack']
    self.ptr, self.i8, self.i16 = batch.ptr, batch.i8, batch.i16
    self.i32, self.i64, self.f64 = batch.i32, batch.i64, batch.f64
    self.module = batch.module
    self.helpers = batch.helpers
    self.fn = self.ir.Function(
        self.module, self.ir.FunctionType(self.i16, [self.ptr, self.ptr]), name=symbol
      )
    self.rts, self.C = self.fn.args
    self.rts.name, self.C.name = 'rts', 'C'
    self.blocks = {}   # pc -> block

  def call(self, name, *args):
    return self.builder.call(self.helpers[name], list(args))

  def const(self, k):
    '''A link-time symbol for a constant slot of this image's bytecode.'''
    if not self.consts[k]:
      return self.ir.Constant(self.ptr, None)
    symbol = _constant_symbol(self.symbol, k)
    if symbol not in self.module.globals:
      value = self.ir.GlobalVariable(self.module, self.i8, name=symbol)
      value.linkage = 'external'
      self.batch.constants[self.symbol].append(k)
      self.batch.addresses[symbol] = self.consts[k]
    return self.module.globals[symbol]

  def i32c(self, value):
    return self.ir.Constant(self.i32, value)

  def emit(self):
    ir = self.ir
    entry = self.fn.append_basic_block('entry')
    self.builder = ir.IRBuilder(entry)
    b = self.builder
    sizes = self.jit.sizes
    self.cursor = b.alloca(ir.ArrayType(self.i8, sizes['cursor']), name='cursor')
    self.cursor.align = 8
    vartype = ir.ArrayType(self.i8, sizes['variable'])
    self.vars = []
    # One Variable more when the code indexes a path into a temporary
    # (PUSH_PATH, SET_SUCC with a path): the generated C++ has the same
    # temporaries, and a function without them pays for no Variable.
    nvars = self.nvars + (1 if self.needs_temporary() else 0)
    for v in range(nvars):
      var = b.alloca(vartype, name='var%d' % v)
      var.align = 8
      self.vars.append(var)
    self.tmpvar = self.vars[self.nvars] if nvars > self.nvars else None
    self.cells = [b.alloca(self.ptr, name='cell%d' % v) for v in range(self.nvars)]
    self.regs = [b.alloca(self.ptr, name='reg%d' % r) for r in range(self.nregs)]
    for reg in self.regs:
      b.store(ir.Constant(self.ptr, None), reg)
    self.args = b.alloca(ir.ArrayType(self.ptr, max(self.nstack, 1)), name='args')
    self.call('jit_cursor', self.C, self.cursor)
    for var in self.vars:
      self.call('jit_var_init', var)
    # The blocks: the entry of the code and every target of a case.
    starts = self.block_starts()
    for pc in starts:
      self.blocks[pc] = self.fn.append_basic_block('L%d' % pc)
    b.branch(self.blocks[0])
    for pc in starts:
      self.emit_block(pc)
    return self.module

  def decode(self, pc):
    '''The opcode at ``pc``, its operands, and the length of the unit.'''
    code = self.code
    op = code[pc]
    name = bytecode.OPCODES[op]
    if name == 'CASE_CONS':
      ntab = code[pc + 3]
      return name, code[pc + 1:pc + 4 + ntab], 4 + ntab
    if name == 'CASE_LIT':
      n = code[pc + 4]
      return name, code[pc + 1:pc + 5 + 3 * n], 5 + 3 * n
    fixed, count_at = bytecode._LENGTHS[name]
    length = 1 + fixed
    if count_at is not None:
      length += code[pc + 1 + count_at]
    return name, code[pc + 1:pc + length], length

  def needs_temporary(self):
    '''Whether an opcode indexes a path into a temporary variable.'''
    pc = 0
    while pc < len(self.code):
      name, ops, length = self.decode(pc)
      if name == 'PUSH_PATH' or (name == 'SET_SUCC' and ops[1] > 1):
        return True
      pc += length
    return False

  def block_starts(self):
    starts = {0}
    pc = 0
    while pc < len(self.code):
      name, ops, length = self.decode(pc)
      if name == 'CASE_CONS':
        starts.update(t for t in ops[3:] if t != NO_BRANCH)
      elif name == 'CASE_LIT':
        n = ops[3]
        starts.update(ops[4 + 3 * i + 2] for i in range(n))
      pc += length
    return sorted(starts)

  def emit_block(self, start):
    b = self.builder
    b.position_at_end(self.blocks[start])
    stack = []
    pc = start
    while True:
      name, ops, length = self.decode(pc)
      pc += length
      if self.emit_op(name, ops, stack):
        return      # the block ended in a return, an exempt or a case
      assert pc < len(self.code), 'the bytecode runs off its end'
      assert pc not in self.blocks, 'a block falls into another'

  def path(self, base, path, into):
    '''Binds the variable ``into`` to the end of ``path`` from ``base``.'''
    if base == ROOT_VAR:
      self.call('jit_bind_root', self.cursor, into, self.i32c(path[0]))
    else:
      self.call('jit_bind_var', into, self.vars[base], self.i32c(path[0]))
    for p in path[1:]:
      self.call('jit_bind_var', into, into, self.i32c(p))

  def store_args(self, values):
    '''Writes ``values`` into the argument buffer; returns its address.'''
    b = self.builder
    for i, value in enumerate(values):
      slot = b.gep(self.args, [self.i32c(0), self.i32c(i)], inbounds=True)
      b.store(value, slot)
    return b.gep(self.args, [self.i32c(0), self.i32c(0)], inbounds=True)

  def ret(self, tag):
    '''Destroys the variables and returns ``tag``.'''
    for var in self.vars:
      self.call('jit_var_destroy', var)
    self.builder.ret(tag)

  def emit_op(self, name, ops, stack):
    '''Emits one opcode; returns True when it ends the block.'''
    b = self.builder
    if name == 'LOAD_ROOT_SUCC':
      b.store(self.call('jit_root_succ', self.cursor, self.i32c(ops[1])), self.regs[ops[0]])
    elif name == 'LOAD_VAR_SUCC':
      b.store(self.call('jit_var_succ', self.vars[ops[1]], self.i32c(ops[2])), self.regs[ops[0]])
    elif name == 'BIND_ROOT':
      self.path(ROOT_VAR, ops[2:2 + ops[1]], self.vars[ops[0]])
    elif name == 'BIND_VAR':
      self.path(ops[1], ops[3:3 + ops[2]], self.vars[ops[0]])
    elif name == 'COPY_REG':
      b.store(b.load(self.regs[ops[1]]), self.regs[ops[0]])
    elif name == 'COPY_VAR':
      self.call('jit_var_copy', self.vars[ops[0]], self.vars[ops[1]])
    elif name == 'FREE_REG':
      b.store(self.call('jit_freshvar', self.rts), self.regs[ops[0]])
    elif name == 'PUSH_REG':
      stack.append(b.load(self.regs[ops[0]]))
    elif name == 'PUSH_VAR':
      stack.append(self.call('jit_rvalue', self.vars[ops[0]]))
    elif name == 'PUSH_ROOT':
      stack.append(self.call('jit_redex', self.cursor))
    elif name == 'PUSH_CONST':
      stack.append(self.const(ops[0]))
    elif name == 'PUSH_SUCC':
      if ops[0] == ROOT_VAR:
        stack.append(self.call('jit_root_succ', self.cursor, self.i32c(ops[1])))
      else:
        stack.append(self.call('jit_var_succ', self.vars[ops[0]], self.i32c(ops[1])))
    elif name == 'PUSH_PATH':
      self.path(ops[0], ops[2:2 + ops[1]], self.tmpvar)
      stack.append(self.call('jit_rvalue', self.tmpvar))
    elif name in ('MAKE', 'MAKE_PARTIAL'):
      n = ops[1]
      values = stack[len(stack) - n:]
      del stack[len(stack) - n:]
      helper = 'jit_make' if name == 'MAKE' else 'jit_make_partial'
      stack.append(self.call(helper, self.const(ops[0]), self.store_args(values), self.i32c(n)))
    elif name == 'MAKE_STRING':
      stack.append(self.call('jit_cstring', self.const(ops[0])))
    elif name == 'STORE_REG':
      b.store(stack.pop(), self.regs[ops[0]])
    elif name == 'STORE_VAR':
      v = ops[0]
      self.call('jit_store_var', self.vars[v], self.cells[v], stack.pop())
    elif name == 'SET_SUCC':
      n = ops[1]
      path = ops[2:2 + n]
      value = stack.pop()
      if n == 1:
        self.call('jit_set_succ', self.vars[ops[0]], self.i32c(path[0]), value)
      else:
        self.path(ops[0], path[:-1], self.tmpvar)
        self.call('jit_set_succ', self.tmpvar, self.i32c(path[-1]), value)
    elif name == 'EXEMPT':
      self.ret(self.call('jit_exempt', self.cursor))
      return True
    elif name == 'RET_REF':
      assert len(stack) == 1
      self.ret(self.call('jit_ret_ref', self.cursor, stack.pop()))
      return True
    elif name == 'RET_NODE':
      n = ops[1]
      assert len(stack) == n
      args = self.store_args(stack)
      del stack[:]
      self.ret(self.call('jit_ret_node', self.cursor, self.const(ops[0]), args, self.i32c(n)))
      return True
    elif name == 'RET_STRING':
      self.ret(self.call('jit_ret_string', self.cursor, self.const(ops[0])))
      return True
    elif name == 'CASE_CONS':
      assert not stack
      v, k, ntab = ops[0], ops[1], ops[2]
      table = ops[3:3 + ntab]
      tag = self.call('jit_hnf', self.rts, self.C, self.vars[v], self.const(k))
      default = self.fn.append_basic_block('ret_tag')
      switch = b.switch(tag, default)
      for t, target in enumerate(table):
        if target != NO_BRANCH:
          switch.add_case(self.ir.Constant(self.i16, t), self.blocks[target])
      b.position_at_end(default)
      self.ret(tag)
      return True
    elif name == 'CASE_LIT':
      assert not stack
      v, k, kind, n = ops[0], ops[1], ops[2], ops[3]
      entries = [tuple(ops[4 + 3 * i:7 + 3 * i]) for i in range(n)]
      tag = self.call('jit_hnf', self.rts, self.C, self.vars[v], self.const(k))
      is_status = b.icmp_signed('<', tag, self.ir.Constant(self.i16, T_CTOR))
      status = self.fn.append_basic_block('ret_status')
      value_block = self.fn.append_basic_block('value')
      b.cbranch(is_status, status, value_block)
      b.position_at_end(status)
      self.ret(tag)
      b.position_at_end(value_block)
      node = self.call('jit_var_target', self.vars[v])
      fail = self.fn.append_basic_block('no_branch')
      kind = chr(kind)
      if kind in 'ic':
        if kind == 'i':
          big = self.call('jit_is_bigint', node)
          is_big = b.icmp_unsigned('!=', big, self.i32c(0))
          small = self.fn.append_basic_block('small')
          b.cbranch(is_big, fail, small)
          b.position_at_end(small)
          value = self.call('jit_int_value', node)
        else:
          value = b.zext(self.call('jit_char_value', node), self.i64)
        switch = b.switch(value, fail)
        for lo, hi, target in entries:
          switch.add_case(self.ir.Constant(self.i64, (lo | (hi << 32))), self.blocks[target])
      elif kind == 'f':
        import struct
        value = self.call('jit_float_value', node)
        for lo, hi, target in entries:
          branch_value = struct.unpack('<d', struct.pack('<Q', lo | (hi << 32)))[0]
          hit = b.fcmp_ordered('==', value, self.ir.Constant(self.f64, branch_value))
          miss = self.fn.append_basic_block('miss')
          b.cbranch(hit, self.blocks[target], miss)
          b.position_at_end(miss)
        b.branch(fail)
      elif kind == 'p':
        for lo, hi, target in entries:
          other = self.const(lo | (hi << 32))
          same = b.icmp_signed('==', self.call('jit_integer_compare', node, other), self.i32c(0))
          miss = self.fn.append_basic_block('miss')
          b.cbranch(same, self.blocks[target], miss)
          b.position_at_end(miss)
        b.branch(fail)
      else:
        raise ValueError('a literal case of kind %r' % kind)
      b.position_at_end(fail)
      self.ret(self.call('jit_exempt', self.cursor))
      return True
    else:
      raise ValueError('an unknown opcode %r' % name)
    return False
