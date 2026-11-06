'''Pure tracing does not turn a function into an I/O step (#241).'''
import cytest # from ./lib; must be first
import unittest


class TestIssue241(cytest.TestCase):
  def check_goal(self, mode, goal):
    child = cytest.run_in_subprocess('''
import curry
curry.reset(interpret=%r, jit='off')
curry.path.insert(0, 'data/curry/issue241')
module = curry.import_('ContractChoice')
values = list(curry.eval(module[%r]))
assert len(values) == 1, values
if %r == 'value':
  assert curry.show(values[0]) == '[]', values
else:
  assert module.main.info.flags & curry.common.F_MONADIC
''' % (mode, goal, goal), timeout=90, address_space=1 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
    self.assertEqual(child.stdout, '[]\n' if goal == 'main' else '')
    self.assertEqual(child.stderr, '')

  def test_main_interpreted(self):
    self.check_goal('all', 'main')

  def test_main_compiled(self):
    self.check_goal('off', 'main')

  def test_value_interpreted(self):
    self.check_goal('all', 'value')

  def test_value_compiled(self):
    self.check_goal('off', 'value')

  def test_real_io_step_rejects_choice(self):
    for mode in ('all', 'off'):
      with self.subTest(interpret=mode):
        child = cytest.run_in_subprocess('''
import curry
curry.reset(interpret=%r, jit='off')
module = curry.compile("""
guarded :: Bool -> IO ()
guarded b = if b then putStrLn "yes" else return ()
main :: IO ()
main = guarded (True ? False)
""")
assert module.guarded.info.flags & curry.common.F_MONADIC
try:
  list(curry.eval(module.main))
except curry.NondetError as exc:
  assert str(exc) == 'non-determinism in monadic actions occurred!', str(exc)
else:
  raise AssertionError('a choice reached a real I/O step')
''' % mode, timeout=90, address_space=1 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertEqual(child.stdout, '')

  def test_unsafe_primitive_still_checks_its_action(self):
    for mode in ('all', 'off'):
      with self.subTest(interpret=mode):
        child = cytest.run_in_subprocess('''
import curry
curry.reset(interpret=%r, jit='off')
module = curry.compile("""
import System.IO.Unsafe (unsafePerformIO)
value :: Int
value = unsafePerformIO (if True ? False then return 1 else return 2)
""")
assert not module.value.info.flags & curry.common.F_MONADIC
try:
  list(curry.eval(module.value))
except curry.NondetError as exc:
  assert str(exc) == 'non-determinism in monadic actions occurred!', str(exc)
else:
  raise AssertionError('unsafePerformIO accepted a nondeterministic action')
''' % mode, timeout=90, address_space=1 << 30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

  def test_trace_library_flags(self):
    child = cytest.run_in_subprocess('''
import curry
curry.reset(interpret='all', jit='off')
debug = curry.import_('Debug.Trace')
unsafe = curry.import_('System.IO.Unsafe')
for name in ('trace', 'traceId', 'traceShow', 'traceShowId', 'assert'):
  assert not debug[name].info.flags & curry.common.F_MONADIC, name
for name in ('traceIO', 'assertIO'):
  assert debug[name].info.flags & curry.common.F_MONADIC, name
assert not unsafe.trace.info.flags & curry.common.F_MONADIC
assert not unsafe.unsafePerformIO.info.flags & curry.common.F_MONADIC
''', timeout=90, address_space=1 << 30)
    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


if __name__ == '__main__':
  unittest.main()
