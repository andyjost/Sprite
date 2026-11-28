'''The opt-in depth-first scheduler, beside the default Fair Scheme order.'''
import cytest # from ./lib; must be first
import curry, json, os, unittest
from curry.interpreter import flags

ADDRESS_SPACE = 2_000_000_000
TIMEOUT = 300

CHILD = '''
import curry, json
curry.reset(search=%r, rotation='steps:65536', jit='off')
M = curry.import_('Search')
'''


def child(test, mode, code, cap=ADDRESS_SPACE):
  proc = cytest.run_in_subprocess(CHILD % mode + code, TIMEOUT,
                                 address_space=cap)
  test.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
  return proc.stdout.strip()


class TestSearch(cytest.TestCase):
  def test_flag(self):
    self.assertEqual(flags.FLAG_INFO['search'][1], 'fair')
    with self.assertRaises(curry.FlagError):
      curry.reset(search='bogus')
    proc = cytest.run_in_subprocess('''
import os
os.environ.pop('SPRITE_INTERPRETER_FLAGS', None)
import curry
assert curry.flags['search'] == 'fair'
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'search:dfs'
curry.reset(backend='cxx')
assert curry.flags['search'] == 'dfs'
print('ok')
''', TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.strip(), 'ok')

  def test_tools(self):
    self.assertEqual(child(self, 'fair', """
import os, subprocess, sys, cytest
source = os.path.join('data', 'curry', 'Search.curry')
env = dict(os.environ, SPRITE_INTERPRETER_FLAGS='search:dfs')
commands = [
  (cytest.tool_command([curry.config.sprite_exec()]) + [source, '-g', 'order'], env),
  ([sys.executable, '-m', 'curry.tools.repl', ':set', 'search', 'dfs',
    ':load', source, ':eval', 'order', ':quit'], dict(os.environ,
    SPRITE_INTERPRETER_FLAGS='search:fair'))]
for command, environment in commands:
  proc = subprocess.run(command, env=environment, capture_output=True,
                        text=True, timeout=60)
  assert proc.returncode == 0, proc.stderr
  assert proc.stdout.splitlines() == ['0', '1', '2'], proc.stdout
print('ok')
"""), 'ok')

  def test_order(self):
    for mode, expected in [('fair', [2, 0, 1]), ('dfs', [0, 1, 2])]:
      self.assertEqual(json.loads(child(self, mode,
        "print(json.dumps(list(curry.eval(M.order))))")), expected)

  def test_same_values(self):
    results = []
    for mode in ['fair', 'dfs']:
      result = json.loads(child(self, mode, '''
answers = curry.solve(curry.parse('xs ++ ys =:= [1,2,3] where xs, ys free'))
bindings = sorted((str(a.value), str(a.bindings['xs']), str(a.bindings['ys']))
                  for a in answers)
print(json.dumps({
  'permutations': sorted(str(x) for x in curry.eval(M.permutations)),
  'bindings': bindings,
  'capsule': sorted(str(x) for x in curry.eval(M.capsule)),
  'small': sorted(str(x) for x in curry.eval(M.small))}))
'''))
      self.assertEqual(len(result['permutations']), 120)
      self.assertEqual(len(result['bindings']), 4)
      self.assertEqual(len(result['small']), 20)
      self.assertEqual(result['capsule'], ['[11, 21]', '[12, 22]'])
      results.append(result)
    self.assertEqual(*results)

  @cytest.posix_only('requires an address-space limit')
  @cytest.skipIfGcStress('279,936 leaves collect at every step')
  def test_memory(self):
    # Measured on a local system: DFS peaks at 225 MB RSS, fair at 586 MB.
    # 512 MB of address space is over twice the DFS RSS and below fair RSS.
    # Counting streams answers rather than retaining their Python values.
    self.assertEqual(child(self, 'dfs',
      'print(sum(1 for _ in curry.eval(M.main)))', cap=512_000_000), '21875')

  @cytest.posix_only('uses POSIX SIGINT delivery')
  def test_interruption(self):
    for rotation in ['steps:65536', 'time:10ms']:
      self.assertEqual(child(self, 'dfs', '''
import os, signal, threading
curry.reset(search='dfs', rotation=%r, jit='off')
M = curry.import_('Search')
# Import and construct before the signal is scheduled.
values = curry.eval(M.loop)
timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
timer.start()
try:
  next(values)
except KeyboardInterrupt:
  print('ok')
else:
  raise AssertionError('the evaluation ignored SIGINT')
finally:
  timer.join()
''' % rotation), 'ok')

  def test_suspended_front(self):
    self.assertEqual(child(self, 'dfs', '''
from curry.backends.cxx import curryrtbindings as native
import cytest
x = curry.term(curry.free('x', type='Int'))._node
rts = native.RuntimeState(cytest.raw.interp(), cytest.raw.expr(M.suspended, x))
try:
  assert str(next(rts.generate_values())) == '[99]'
  assert rts.queue_size == 1
  try:
    next(rts.generate_values())
  except curry.SuspensionError:
    print('ok')
  else:
    raise AssertionError('expected suspension')
finally:
  rts.close()
'''), 'ok')
