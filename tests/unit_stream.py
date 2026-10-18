'''The C++ output channel, its paused roots and its terminal meaning.'''
import cytest # from ./lib; must be first
import curry
import gc
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import weakref
from curry import config

ROOT = Path(__file__).resolve().parent.parent

@unittest.skipUnless(curry.flags['backend'] == 'cxx',
    'the Python backend is retired and has no stream yield point')
class TestStream(cytest.TestCase):
  def setUp(self):
    self.M = curry.import_('StreamChannel')

  def test_close_releases_parked_queue(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    totals = curry._interpreter_._evaluation_totals
    before = len(totals._running)
    s = curry.stream(self.M.three)
    self.assertEqual(len(totals._running), before)
    self.assertEqual(next(s), 1)
    rts, = [r for r in totals._running if r.queue_size]
    held = weakref.ref(rts)
    self.assertEqual(rts.queue_size, 1)
    configurations = cyrt.gc_configuration_count()
    del rts
    s.close()
    self.assertEqual(len(totals._running), before)
    self.assertIsNone(held())
    self.assertEqual(cyrt.gc_configuration_count(), configurations - 1)
    self.assertEqual(list(s), [])

  def test_parked_stream_survives_collection_and_other_stream(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    a, b = curry.stream(self.M.three), curry.stream(self.M.three)
    self.addCleanup(a.close)
    self.addCleanup(b.close)
    self.assertEqual((next(a), next(b), next(a)), (1, 1, 2))
    gc.collect()
    cyrt.gc_collect()
    self.assertEqual(list(b), [2, 3])
    self.assertEqual(list(a), [3])
    self.assertEqual((a.result, b.result), (42, 42))

  def test_stop_iteration_result(self):
    s = curry.stream(self.M.three)
    self.assertEqual([next(s), next(s), next(s)], [1, 2, 3])
    with self.assertRaises(StopIteration) as caught:
      next(s)
    self.assertEqual((caught.exception.value, s.result), (42, 42))

  def test_whole_values_preserve_types(self):
    empty, string, strings, box, pair = list(curry.stream(self.M.whole))
    self.assertEqual((empty, string, strings, pair), ([], '', ['', 'a'], (curry.Char('x'), True)))
    self.assertIsInstance(box, self.M.Box)
    self.assertEqual(box.args, ([1, 2],))

  def test_erased_parameter_uses_value_conversion(self):
    M = curry.compile('''
import Sprite.Stream
data Box a = Box a
instance Show (Box a) where
  show _ = "Box"
out :: IO ()
out = yield (Box "")
''', name='StreamErasedType')
    value, = curry.stream(M.out)
    # The unconstrained instance carries no element type for the empty list.
    self.assertEqual(value.args, ([],))
    self.assertEqual(curry.typeof(value), 'Box a')

  def test_free_variable_is_a_value(self):
    value, = curry.stream(self.M.freeOut)
    self.assertIsInstance(value, curry.Var)

  def test_pure_goal_refused(self):
    with self.assertRaisesRegex(curry.CurryTypeError, 'IO action'):
      curry.stream(curry.term(1))

  def test_no_side_effect_until_pull(self):
    with tempfile.TemporaryDirectory() as dirname:
      path = os.path.join(dirname, 'started')
      s = curry.stream(self.M.startFile(path))
      self.addCleanup(s.close)
      self.assertFalse(os.path.exists(path))
      self.assertEqual(next(s), 1)
      self.assertEqual(Path(path).read_text(), 'started')

  def test_choices_in_action_value_and_result(self):
    for action in (self.M.choiceAction, self.M.nestedChoice):
      s = curry.stream(action)
      with self.subTest(action=str(action)), self.assertRaises(curry.NondetError):
        next(s)
      self.assertEqual(list(s), [])
    s = curry.stream(self.M.choiceResult)
    self.assertEqual(next(s), 1)
    with self.assertRaises(curry.NondetError):
      next(s)
    self.assertEqual(list(s), [])

  def test_error_follows_yield_and_closes(self):
    s = curry.stream(self.M.priorError)
    self.assertEqual(next(s), 1)
    with self.assertRaisesRegex(curry.EvaluationError, 'stream boom'):
      next(s)
    self.assertEqual(list(s), [])
    self.assertIsNone(s.result)

  def test_retained_error_releases_run(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    configurations = cyrt.gc_configuration_count()
    queues = cyrt.gc_queue_count()
    s = curry.stream(self.M.priorError)
    self.assertEqual(next(s), 1)
    try:
      next(s)
    except curry.EvaluationError as caught:
      error = caught
    else:
      self.fail('the action did not raise its error')
    self.assertIsNotNone(error.__traceback__)
    self.assertEqual(cyrt.gc_configuration_count(), configurations)
    self.assertEqual(cyrt.gc_queue_count(), queues)
    self.assertEqual(list(s), [])

  def test_catch_resumes_after_yield(self):
    self.assertEqual(list(curry.stream(self.M.recovered)), [1, 2])

  def test_interpreted_action(self):
    proc = cytest.run_in_subprocess('''
import curry
curry.reset(interpret='all')
M = curry.import_('StreamChannel')
s = curry.stream(M.three)
assert list(s) == [1, 2, 3]
assert s.result == 42
''', timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)

  def test_step_limit_at_output(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    from curry.typecheck import goals
    interp = curry._interpreter_
    def state():
      goal = goals.make_goal(interp, (self.M.three,))
      return interp.backend.create_evaluation_rts(interp, goal.expr)
    first = state()
    first.next()
    self.assertTrue(first.stream_yielded)
    limited = state()
    limited.step_limit = first.steps_total
    with self.assertRaises(cyrt.StepLimitReached):
      limited.next()
    self.assertEqual(limited.steps_total, first.steps_total)

  def test_set_function_in_action(self):
    self.assertEqual(list(curry.stream(self.M.setInside)), [1, 2])

  def test_yield_inside_set_is_refused(self):
    with self.assertRaisesRegex(curry.EvaluationError, 'yield inside a set function'):
      next(curry.stream(self.M.insideSet))

  def run_tool(self, *args, input=None):
    proc = subprocess.run(args, input=input, capture_output=True, text=True, timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def test_sprite_exec_prints_yields_in_order(self):
    output = self.run_tool(config.sprite_exec(), str(ROOT / 'tests/data/curry/StreamChannel.curry'), '-g', 'three')
    self.assertEqual(output, '1\n2\n3\n42\n')

  def test_terminal_uses_custom_show(self):
    output = self.run_tool(config.sprite_exec(), str(ROOT / 'tests/data/curry/StreamChannel.curry'), '-g', 'custom')
    self.assertEqual(output, 'boxed:7\n')

  def test_terminal_show_obeys_io_choice_rule(self):
    proc = cytest.run_in_subprocess('''
import curry
M = curry.compile("""
import Sprite.Stream
data Shown = Shown
instance Show Shown where
  show _ = "a" ? "b"
out :: IO ()
out = yield Shown
""", name='StreamShowChoice')
assert len(list(curry.stream(M.out))) == 1
try:
  list(curry.eval(M.out))
except curry.NondetError:
  pass
else:
  raise AssertionError('terminal show accepted a choice')
''', timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, '')

  def test_repl_prints_yields(self):
    output = self.run_tool(str(Path(config.sprite_exec()).with_name('python')),
        '-m', 'curry.tools.icy', input=':load StreamChannel\n:eval custom\n:quit\n')
    self.assertIn('boxed:7\n', output)
    self.assertNotIn('()\n', output)

  def test_oracle_shim_matches_terminal(self):
    pakcs = Path(config.installed_path('tools/pakcs'))
    if not pakcs.exists():
      self.skipTest('PAKCS is unavailable; the shim was not run')
    env = dict(os.environ, CURRYPATH=str(ROOT / 'curry/oracle') + os.pathsep + os.environ.get('CURRYPATH', ''))
    proc = subprocess.run([str(pakcs), '--nocypm', '-q', ':load',
        str(ROOT / 'tests/data/curry/flows/Primes.curry'), ':eval', 'threeOut', ':quit'],
        env=env, capture_output=True, text=True, timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, '1\n2\n3\n')
    self.assertEqual(proc.stdout, self.run_tool(config.sprite_exec(),
        str(ROOT / 'tests/data/curry/flows/Primes.curry'), '-g', 'threeOut'))

if __name__ == '__main__':
  unittest.main()
