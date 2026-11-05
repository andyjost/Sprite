'''
The JIT of the C++ backend: LLVM code from the bytecode of an interpreted
function, compiled in process on llvmlite (the spike of issue #65).

The JIT plugs in where the interpreter plugs in.  The materializer builds
the info tables of a module and attaches the bytecode of each function
(materialize.py, bytecode.py); under the flag ``jit`` set to 'eager' it
queues each function (:func:`enqueue`), and when the module is loaded the
backend compiles the queue (:func:`flush`): batches of bytecode functions,
read back from the runtime (``icurry_bytecode``, the
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
import atexit, contextlib, hashlib, json, logging, os, re, struct, tempfile, threading, time, zlib

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
_group_lock = threading.Lock()
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
  messages = []
  try:
    with _lock:
      jit.compile_batch([(info, name)], messages=messages)
  finally:
    _emit_messages(messages)

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
  Optimizes queued functions in batches, emits independent native objects
  and swaps their steps. The backend calls it at module load and before evaluation.
  One publication holds all new objects of each Curry module.
  '''
  jit = _jit
  if jit is None:
    return
  with _lock:
    pending, jit.pending = jit.pending, []
  if pending:
    start = time.perf_counter()
    _compile_groups(jit, pending)
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
  with _group_lock:
    with _lock:
      pass

def _after_fork_in_child():
  # The threads of the parent do not exist in the child, and a lock that
  # one of them held at the fork would never open: the child starts with a
  # fresh lock and no hot thread, and the next start_hot_tier starts one.
  global _lock, _group_lock, _hot_thread
  _lock = threading.Lock()
  _group_lock = threading.Lock()
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
    try:
      # These bindings read tables without acquiring the heap lock.
      start = time.perf_counter()
      _compile_groups(jit, [(info, jit.names.get(curryrt.icurry_address(info))
          or curryrt.icurry_name(info)) for info in hot], post=True)
      if not _hot_enabled:
        continue
      logger.info('jit hot: compiled %s in %.1f ms',
          ', '.join(curryrt.icurry_name(info) for info in hot),
          1000 * (time.perf_counter() - start))
      jit.hot += len(hot)
    except Exception as exc:
      jit.errors += 1
      jit.last_error = '%s: %s' % (type(exc).__name__, exc)
      logger.exception('The hot tier of the JIT failed; the functions stay interpreted')


def _emit_messages(messages):
  from ...toolchain import _productlock
  _productlock.emit_messages(messages, logger)


def _compile_groups(jit, items, post=False):
  messages = []
  try:
    with _group_lock:
      _compile_groups_locked(jit, items, post, messages)
  finally:
    _emit_messages(messages)

def _compile_groups_locked(jit, items, post, messages):
  # Group and publish by image, but let a waiting resolver enter between
  # optimizer batches. No binding here may acquire the heap under _lock.
  with _lock:
    groups = {}
    for info, name in items:
      context = jit.modules.get(curryrt.icurry_address(info))
      groups.setdefault(id(context), (context, []))[1].append((info, name))
    ordered = list(groups.values())
    if post:
      ordered.sort(key=lambda entry: sum(
          len(curryrt.icurry_bytecode(info)['code']) for info, _ in entry[1]),
          reverse=True)
  for _, group in ordered:
    dirty = set()
    for offset in range(0, len(group), 32):
      with _lock:
        if post and not _hot_enabled:
          for context in dirty:
            if context.dirty:
              context.store(messages=messages)
          return
        context = jit.compile_batch(group[offset:offset + 32], post=post, store=False, messages=messages)
        if context is not None:
          dirty.add(context)
      # Give a resolver waiting for the GIL a chance to take the lock.
      if offset + 32 < len(group):
        time.sleep(0)
    with _lock:
      for context in dirty:
        if context.dirty:
          context.store(messages=messages)


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


# The function attributes of the helpers that name the compiler's target: the
# JIT compiles for the CPU of the host (create_target_machine), and the code
# it makes carries none, so the helpers inline into it under one target.
# Apple's clang also marks every function for stack probing through
# __chkstk_darwin, which LLVM's own AArch64 backend rejects ("Unsupported
# stack probing method"); the code the JIT makes probes no stack.
_TARGET_ATTRIBUTES = re.compile(
    r'\s*"(probe-stack|target-cpu|target-features|tune-cpu)"="[^"]*"')

def _host_helpers(llvm, module):
  '''The helpers module without the attributes of the compiler's target.'''
  text = str(module)
  stripped = _TARGET_ATTRIBUTES.sub('', text)
  if stripped == text:
    return module
  return llvm.parse_assembly(stripped)


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
      self.helpers = _host_helpers(llvm, llvm.parse_bitcode(stream.read()))
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
    curryrt.icurry_set_cache_hook(_resolve_cached)

  def compile_batch(self, items, post=False, store=True, messages=None):
    '''
    Optimizes ``items`` together, emits one object per function and swaps their
    steps; with ``post`` the swaps are posted for a scheduler to apply at
    its safepoint (the thread of the hot tier), else set at once (the
    thread that loads a module, with no evaluation of its own running).
    '''
    if messages is None:
      messages = []
    if post and not _hot_enabled:
      return
    if not items:
      return
    # Callers bound the optimizer batch to one image and at most 32 steps.
    context = self.modules.get(curryrt.icurry_address(items[0][0]))
    swap = curryrt.icurry_post_step if post else curryrt.icurry_set_step
    uncached = []
    for info, name in items:
      if curryrt.icurry_is_jit(info):
        continue
      if context is not None and name in context.cached:
        address = context.resolve(name, messages=messages)
        if address:
          swap(info, address)
        else:
          uncached.append((info, name))
      else:
        uncached.append((info, name))
    items = uncached
    if not items:
      return
    start = time.perf_counter()
    batch = _Batch(self, 'jit%d' % self.serial)
    self.serial += 1
    items = [(info, name) for info, name in items if not curryrt.icurry_is_jit(info)]
    if not items:
      return
    symbols = []
    costs = {}
    for info, name in items:
      bc = curryrt.icurry_bytecode(info)
      if bc is None:
        raise ValueError('%s is not an interpreted function' % name)
      if curryrt.icurry_is_jit(info):
        continue   # queued twice, or compiled by an earlier flush
      symbol = batch.emit(name, bc, context.symbols[name] if context else None)
      costs[symbol] = len(bc['code'])
      symbols.append((info, name, symbol))
    if not symbols:
      return
    llmod = self.llvm.parse_assembly(str(batch.module))
    if post and not _hot_enabled:
      return
    t_ir = time.perf_counter()
    llmod.link_in(self.helpers, preserve=True)
    # The helpers are internal to the module once linked: the inliner folds
    # the ones the steps call into them, and the dead-code pass drops the
    # rest, so the optimizer and the code generator see the steps alone.
    for fn in llmod.functions:
      if fn.name.startswith('jit_') and not fn.is_declaration:
        fn.linkage = 'internal'
    llmod.verify()
    if post and not _hot_enabled:
      return
    t_link = time.perf_counter()
    options = self.llvm.create_pipeline_tuning_options(speed_level=2)
    builder = self.llvm.create_pass_builder(self.machine, options)
    builder.getModulePassManager().run(llmod, builder)
    if post and not _hot_enabled:
      return
    t_opt = time.perf_counter()
    dump = os.environ.get('SPRITE_JIT_DUMP')
    if dump:
      # The optimized IR and the assembly of each batch, for the study of
      # the code (the spike).
      os.makedirs(dump, exist_ok=True)
      with open(os.path.join(dump, batch.name + '.ll'), 'w') as stream:
        text = str(llmod)
        import re
        for _, name, symbol in symbols:
          text = re.sub(r'(?m)^(define [^\n]*@"?' + re.escape(symbol) + r'"?\()',
              lambda match: '; ' + name + '\n' + match.group(0), text)
        stream.write(text)
      with open(os.path.join(dump, batch.name + '.s'), 'w') as stream:
        stream.write(self.machine.emit_assembly(llmod))
    if post:
      # Put substantial hot bodies into service while the smaller steps
      # are still being emitted. Bytecode length is a cheap cost estimate.
      symbols.sort(key=lambda item: costs[item[2]], reverse=True)
    swapped = 0
    for info, name, symbol in symbols:
      if post and not _hot_enabled:
        break
      # The native object is ORC's materialization unit. Retain this step
      # and its reachable helper code only; optimization above is shared.
      unit = llmod.clone()
      for fn in unit.functions:
        if not fn.is_declaration and fn.name != symbol:
          fn.linkage = 'internal'
      prune = self.llvm.create_new_module_pass_manager()
      prune.add_global_dead_code_eliminate_pass()
      prune.run(unit, builder)
      if post and not _hot_enabled:
        break
      records = [(name, symbol, batch.constants[symbol])]
      addresses = {_constant_symbol(symbol, k): batch.addresses[_constant_symbol(symbol, k)]
          for k in batch.constants[symbol]}
      obj = self.machine.emit_object(unit)
      if post and not _hot_enabled:
        break
      library = 'jit%d' % self.serial
      self.serial += 1
      tracker = self.link_object(obj, records, addresses, library)
      if context is None:
        self.trackers.append(tracker)
      else:
        context.objects.append((records, obj))
        context.dirty = True
        self.generations.setdefault(context.key, []).append((tracker, records))
      if not curryrt.icurry_is_jit(info):
        swap(info, tracker[symbol])
        swapped += 1
    self.functions += swapped
    if context is not None and store and context.dirty:
      context.store(messages=messages)
    self.batches += 1
    end = time.perf_counter()
    self.seconds += end - start
    messages.append((logging.DEBUG,
        'JIT batch %s: %d functions, %.1f ms (IR %.1f, link %.1f, optimize %.1f, code %.1f)'
      , (batch.name, len(symbols), 1000 * (end - start), 1000 * (t_ir - start)
      , 1000 * (t_link - t_ir), 1000 * (t_opt - t_link), 1000 * (end - t_opt))
      ))

    return context


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
_CACHE_MAGIC = b'SPRTJIT4'
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


def _open_cache(path):
  '''Pin a generation while allowing publishers to replace its name.'''
  if os.name != 'nt':
    return open(path, 'rb', buffering=0)
  import ctypes
  from ctypes import wintypes
  import msvcrt
  kernel = ctypes.WinDLL('kernel32', use_last_error=True)
  create = kernel.CreateFileW
  create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
  create.restype = wintypes.HANDLE
  close = kernel.CloseHandle
  close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
  # GENERIC_READ; FILE_SHARE_READ | WRITE | DELETE; OPEN_EXISTING.
  # Write sharing also permits corruption tests and metadata-only opens.
  handle = create(os.fsdecode(path), 0x80000000, 0x7, None, 3, 0, None)
  if handle == ctypes.c_void_p(-1).value:
    raise ctypes.WinError(ctypes.get_last_error())
  try:
    fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
  except BaseException:
    close(handle)
    raise
  try:
    # Index reads must not prefetch payload bytes: verify the file's current
    # bytes when an object is resolved, even after an in-place overwrite.
    return os.fdopen(fd, 'rb', buffering=0)
  except BaseException:
    os.close(fd)
    raise


def _process_alive(pid):
  # Match the AOT generation collector: uncertainty keeps the temporary.
  if pid <= 0:
    return True
  if os.name != 'nt':
    try:
      os.kill(pid, 0)
    except ProcessLookupError:
      return False
    except PermissionError:
      pass
    return True
  import ctypes
  from ctypes import wintypes
  kernel = ctypes.WinDLL('kernel32', use_last_error=True)
  opened = kernel.OpenProcess
  opened.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
  opened.restype = wintypes.HANDLE
  wait = kernel.WaitForSingleObject
  wait.argtypes, wait.restype = [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD
  close = kernel.CloseHandle
  close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
  handle = opened(0x100000, False, pid)  # SYNCHRONIZE
  if not handle:
    return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER
  try:
    return wait(handle, 0) != 0  # WAIT_OBJECT_0 means exited
  finally:
    close(handle)


class _Object:
  '''An indexed object; native bytes are read and verified only on demand.'''
  def __init__(self, index, offset, entry):
    self.index, self.offset, self.entry = index, offset, entry
    self.path = index.path

  def read(self):
    fallback = self.entry.get('_fallback')
    try:
      native = self._read()
    except (OSError, ValueError):
      if fallback is None:
        raise
      return fallback.read()
    if fallback is not None:
      fallback.index.release(fallback.entry)
      del self.entry['_fallback']
    return native

  def _read(self):
    # The open descriptor pins this generation across path replacement.
    if self.entry.get('_dropped'):
      raise ValueError('dropped JIT object')
    if '_native' in self.entry:
      return self.entry['_native']
    read = False
    try:
      obj = self.index.read_at(self.offset, self.entry['size'])
      if (len(obj) != self.entry['size']
          or hashlib.sha256(obj).hexdigest() != self.entry['digest']):
        raise ValueError('corrupt JIT object')
      native = zlib.decompress(obj)
      # Publication must not depend on this generation still owning its path.
      self.entry['_native'] = native
      read = True
      return native
    except zlib.error as exc:
      raise ValueError('corrupt compressed JIT object') from exc
    finally:
      self.index.release(self.entry, dropped=not read)



def _object_bytes(obj):
  return obj.read() if isinstance(obj, _Object) else obj


class _IndexedObjects:
  '''Decoded entries, without per-function file views until they are used.'''
  def __init__(self, path, entries, stream):
    self.path, self.entries, self.stream = path, entries, stream
    self.read_lock = threading.RLock()
    self.extra = []
    self.others = []
    self.remaining = len(entries)
    if not entries:
      self.close()

  def release(self, entry, dropped=True):
    if not entry.get('_released'):
      entry['_released'] = True
      self.remaining -= 1
      if dropped:
        entry['_dropped'] = True
      if not self.remaining:
        with self.read_lock:
          self.stream.close()

  def close(self):
    with self.read_lock:
      self.stream.close()
    for other in self.others:
      other.close()

  def read_at(self, offset, size):
    with self.read_lock:
      pread = getattr(os, 'pread', None)
      if pread is not None:
        return pread(self.stream.fileno(), size, offset)
      # A synchronous Windows handle has one file position. Serialize seek
      # and read (and close) so callers observe independent positioned reads.
      self.stream.seek(offset)
      return self.stream.read(size)

  def view(self, entry):
    return (entry['functions'],
        _Object(self, entry['_offset'], entry))

  def __iter__(self):
    for entry in self.entries:
      yield self.view(entry)
    yield from self.extra

  def __len__(self):
    return len(self.entries) + len(self.extra)

  def append(self, pair):
    self.extra.append(pair)


def _read_cache(path, key, check_identity=True):
  stream = _open_cache(path)
  try:
    magic, size = _CACHE_PREFIX.unpack(stream.read(_CACHE_PREFIX.size))
    if magic != _CACHE_MAGIC or size > 16 * 1024 * 1024:
      raise ValueError('invalid JIT cache header')
    index = json.loads(stream.read(size))
    st = os.fstat(stream.fileno())
    if index['key'] != key:
      raise ValueError('stale JIT object')
    if check_identity and (st.st_size, st.st_mtime_ns) != (index['size'], index['mtime_ns']):
      raise ValueError('changed JIT envelope')
    offset = _CACHE_PREFIX.size + size
    names = set()
    for entry in index['objects']:
      records = entry['functions']
      if len(records) != 1 or entry['size'] <= 0 or records[0][0] in names:
        raise ValueError('invalid function object index')
      names.add(records[0][0])
      entry['_offset'] = offset
      offset += entry['size']
    if offset != st.st_size:
      raise ValueError('invalid JIT payload size')
    return _IndexedObjects(path, index['objects'], stream)
  except BaseException:
    stream.close()
    raise

def _resolve_cached(address):
  jit = _jit
  messages = []
  try:
    with _lock:
      context = jit.modules.get(address)
      if context is None or curryrt.icurry_is_jit(context.items[jit.names[address]]):
        return 0
      name = jit.names[address]
      if name in context.failed:
        return 0
      try:
        return context.resolve(name, messages=messages)
      except Exception as exc:
        context.failed.add(name)
        messages.append((logging.WARNING,
            'jit cache: function %s stays interpreted: %s', (name, exc)))
        return 0
  finally:
    _emit_messages(messages)


class _CachedModule:
  '''An attached image's cache slot and independent function objects.'''
  def __init__(self, jit, path, header, items):
    self.jit, self.header, self._key = jit, header, None
    self.path = path
    self.name = header['name']
    self.items = dict((name, info) for info, name in items)
    # The same key means the same image and the same functions outside AOT
    # objects, so these module-local ordinals stay unique across a merge.
    self.symbols = {name: 's%x' % k for k, name in enumerate(sorted(self.items))}
    self.objects = []
    self.dirty = False
    self.index = None
    self.cached = {}
    self.resolved = {}
    self.failed = set()
    self.counted = set()
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

  def object_for(self, name):
    pair = self.cached[name]
    if isinstance(pair, dict):
      if self.index is None:
        raise ValueError('dropped JIT object')
      pair = self.index.view(pair)
      self.cached[name] = pair
    return pair

  def resolve(self, name, messages=None):
    if messages is None:
      messages = []
    if name in self.failed:
      return 0
    start = time.perf_counter()
    try:
      if name not in self.resolved:
        records, obj = self.object_for(name)
        _, symbol, constants = records[0]
        bc = curryrt.icurry_bytecode(self.items[name])
        if bc is None:
          raise ValueError('cached function has no bytecode')
        addresses = {_constant_symbol(symbol, k): bc['consts'][k] for k in constants}
        native = _object_bytes(obj)
        library = 'cached%d' % self.jit.serial
        self.jit.serial += 1
        tracker = self.jit.link_object(native, records, addresses, library)
        self.jit.generations.setdefault(self.key, []).append((tracker, records))
        self.resolved[name] = (tracker, symbol)
      tracker, symbol = self.resolved[name]
      if name not in self.counted:
        self.counted.add(name)
        self.jit.linked += 1
      messages.append((logging.INFO, 'jit cache: module %s, resolved %s, %.3f ms',
          (self.name, name, 1000 * (time.perf_counter() - start))))
      return tracker[symbol]
    except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as exc:
      self.failed.add(name)
      messages.append((logging.WARNING, 'jit cache: function %s stays interpreted: %s', (name, exc)))
      return 0

  def release(self, name):
    if self.index is not None and name in self.cached:
      pair = self.cached[name]
      if isinstance(pair, dict):
        self.index.release(pair)
        entry = pair
      elif isinstance(pair[1], _Object):
        pair[1].index.release(pair[1].entry)
        entry = pair[1].entry
      else:
        return
      fallback = entry.pop('_fallback', None)
      if fallback is not None:
        fallback.index.release(fallback.entry)

  def load(self, jit, messages=None):
    if messages is None:
      messages = []
    # Reuse the index and linked code across resets. Unresolved objects
    # retain their pinned generation and are verified at materialization.
    objects = jit.object_generations.get(self.key)
    if objects is None:
      paths = [self.local]
      if self.root and os.path.isdir(self.root):
        paths.append(self.private)
      for path in paths:
        try:
          found = _read_cache(path, self.key)
          if objects is None:
            objects = found
          else:
            names = {records[0][0]: obj for records, obj in objects}
            objects.others.append(found)
            for records, obj in found:
              if records[0][0] in names:
                names[records[0][0]].entry['_fallback'] = obj
              else:
                objects.append((records, obj))
        except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as exc:
          messages.append((logging.DEBUG, 'jit cache: module %s: %s', (self.name, exc)))
          if path == self.private:
            # A merge may replace local and remove private between our reads.
            # Retry local once to pick up the objects that moved there.
            try:
              found = _read_cache(self.local, self.key)
            except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error):
              pass
            else:
              if objects is not None:
                objects.close()
              objects = found
    if objects is None:
      messages.append((logging.INFO, 'jit cache: module %s, miss', (self.name,)))
      return False
    self.objects = objects
    if isinstance(objects, _IndexedObjects):
      self.index = objects
      self.cached = {entry['functions'][0][0]: entry for entry in objects.entries}
      self.cached.update({pair[0][0][0]: pair for pair in objects.extra})
    else:
      self.cached = {pair[0][0][0]: pair for pair in objects}
    for tracker, records in jit.generations.get(self.key, []):
      name, symbol, _ = records[0]
      self.resolved[name] = (tracker, symbol)
    jit.object_generations[self.key] = objects
    messages.append((logging.INFO, 'jit cache: module %s, indexed %d functions', (self.name, len(self.cached))))
    return True

  def store(self, messages=None):
    if messages is None:
      messages = []
    from ...toolchain import _productlock
    from . import image
    # New code replaces a failed cached object of the same function. Drop
    # duplicates before reading, since the older object may be corrupt.
    latest = {records[0][0]: (records, obj) for records, obj in self.objects}
    # A corrupt object is dropped, not preserved: its function is compiled
    # again when it is hot, and the publication of the others goes ahead.
    objects = []
    for records, obj in latest.values():
      try:
        objects.append((records, _object_bytes(obj)))
      except (OSError, ValueError) as exc:
        messages.append((logging.DEBUG, 'jit cache: module %s drops %s: %s', (self.name, records[0][0], exc)))
    if self.index is not None:
      self.index.close()
    self.objects = objects
    for records, obj in objects:
      name = records[0][0]
      if name in self.cached:
        self.cached[name] = (records, obj)
    self.index = None
    self.dirty = False
    self.jit.object_generations[self.key] = self.objects
    self.jit.module_keys[self.name] = self.key
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
        with contextlib.ExitStack() as locks:
          locks.enter_context(_productlock.locked(lockpath, messages=messages))
          # Local writers take the private lock second, so a fallback writer
          # cannot publish between our merge and removal of that generation.
          if path == self.local and self.private:
            locks.enter_context(_productlock.locked(
                os.path.join(os.path.dirname(self.private), 'cache.py'), messages=messages))
          # A process must never overwrite a slot belonging to another image.
          if path == self.local and image.read(self.path) != self.header:
            continue
          merged = {}
          sources = [path]
          if path == self.local and self.private:
            sources.append(self.private)
          for source in sources:
            try:
              # Copies may lose timestamps; verify every recovered object.
              existing = _read_cache(source, self.key, check_identity=False)
              ours = {records[0][0] for records, _ in objects}
              try:
                for records, obj in existing:
                  if records[0][0] in ours or records[0][0] in merged:
                    continue
                  try:
                    merged[records[0][0]] = (records, _object_bytes(obj))
                  except (OSError, ValueError):
                    pass
              finally:
                existing.close()
            except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error):
              pass
          merged.update({records[0][0]: (records, obj) for records, obj in objects})
          objects = list(merged.values())
          packed = [(records, zlib.compress(obj)) for records, obj in objects]
          entries = [dict(functions=records, size=len(obj),
              digest=hashlib.sha256(obj).hexdigest()) for records, obj in packed]
          # Even seconds round-trip on FAT32 as well as whole-second filesystems.
          stamp = (time.time_ns() // 2000000000) * 2000000000
          index = dict(key=self.key, objects=entries, size=0, mtime_ns=stamp)
          payload = b''.join(obj for _, obj in packed)
          while True:
            encoded = json.dumps(index, sort_keys=True, separators=(',', ':')).encode('ascii')
            size = _CACHE_PREFIX.size + len(encoded) + len(payload)
            if size == index['size']:
              break
            index['size'] = size
          data = _CACHE_PREFIX.pack(_CACHE_MAGIC, len(encoded)) + encoded + payload
          # Writers in this directory use the same module lock. Only remove
          # temporaries whose creating process has gone away.
          for entry in os.scandir(directory):
            if not entry.name.startswith('.jit-'):
              continue
            try:
              pid = int(entry.name.split('-')[1])
              if not _process_alive(pid):
                os.unlink(entry.path)
            except (ValueError, PermissionError):
              pass
          fd, tmp = tempfile.mkstemp(prefix='.jit-%d-' % os.getpid(), dir=directory)
          with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
          os.utime(tmp, ns=(stamp, stamp))
          os.chmod(tmp, 0o644)
          os.replace(tmp, path)
          tmp = None
          # Pin the published generation before another writer can replace it.
          # The attached objects no longer need retained native payloads.
          published = _read_cache(path, self.key)
          self.objects = self.index = published
          self.cached = {entry['functions'][0][0]: entry for entry in published.entries}
          self.jit.object_generations[self.key] = published
          if path == self.local and self.private:
            try:
              os.unlink(self.private)
            except FileNotFoundError:
              pass
          if path == self.private:
            for entry in os.scandir(directory):
              if entry.name.endswith('.jit') and entry.path != path:
                os.unlink(entry.path)
        messages.append((logging.INFO, 'jit cache: module %s, stored %d functions', (self.name, len(objects))))
        return
      except (OSError, ValueError) as exc:
        messages.append((logging.DEBUG, 'jit cache: cannot store module %s: %s', (self.name, exc)))
      finally:
        if tmp is not None:
          os.unlink(tmp)


def attach_cache(path, header, items):
  '''Register an image and its cache index without reading native bytes.'''
  jit = _get()
  messages = []
  try:
    with _lock:
      context = _CachedModule(jit, path, header, items)
      for info, name in items:
        jit.modules[curryrt.icurry_address(info)] = context
        jit.names[curryrt.icurry_address(info)] = name
      context.load(jit, messages=messages)
      # A replaced image generation no longer owns any attached steps.
      old = jit.module_keys.get(context.name)
      key = context.key if context.objects else None
      if old is not None and old != key:
        for tracker, _ in jit.generations.pop(old, []):
          tracker.close()
        detached = jit.object_generations.pop(old, None)
        if isinstance(detached, _IndexedObjects):
          detached.close()
      jit.module_keys[context.name] = key
  finally:
    _emit_messages(messages)
  # Installing entries takes the heap lock. Never wait for the heap while
  # holding the JIT lock: an evaluation may be waiting in a resolver.
  if context.cached:
    curryrt.icurry_install_cached([info for name, info in context.items.items()
        if name in context.cached])


def _constant_symbol(symbol, k):
  return '%s_%x' % (symbol, k)


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
  , 'jit_literal_probe': ('t', 'ppp'), 'jit_hnf': ('t', 'pppp'), 'jit_var_target': ('p', 'p')
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

  def emit(self, name, bc, symbol=None):
    '''Adds the step of ``name`` to the module; returns its symbol.'''
    symbol = symbol or '%ss%x' % (self.name, self.count)
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
      guide = self.ir.Constant(self.ptr, None) if kind & 256 else self.const(k)
      if kind & 512:
        tag = self.call('jit_literal_probe', self.rts, self.C, self.vars[v])
        nonliteral = b.and_(
            b.icmp_signed('>', tag, self.ir.Constant(self.i16, -10)),
            b.icmp_signed('<', tag, self.ir.Constant(self.i16, T_CTOR)))
        dispatch = self.fn.append_basic_block('literal_probe')
        b.cbranch(nonliteral, self.blocks[entries[-1][2]], dispatch)
        b.position_at_end(dispatch)
      else:
        tag = self.call('jit_hnf', self.rts, self.C, self.vars[v], guide)
      is_status = b.icmp_signed('<', tag, self.ir.Constant(self.i16, T_CTOR))
      status = self.fn.append_basic_block('ret_status')
      value_block = self.fn.append_basic_block('value')
      b.cbranch(is_status, status, value_block)
      b.position_at_end(status)
      self.ret(tag)
      b.position_at_end(value_block)
      node = self.call('jit_var_target', self.vars[v])
      fail = self.fn.append_basic_block('no_branch')
      if kind & 512:
        entries.pop()  # The probe's nonliteral target is separate from a miss.
      if kind & 128:
        default_target = entries.pop()[2]
        fallback = self.blocks[default_target]
      else:
        fallback = fail
      kind = chr(kind & 127)
      if kind in 'ic':
        if kind == 'i':
          big = self.call('jit_is_bigint', node)
          is_big = b.icmp_unsigned('!=', big, self.i32c(0))
          small = self.fn.append_basic_block('small')
          b.cbranch(is_big, fallback, small)
          b.position_at_end(small)
          value = self.call('jit_int_value', node)
        else:
          value = b.zext(self.call('jit_char_value', node), self.i64)
        switch = b.switch(value, fallback)
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
        b.branch(fallback)
      elif kind == 'p':
        for lo, hi, target in entries:
          other = self.const(lo | (hi << 32))
          same = b.icmp_signed('==', self.call('jit_integer_compare', node, other), self.i32c(0))
          miss = self.fn.append_basic_block('miss')
          b.cbranch(same, self.blocks[target], miss)
          b.position_at_end(miss)
        b.branch(fallback)
      else:
        raise ValueError('a literal case of kind %r' % kind)
      b.position_at_end(fail)
      self.ret(self.call('jit_exempt', self.cursor))
      return True
    else:
      raise ValueError('an unknown opcode %r' % name)
    return False
