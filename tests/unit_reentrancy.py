'''Reentrant host calls obey the same boundary at every Sprite lock.'''
import cytest # from ./lib; must be first
import unittest

CHILD = '''
import cytest, curry, logging, os, signal, tempfile, threading
from curry.backends.cxx.curryrtbindings import _curryrtbindings as native
from curry.backends.cxx import llvmjit, curryrtbindings
from curry.toolchain import _productlock
curry.reset(backend='cxx', interpret='all', jit='off')
term = curry.term(7)
'''

class TestReentrancy(cytest.TestCase):
  def child(self, code):
    proc = cytest.run_in_subprocess(CHILD + code, 5)
    self.assertEqual(proc.returncode, 0,
        'child status %s\n%s\n%s' % (proc.returncode, proc.stdout, proc.stderr))
    self.assertEqual(proc.stdout.splitlines(), ['ok'])

  @cytest.posix_only('uses a POSIX signal during the worker handoff')
  def test_signal_during_worker_handoff(self):
    for action in ('curry.stats()', 'str(term._node)',
                   'curry.eval(term).one()'):
      with self.subTest(action=action):
        self.child('action = %r\n' % action + '''
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(backend='cxx', interpret='all', jit='off', stack_limit=65536)
term = curry.term(7)
M = curry.import_('StackGuard')
finish = threading.Event()
received = []
def handler(signum, frame):
  try:
    eval(action)
  except curry.ReentrancyError as exc:
    received.append(str(exc))
  finally:
    finish.set()
signal.signal(signal.SIGUSR1, handler)
def callback():
  sent = False
  for i in range(3000):
    if not sent and threading.current_thread() is not threading.main_thread():
      sent = True
      os.kill(os.getpid(), signal.SIGUSR1)
      assert finish.wait(2), 'handler did not finish'
    yield 1
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.lengthInts, callback(), typed=True))
assert [cytest.raw.interp().topython(v) for v in ev.evaluate()] == [3000]
assert ev.rts._escalated and len(received) == 1, received
assert 'Sprite' in received[0]
assert curry.eval(term).one() == 7
print('ok')
''')

  def test_frontend_and_cache_logs_release_product_lock(self):
    for source in ('cache', 'toolchain._curry2icurry', 'toolchain._frontend'):
      with self.subTest(source=source):
        self.child('source = %r\n' % source + '''
from curry import cache
from curry.toolchain import _curry2icurry
with tempfile.TemporaryDirectory() as directory:
  path = os.path.join(directory, 'ReentrantLog.curry')
  with open(path, 'w') as stream:
    stream.write('module ReentrantLog where\\nf :: Int\\nf = 7\\n')
  os.environ['SPRITE_CACHE_FILE'] = os.path.join(directory, 'cache.db')
  cache.reset()
  entered, owned = threading.Event(), threading.Event()
  errors, records = [], []
  def owner():
    assert entered.wait(2)
    def callback():
      owned.set()
      with _productlock.locked(path):
        pass
    try:
      native._metadata_call(callback)
    except BaseException as exc:
      errors.append(exc)
  class Handler(logging.Handler):
    def emit(self, record):
      if records:
        return
      records.append(record.getMessage())
      entered.set()
      assert owned.wait(2)
      assert curry.eval(term).one() == 7
      assert not getattr(_productlock._local, 'held', {})
  logger = logging.getLogger('curry.' + source)
  logger.setLevel(logging.DEBUG)
  logger.addHandler(Handler())
  thread = threading.Thread(target=owner)
  thread.start()
  try:
    _curry2icurry.curry2icurry(path, [directory] + list(curry.path), use_cache=True)
  finally:
    thread.join()
  assert records and not errors, (records, errors)
print('ok')
''')

  def test_logging_handler_under_lock_gets_error(self):
    self.lock_handler(False)

  @cytest.posix_only('uses synchronous POSIX signal delivery')
  def test_signal_handler_under_lock_gets_error(self):
    self.lock_handler(True)

  def lock_handler(self, use_signal):
    self.child('use_signal = %r\n' % use_signal + '''
# Include both the JIT and module caches, and nested product ownership.
P = curry.import_('Prelude')
locks = [llvmjit._lock, llvmjit._group_lock, curry.info(P)._cache_lock,
         cytest.raw.interp().sigtable._lock]
errors = []
metadata = curry.info(P)
symbol = metadata.symbols['id']
results = curry.eval(term)
actions = [lambda: curry.eval(term).one(), lambda: next(results),
           lambda: metadata.symbols, lambda: metadata.types,
           lambda: symbol.signature, lambda: term + 1]
def callback(*args):
  for action in actions:
    try:
      action()
    except curry.ReentrancyError as exc:
      errors.append(str(exc))
    else:
      raise AssertionError('reentrant entry was accepted')
class Handler(logging.Handler):
  def emit(self, record): callback()
logger = logging.getLogger('reentrancy-test')
logger.setLevel(logging.INFO)
logger.addHandler(Handler())
if use_signal:
  signal.signal(signal.SIGUSR1, callback)
with tempfile.TemporaryDirectory() as directory:
  contexts = locks + [_productlock.locked(os.path.join(directory, 'M.icy'))]
  for lock in contexts:
    with lock:
      if use_signal: signal.raise_signal(signal.SIGUSR1)
      else: logger.info('host record')
assert len(errors) == len(contexts) * len(actions), errors
assert next(results) == 7
results.close()
assert len(set(errors)) == 1, errors
assert curry.eval(term).one() == 7
print('ok')
''')

  def test_primitive_callback_can_evaluate(self):
    self.child('''
curryrtbindings.register_primitive('ReentrantCallback.f', 0,
    lambda: curry.eval(term).one())
M = curry.compile('f :: Int\\nf external', name='ReentrantCallback')
assert curry.eval(M.f).one() == 7
print('ok')
''')

  def test_nested_deferral_and_exception_release(self):
    self.child('''
from curry.utility import locking
records = []
class Handler(logging.Handler):
  def emit(self, record):
    assert not locking._held()
    assert curry.eval(term).one() == 7
    records.append(record.getMessage())
logger = logging.getLogger('nested-deferral-test')
logger.setLevel(logging.INFO)
logger.addHandler(Handler())
with tempfile.TemporaryDirectory() as directory:
  try:
    with llvmjit._lock:
      with _productlock.locked(os.path.join(directory, 'M.icy')):
        _productlock.log(logger, logging.INFO, 'product %s', 1)
        locking.log(logger, logging.INFO, 'cache %s', 2)
        assert not records
      assert not records
      raise ValueError('release both scopes')
  except ValueError:
    pass
assert sorted(records) == ['cache 2', 'product 1'], records
assert curry.eval(term).one() == 7
print('ok')
''')
