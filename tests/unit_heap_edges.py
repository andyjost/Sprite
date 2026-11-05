'''Heap waits and Python callbacks must follow metadata lock release.'''
import cytest # from ./lib; must be first

CHILD = '''
import cytest, curry, gc, logging, threading, types
from contextlib import contextmanager
from unittest import mock
from curry.backends.cxx import llvmjit, curryrtbindings as native
from curry.backends.cxx.curryrtbindings import _curryrtbindings as bindings
from curry.objects.terms import Term
from curry.objects.handle import getHandle
curry.reset(backend='cxx', interpret='all', jit='off')
errors = []
def checked(action):
  try:
    action()
  except BaseException as exc:
    errors.append(exc)

def product_interleaving(action, basename):
  from curry.toolchain import _productlock
  entered, owned, attempted = [threading.Event() for _ in range(3)]
  from curry.backends.cxx import image
  original_tag = native.InfoTable.tag
  original_lock, original_registry = _productlock.locked, native.registered_names
  paths = []
  @contextmanager
  def locked(path, *args, **kwds):
    selected = not paths and path.endswith(basename)
    with original_lock(path, *args, **kwds) as waited:
      if selected:
        paths.append(path)
        entered.set()
        assert owned.wait(2)
      try:
        yield waited
      finally:
        if selected:
          attempted.set()
  def registry(name):
    if getattr(_productlock._local, 'held', {}):
      attempted.set()
    return original_registry(name)
  def tag(self):
    if getattr(_productlock._local, 'held', {}):
      attempted.set()
    # Force heap ownership for the descriptor read, including binding builds
    # whose property helpers do not propagate precall attributes.
    return bindings._metadata_call(lambda: original_tag.__get__(self, native.InfoTable))
  def callback():
    owned.set()
    assert attempted.wait(2)
    with original_lock(paths[0]):
      pass
  def owner():
    assert entered.wait(2)
    bindings._metadata_call(callback)
  with mock.patch.object(_productlock, 'locked', locked), \\
       mock.patch.object(native, 'registered_names', registry), \\
       mock.patch.object(native.InfoTable, 'tag', property(tag)):
    first = threading.Thread(target=lambda: checked(owner))
    second = threading.Thread(target=lambda: checked(action))
    first.start()
    second.start()
    first.join()
    second.join()
  assert paths and not errors, errors
'''

class TestHeapEdges(cytest.TestCase):
  def child(self, code, timeout=5):
    proc = cytest.run_in_subprocess(CHILD + code, timeout)
    self.assertEqual(proc.returncode, 0,
        'child status %s\n%s\n%s' % (proc.returncode, proc.stdout, proc.stderr))
    self.assertEqual(proc.stdout.splitlines(), ['ok'])

  def test_symbol_construction_releases_cache_lock_before_heap(self):
    self.child('''
P = curry.import_('Prelude')
metadata = curry.info(P)
metadata._terms.clear()
info = getHandle(P).symbols['Just']
owned, constructing = threading.Event(), threading.Event()
original = Term.__init__
def construct(self, *args, **kwds):
  if threading.current_thread().name == 'producer':
    constructing.set()
  return original(self, *args, **kwds)
def callback():
  owned.set()
  assert constructing.wait(2)
  assert Term.from_symbol(info, P) is not None
def producer():
  assert owned.wait(2)
  assert Term.from_symbol(info, P) is not None
with mock.patch.object(Term, '__init__', construct):
  first = threading.Thread(target=lambda: checked(lambda: bindings._metadata_call(callback)))
  second = threading.Thread(target=lambda: checked(producer), name='producer')
  first.start()
  second.start()
  first.join()
  second.join()
assert not errors, errors
print('ok')
''')

  def test_abandoned_results_do_not_read_heap_counters_during_gc(self):
    self.collector('curry.eval(curry.choice(1, 2))')

  def test_abandoned_stream_uses_deferred_disposal_during_gc(self):
    self.collector("curry.stream(curry.import_('StreamChannel').three)")

  def collector(self, expression):
    self.child('''
gc.disable()
results = ''' + expression + '''
next(results)
cycle = [results]
cycle.append(cycle)
del results, cycle
owned, collecting = threading.Event(), threading.Event()
def callback():
  owned.set()
  assert collecting.wait(2)
  with llvmjit._lock:
    pass
def collect():
  assert owned.wait(2)
  with llvmjit._lock:
    collecting.set()
    gc.collect()
first = threading.Thread(target=lambda: checked(lambda: bindings._metadata_call(callback)))
second = threading.Thread(target=lambda: checked(collect))
first.start()
second.start()
first.join()
second.join()
assert not errors, errors
assert cytest.raw.interp()._evaluation_totals.steps > 0
print('ok')
''')

  def test_jit_resolver_logging_can_reenter_evaluation(self):
    self.child('''
term = curry.term(7)
jit = types.SimpleNamespace(modules={}, names={1: 'M.f'}, pending=[], linked=0)
context = object.__new__(llvmjit._CachedModule)
context.jit, context.name = jit, 'M'
context.items, context.failed = {'M.f': None}, set()
context.resolved = {'M.f': ({'step': 123}, 'step')}
context.counted = set()
jit.modules[1] = context
class ReenterError(ValueError):
  def __str__(self):
    llvmjit.flush()
    return 'reentrant error formatting'
class Reenter(logging.Handler):
  def emit(self, record):
    record.getMessage()
    llvmjit.flush()
    assert curry.eval(term).one() == 7
handler = Reenter()
llvmjit.logger.addHandler(handler)
llvmjit.logger.setLevel(logging.INFO)
with mock.patch.object(llvmjit, '_jit', jit), \\
     mock.patch.object(native, 'icurry_is_jit', return_value=False), \\
     mock.patch.object(native, 'icurry_apply_posted', return_value=0):
  assert llvmjit._resolve_cached(1) == 123
  context.resolved.clear()
  with mock.patch.object(context, 'object_for', side_effect=ReenterError()):
    assert llvmjit._resolve_cached(1) == 0
llvmjit.logger.removeHandler(handler)
print('ok')
''')

  def test_product_registry_snapshot_precedes_image_lock(self):
    self.child('''
import os, tempfile
from curry import config
with tempfile.TemporaryDirectory() as directory:
  path = os.path.join(directory, '.curry', config.intermediate_subdir(), 'HeapImage.img')
  os.makedirs(os.path.dirname(path))
  product_interleaving(lambda: cytest.write_module_image(
      path, cytest.json_module('HeapImage', 42)), 'HeapImage.img')
print('ok')
''')

  def test_product_registry_snapshot_precedes_object_lock(self):
    self.object_compile(False)

  def test_product_compilation_logging_can_reenter(self):
    self.object_compile(True)

  def object_compile(self, log_callbacks):
    self.child('log_callbacks = %r\n' % log_callbacks + '''
import os, tempfile
from curry import config
from curry.toolchain import plans
curry.reset(backend='cxx', interpret='off', jit='off')
with tempfile.TemporaryDirectory(dir=os.getcwd()) as directory:
  path = os.path.join(directory, '.curry', config.intermediate_subdir(), 'HeapObject.img')
  os.makedirs(os.path.dirname(path))
  os.environ['SPRITE_PRODUCT_CACHE'] = os.path.join(directory, 'cache')
  cytest.write_module_image(path, cytest.json_module('HeapObject', 42))
  plan = plans.makeplan(cytest.raw.interp(), plans.MAKE_ALL & ~plans.MAKE_TARGET_OBJECT)
  cpp = curry.toolchain.makecurry(plan, 'HeapObject', [directory])
  from curry.backends.cxx.toolchain import Cpp2So
  from curry.backends.cxx import toolchain
  from curry.toolchain import _productlock, _productcache
  records = []
  class Reenter(logging.Handler):
    def emit(self, record):
      assert not getattr(_productlock._local, 'held', {})
      llvmjit.flush()
      assert curry.eval(curry.term(7)).one() == 7
      records.append(record.msg)
  handler = Reenter()
  for logger in (toolchain.logger, _productcache.logger):
    if log_callbacks:
      logger.addHandler(handler)
      logger.setLevel(logging.DEBUG)
  product_interleaving(lambda: Cpp2So(cytest.raw.interp())(cpp, [directory]), 'HeapObject.cpp')
  assert _productcache.counts['stored'] > 0
  if log_callbacks:
    assert any('Compil' in message for message in records)
    assert any('cache stored' in message for message in records)
  for logger in (toolchain.logger, _productcache.logger):
    logger.removeHandler(handler)
print('ok')
''', timeout=120)

  def test_imported_constructor_tags_precede_image_lock(self):
    """Use a guarded hook in place of the unguarded native tag descriptor.

    A baseline timeout shows the inversion with that hook, not a deadlock of
    the unchanged baseline descriptor, whose property heap guard is ineffective.
    """
    self.child('''
import os, tempfile
from curry.backends.cxx import image
from curry import icurry as I, config
curry.import_('Prelude')
with tempfile.TemporaryDirectory() as directory:
  path = os.path.join(directory, '.curry', config.intermediate_subdir(), 'HeapCase.img')
  os.makedirs(os.path.dirname(path))
  branch = I.IConsBranch('Prelude.True', 0,
      I.IBlock([], [], I.IReturn(I.ILit(I.IInt(42)))))
  function = I.IFunction('HeapCase.goal', 1, body=I.IFuncBody(I.IBlock(
      [I.IVarDecl(1)], [I.IVarAssign(1, I.IVarAccess(0, [0]))],
      I.ICaseCons(1, [branch, I.IConsBranch('Prelude.False', 0,
          I.IBlock([], [], I.IReturn(I.ILit(I.IInt(0)))))]))))
  module = I.IModule('HeapCase', ['Prelude'], [], [function], filename=path[:-4] + '.curry')
  product_interleaving(lambda: image.write(cytest.raw.interp(), module, path=path), 'HeapCase.img')
  header = image.read(path)
  assert header['name'] == 'HeapCase'
  cytest.raw.import_(image.attach(cytest.raw.interp(), module.filename, path, header))
  for argument, expected in ((True, '42'), (False, '0')):
    goal = cytest.raw.expr(cytest.raw.interp().symbol('HeapCase.goal'), argument)
    assert [str(value) for value in cytest.raw.values(goal)] == [expected]
print('ok')
''')

  def test_product_registry_snapshot_precedes_contender_stamp_check(self):
    self.child('''
import os, tempfile
from curry import config
from curry.toolchain import plans
from curry.backends.cxx import toolchain
curry.reset(backend='cxx', interpret='off', jit='off')
with tempfile.TemporaryDirectory() as directory:
  os.environ['SPRITE_PRODUCT_CACHE'] = ''
  path = os.path.join(directory, '.curry', config.intermediate_subdir(), 'HeapContender.img')
  os.makedirs(os.path.dirname(path))
  cytest.write_module_image(path, cytest.json_module('HeapContender', 42))
  plan = plans.makeplan(cytest.raw.interp(), plans.MAKE_ALL)
  curry.toolchain.makecurry(plan, 'HeapContender', [directory])
  cpp = path[:-4] + '.cpp'
  step = toolchain.Cpp2So(cytest.raw.interp())
  original = step.product_snapshot
  calls = []
  def snapshot(filename):
    calls.append(filename)
    return None if len(calls) == 1 else original(filename)
  checked_stamps = []
  stamp = step.stamp_is_current
  def current(*args, **kwds):
    checked_stamps.append(True)
    return stamp(*args, **kwds)
  with mock.patch.object(step, 'product_snapshot', snapshot), \
       mock.patch.object(step, 'stamp_is_current', current):
    product_interleaving(lambda: step(cpp, [directory]), 'HeapContender.cpp')
  assert checked_stamps
print('ok')
''')

  @cytest.posix_only('advisory process-lock contention')
  def test_jit_publication_contention_logging_can_reenter(self):
    """Exercise deferred publication logging through the messages API.

    The unchanged baseline rejects store(messages=...) before contention;
    that API failure alone is not evidence of a baseline deadlock.
    """
    self.child('''
import os, tempfile
from curry.toolchain import _productlock
from curry.backends.cxx import image
term = curry.term(7)
seen = []
class Reenter(logging.Handler):
  def emit(self, record):
    record.getMessage()
    llvmjit.flush()
    assert curry.eval(term).one() == 7
    seen.append(record.msg)
handler = Reenter()
_productlock.logger.addHandler(handler)
_productlock.logger.setLevel(logging.INFO)
with tempfile.TemporaryDirectory() as directory:
  jit = types.SimpleNamespace(object_generations={}, module_keys={}, pending=[])
  context = llvmjit._CachedModule(jit, os.path.join(directory, 'M.img'), {'name': 'M'}, [])
  context._key = 'test-key'
  original = _productlock.fcntl.flock
  contended = []
  def flock(fd, flags):
    if flags & _productlock.fcntl.LOCK_NB and not contended:
      contended.append(True)
      raise BlockingIOError()
    return original(fd, flags)
  messages = []
  with mock.patch.object(_productlock.fcntl, 'flock', flock), \
       mock.patch.object(llvmjit, '_jit', jit), \
       mock.patch.object(image, 'read', return_value=context.header):
    try:
      with llvmjit._group_lock, llvmjit._lock:
        context.store(messages=messages)
        assert not seen
    finally:
      llvmjit._emit_messages(messages)
  assert contended and seen
_productlock.logger.removeHandler(handler)
print('ok')
''')

  def test_value_counts_do_not_call_heap_taking_counter_bindings(self):
    self.child('''
term = curry.choice(1, 2)
def unexpected(*args):
  raise AssertionError('counter binding called during value consumption')
with mock.patch.object(native.RuntimeState, 'steps_total', property(unexpected)), \
     mock.patch.object(native.RuntimeState, 'forks_total', property(unexpected)), \
     mock.patch.object(native.RuntimeState, 'scheduler_counters', unexpected):
  results = curry.eval(term)
  assert next(results) in (1, 2)
  results.close()
totals = cytest.raw.interp()._evaluation_totals
assert totals.steps > 0 and totals.forks > 0
print('ok')
''')

  def test_posted_swaps_wait_for_heap_ownership(self):
    self.child('''
import time
owned, release, applied = [threading.Event() for _ in range(3)]
def callback():
  owned.set()
  assert release.wait(2)
def apply():
  assert owned.wait(2)
  native.icurry_apply_posted()
  applied.set()
first = threading.Thread(target=lambda: checked(lambda: bindings._metadata_call(callback)))
second = threading.Thread(target=lambda: checked(apply))
first.start()
assert owned.wait(2)
waits = bindings._test_heap_waits()
second.start()
try:
  deadline = time.monotonic() + 2
  while bindings._test_heap_waits() == waits and not applied.is_set():
    assert time.monotonic() < deadline
    applied.wait(.001)
  assert not applied.is_set(), 'posted swaps ran while another thread owned the heap'
finally:
  release.set()
  first.join()
  second.join()
assert applied.is_set() and not errors, errors
print('ok')
''')
