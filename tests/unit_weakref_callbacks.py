'''Deterministic collection during owner operations (issue #185).'''
import cytest
import gc, subprocess, sys, tempfile, unittest, weakref
from curry.typecheck.builder import TypeRecord, IteratorCursor
from curry.typecheck.sigtable import SignatureTable
from curry.backends.generic.eval.evaluator import EvaluationTotals
from curry.toolchain import _str2module


class Node:
  def id(self):
    return id(self)


class CollectOnGet(dict):
  armed = False

  def get(self, key, default=None):
    if self.armed:
      self.armed = False
      gc.collect()
    return super().get(key, default)


def record_gc():
  gc.disable()
  table = TypeRecord()
  table._entries = CollectOnGet()
  first, second = Node(), Node()
  table.put(first, 'first', 'type')
  table.put(second, 'second', 'type')
  second.cycle = second
  second_ref = weakref.ref(second)
  del second
  table._entries.armed = True
  del first  # Queue the first death; draining it collects the second node.
  assert len(table) == 0
  assert second_ref() is None


def record_lookup_gc():
  import threading
  gc.disable()
  table = TypeRecord()
  table._entries = CollectOnGet()
  table._lock = threading.Lock()
  live, dying = Node(), Node()
  table.put(live, 'live', 'type')
  table.put(dying, 'dying', 'type')
  dying.cycle = dying
  dead = weakref.ref(dying)
  del dying
  table._entries.armed = True
  assert table.get(live) == ('live', 'type')
  assert dead() is None
  assert len(table) == 1


class CollectValues(dict):
  armed = False

  def values(self):
    for value in super().values():
      yield value
      if self.armed:
        self.armed = False
        gc.collect()


class CollectSet(set):
  armed = False

  def __iter__(self):
    for value in super().__iter__():
      yield value
      if self.armed:
        self.armed = False
        gc.collect()


class State:
  steps_total, forks_total = 7, 3
  on_read = None
  reads = 0

  def scheduler_counters(self):
    self.reads += 1
    if self.on_read is not None:
      action, self.on_read = self.on_read, None
      action()
    return {'steps': self.steps_total}


def register_state(totals, state):
  # Obtain the production weakref without retaining a generator's strong
  # reference to the state. Seed just the running registry for collection.
  tracked = totals.track(state, iter([1]))
  next(tracked)
  ref = totals._running_refs[id(state)]
  tracked.close()
  totals._steps = totals._forks = 0
  totals._scheduler = None
  totals._running_refs[id(state)] = ref


def totals_collection(view):
  gc.disable()
  totals = EvaluationTotals()
  totals._running_refs = CollectValues()
  live, dying = State(), State()
  register_state(totals, live)
  register_state(totals, dying)
  dying.cycle = dying
  dead = weakref.ref(dying)
  del dying
  version = totals._version
  reads = live.reads
  totals._running_refs.armed = True
  if view == 'running':
    assert totals._running == (live,)
  else:
    assert totals._snapshot() == (7, 3, {'steps': 7})
    assert live.reads == reads + 2  # purge invalidated the first attempt
  assert dead() is None
  # The next critical section purges a death recorded during the traversal.
  assert totals._snapshot() == (7, 3, {'steps': 7})
  assert totals._version == version + 1
  assert len(totals._running_refs) == 1


def totals_running_gc():
  totals_collection('running')


def totals_snapshot_gc():
  totals_collection('snapshot')
  totals_transfer()


def totals_transfer():
  totals = EvaluationTotals()
  first, second = State(), State()
  a = totals.track(first, iter([1]))
  b = totals.track(second, iter([1]))
  next(a)
  next(b)
  # Transfer both running entries after a snapshot captured its baseline.
  # The retry must count the transferred values once, including scheduler data.
  first.on_read = lambda: (a.close(), b.close())
  assert totals._snapshot() == (14, 6, {'steps': 14})
  assert totals._running == ()
  assert totals._snapshot() == (14, 6, {'steps': 14})


def directory_gc():
  gc.disable()
  with tempfile.TemporaryDirectory() as parent:
    import os
    directory = os.path.join(parent, 'module')
    os.mkdir(directory)
    node = Node()
    node.cycle = node
    finalizer = weakref.finalize(node, _str2module._rmdir, directory)
    _str2module._TEMPORARY_DIRS = CollectSet([directory, parent])
    _str2module._TEMPORARY_DIRS.armed = True
    del node
    assert _str2module.is_temporary(os.path.join(parent, 'file'))
    assert not finalizer.alive
    assert not os.path.exists(directory)
    _str2module.is_temporary('unrelated')
    assert directory not in _str2module._TEMPORARY_DIRS
    # The direct error-path call also deletes immediately and queues removal.
    os.mkdir(directory)
    _str2module._TEMPORARY_DIRS.add(directory)
    _str2module._rmdir(directory)
    assert not os.path.exists(directory)
    _str2module.is_temporary('unrelated')
    assert directory not in _str2module._TEMPORARY_DIRS


def directory_logging_gc():
  import logging, os, threading
  gc.disable()
  held, collecting = threading.Event(), threading.Event()
  class Handler(logging.Handler):
    def emit(self, record):
      if record.msg == 'hold':
        held.set()
        assert collecting.wait(3)
        _str2module.is_temporary('unrelated')
  class LoggingSet(CollectSet):
    def __iter__(self):
      for value in super().__iter__():
        yield value
        collecting.set()
  handler = Handler()
  logger = _str2module.logger
  logger.addHandler(handler)
  logger.setLevel(logging.DEBUG)
  with tempfile.TemporaryDirectory() as parent:
    directory = os.path.join(parent, 'module')
    os.mkdir(directory)
    node = Node()
    node.cycle = node
    weakref.finalize(node, _str2module._rmdir, directory)
    del node
    _str2module._TEMPORARY_DIRS = LoggingSet([directory])
    _str2module._TEMPORARY_DIRS.armed = True
    thread = threading.Thread(target=lambda: logger.debug('hold'))
    thread.start()
    assert held.wait(3)
    _str2module.is_temporary('unrelated')
    thread.join(3)
    assert not thread.is_alive()
    assert not os.path.exists(directory)
    _str2module.is_temporary('unrelated')
  logger.removeHandler(handler)


def signatures_gc():
  import types
  gc.disable()
  interp = Node()
  table = SignatureTable(interp)
  table._find = lambda module: None
  table._modules = CollectValues()
  live = types.ModuleType('live')
  dying = types.ModuleType('dying')
  table._entry(live)
  table._entry(dying)
  dying.cycle = dying
  dead = weakref.ref(dying)
  del dying
  table._modules.armed = True
  assert table.modules() == []
  assert dead() is None
  table.modules()
  assert len(table._modules) == 1


def cursor_gc():
  gc.disable()
  class Payload:
    def successor(self, index):
      return self.key
  live = IteratorCursor(None, iter(()), None, None)
  dying = IteratorCursor(None, iter(()), None, None)
  dying.cycle = dying
  dead = weakref.ref(dying)
  del dying
  IteratorCursor._live = CollectOnGet(IteratorCursor._live)
  payload = Payload()
  payload.key = id(live)
  # A plain lock makes an old callback's recursive acquisition hang.
  import threading
  IteratorCursor._live_lock = threading.Lock()
  IteratorCursor._live.armed = True
  assert IteratorCursor.of_node(payload) is live
  assert dead() is None
  assert IteratorCursor.of_node(payload) is live
  assert len(IteratorCursor._live) == 1


def record_concurrent():
  from concurrent.futures import ThreadPoolExecutor
  table = TypeRecord()
  shared = Node()
  def worker(index):
    for i in range(200):
      table.put(shared, index, index)
      scheme, typeexpr = table.get(shared)
      assert scheme == typeexpr
      node = Node()
      table.put(node, i, i)
      old = table._entries[node.id()][0]
      table.put(node, 'replacement', 'replacement')
      # A delayed callback for a superseded reference must do nothing.
      old.__callback__(old)
      assert table.get(node) == ('replacement', 'replacement')
      del node
  with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(worker, range(4)))
  assert len(table) == 1
  del shared
  gc.collect()
  assert len(table) == 0


class TestCallbackLocks(unittest.TestCase):
  def run_child(self, name):
    code = (
        'import faulthandler; faulthandler.dump_traceback_later(5); '
        'import unit_weakref_callbacks as tests; tests.%s()' % name
      )
    result = subprocess.run(
        [sys.executable, '-c', code], capture_output=True, text=True, timeout=10
      )
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_result_type_lookup_collection(self):
    self.run_child('record_lookup_gc')

  def test_result_type_collection(self):
    self.run_child('record_gc')

  def test_evaluation_totals_running_collection(self):
    self.run_child('totals_running_gc')

  def test_evaluation_totals_snapshot_collection(self):
    self.run_child('totals_snapshot_gc')

  def test_directory_logging_collection(self):
    self.run_child('directory_logging_gc')

  def test_signature_collection(self):
    self.run_child('signatures_gc')

  def test_cursor_collection(self):
    self.run_child('cursor_gc')

  def test_temporary_directory_collection(self):
    self.run_child('directory_gc')

  def test_result_type_concurrency_and_identity(self):
    self.run_child('record_concurrent')
