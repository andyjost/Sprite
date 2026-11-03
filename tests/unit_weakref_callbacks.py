'''Deterministic collection inside callback locks (issue #185).'''
import cytest
import gc, subprocess, sys, tempfile, unittest, weakref
from curry.typecheck.builder import TypeRecord
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
  del first  # forget -> get -> collect -> forget, on the same thread
  assert second_ref() is None
  assert len(table) == 0


def totals_reentry():
  totals = EvaluationTotals()
  class State:
    steps_total = forks_total = 0
    def scheduler_counters(self):
      return None
  state = State()
  tracked = totals.track(state, iter([1]))
  assert next(tracked) == 1
  ref = totals._running_refs[id(state)]
  version = totals._version
  with totals._lock:
    ref.__callback__(ref)
  assert totals._running == ()
  assert totals._version == version + 1
  tracked.close()


def directory_gc():
  gc.disable()
  with tempfile.TemporaryDirectory() as parent:
    import os
    directory = os.path.join(parent, 'module')
    os.mkdir(directory)
    node = Node()
    node.cycle = node
    finalizer = weakref.finalize(node, _str2module._rmdir, directory)
    with _str2module._dirs_lock:
      _str2module._TEMPORARY_DIRS.add(directory)
      del node
      gc.collect()
    assert not finalizer.alive
    assert directory not in _str2module._TEMPORARY_DIRS
    assert not os.path.exists(directory)


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

  def test_result_type_collection(self):
    self.run_child('record_gc')

  def test_evaluation_totals_reentry(self):
    self.run_child('totals_reentry')

  def test_temporary_directory_collection(self):
    self.run_child('directory_gc')

  def test_result_type_concurrency_and_identity(self):
    self.run_child('record_concurrent')
