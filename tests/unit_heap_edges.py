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
      yield waited
    if selected:
      attempted.set()
  def registry(name):
    if getattr(_productlock._local, 'held', {}):
      attempted.set()
    return original_registry(name)
  def callback():
    owned.set()
    assert attempted.wait(2)
    with original_lock(paths[0]):
      pass
  def owner():
    assert entered.wait(2)
    bindings._metadata_call(callback)
  with mock.patch.object(_productlock, 'locked', locked), \\
       mock.patch.object(native, 'registered_names', registry):
    first = threading.Thread(target=lambda: checked(owner))
    second = threading.Thread(target=lambda: checked(action))
    first.start()
    second.start()
    first.join()
    second.join()
  assert paths and not errors, errors
'''

class TestHeapEdges(cytest.TestCase):
  def child(self, code):
    proc = cytest.run_in_subprocess(CHILD + code, 5)
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
    self.child('''
gc.disable()
results = curry.eval(curry.choice(1, 2))
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
    self.child('''
import os, tempfile
from curry import config
from curry.toolchain import plans
curry.reset(backend='cxx', interpret='off', jit='off')
with tempfile.TemporaryDirectory() as directory:
  path = os.path.join(directory, '.curry', config.intermediate_subdir(), 'HeapObject.img')
  os.makedirs(os.path.dirname(path))
  cytest.write_module_image(path, cytest.json_module('HeapObject', 42))
  plan = plans.makeplan(cytest.raw.interp(), plans.MAKE_ALL)
  product_interleaving(lambda: curry.toolchain.makecurry(
      plan, 'HeapObject', [directory]), 'HeapObject.cpp')
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
