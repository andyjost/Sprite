'''Deep evaluations escalate from the caller's stack to the heap's worker.'''
import cytest # from ./lib; must be first
import curry, json, unittest

CHILD = '''
import cytest, curry, json
from curry.backends.generic.eval.evaluator import Evaluator
curry.reset(backend='cxx', interpret='off', **%(flags)r)
M = curry.import_('StackGuard')
def run(n):
  ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, n, typed=True))
  values = [cytest.raw.interp().topython(v) for v in ev.evaluate()]
  return values, ev.rts.steps_total
'''

@unittest.skipUnless(curry.flags['backend'] == 'cxx', 'C++ runtime escalation')
class TestIssue153(cytest.TestCase):
  def child(self, code, **flags):
    proc = cytest.run_in_subprocess(
        CHILD % {'flags': flags} + code, 120, address_space=4 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout.splitlines()

  @cytest.skipIfGcStress('a million live cells under a collection per step')
  def test_deep_lengths(self):
    for n in (100000, 1000000):
      with self.subTest(n=n):
        line, = self.child('print(json.dumps(run(%d)[0]))' % n)
        self.assertEqual(json.loads(line), [n])

  def test_disabled_worker_keeps_guard_diagnostic(self):
    lines = self.child('''
try:
  run(100000)
except curry.StackLimitError as error:
  print(error)
''', worker_stack=None)
    self.assertEqual(len(lines), 1)
    self.assertRegex(lines[0], r'^stack limit of \d+ bytes exceeded \(flag stack_limit\)')

  def test_tiny_reservation_names_attempt_and_floor(self):
    lines = self.child('''
try:
  run(10000)
except curry.StackLimitError as error:
  print(error)
''', stack_limit=65536, worker_stack=1)
    self.assertEqual(len(lines), 1)
    self.assertIn('worker_stack', lines[0])
    self.assertIn('attempted sizes in bytes: 1', lines[0])
    self.assertIn('67108864', lines[0])

  def test_escalation_keeps_values_and_step_counts(self):
    line, = self.child('''
plain = run(3000)
curry.reset(backend='cxx', interpret='off', stack_limit=65536)
M = curry.import_('StackGuard')
deep = run(3000)
print(json.dumps([plain, deep]))
''')
    plain, deep = json.loads(line)
    self.assertEqual(plain, deep)
    self.assertEqual(plain[0], [3000])


  def test_refused_reservation_halves_to_a_usable_stack(self):
    # A fresh child has no worker.  A 1 GiB reservation cannot fit this
    # process cap; a smaller reservation can.  The goal needs little heap.
    line, = self.child('''
import resource
resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
ev = Evaluator(cytest.raw.interp(), cytest.raw.expr(M.deep, 3000, typed=True))
values = [cytest.raw.interp().topython(v) for v in ev.evaluate()]
assert values == [3000], values
assert ev.rts._escalated
print(ev.rts._worker_attempts)
''', stack_limit=65536)
    sizes = [int(size) for size in line.split(', ')]
    self.assertGreater(len(sizes), 1, sizes)
    self.assertEqual(sizes[0], 1 << 30)
    for before, after in zip(sizes, sizes[1:]):
      self.assertEqual(after, max(before // 2, 64 << 20))
