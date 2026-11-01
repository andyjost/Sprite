'''Persistent LLVM objects: fresh-process relocation, keys and publication.'''
import cytest # from ./lib; must be first
import curry
from curry.backends.cxx import llvmjit
import json, os, pathlib, subprocess, sys, tempfile, unittest

PROGRAM = '''module Cached where
fib :: Int -> Int
fib n = if n < 2 then n else fib (n-1) + fib (n-2)
message :: String
message = "cached literal"
main :: (Int, String)
main = (fib 12, message)
bad :: Int
bad = 1 + error "cached error"
'''

CHILD = '''
import curry, json, sys
from curry.backends.cxx import curryrtbindings as rt, llvmjit
from unittest import mock
mode, tier, source, abi = sys.argv[1:]
if abi:
  llvmjit._abi_digest = lambda: ['changed ABI']
curry.reset(interpret=mode, jit=tier, jit_backend='llvm')
if tier == 'off' or mode == 'off':
  llvmjit._read_cache = mock.Mock(side_effect=AssertionError('disabled cache read'))
M = curry.import_(source)
before = rt.icurry_is_jit(M.fib.info)
values = [str(x) for x in curry.eval(M.main)]
print(json.dumps(dict(jitted=before, values=values,
    steps=curry.stats()['steps'], swapped=curry.stats()['swapped'])))
'''


class TestJITCache(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    if os.name == 'nt' or not llvmjit.available():
      raise unittest.SkipTest('persistent LLVM objects need a supported JIT')

  def setUp(self):
    self.work = tempfile.TemporaryDirectory(prefix='sprite-jit-cache-')
    self.addCleanup(self.work.cleanup)
    self.base = pathlib.Path(self.work.name)
    self.source = self.base / 'Cached.curry'
    self.source.write_text(PROGRAM)
    self.env = dict(os.environ, SPRITE_JIT_THRESHOLD='1000000000',
        SPRITE_ROTATION='steps:65536', SPRITE_JIT_CACHE=str(self.base / 'private'))
    self.env.pop('SPRITE_INTERPRETER_FLAGS', None)

  def command(self, tier='hot', abi='', mode='new'):
    return [sys.executable, '-c', CHILD, mode, tier, str(self.source), abi]

  def result(self, process):
    out, err = process.communicate(timeout=120)
    self.assertEqual(process.returncode, 0, out + err)
    return json.loads(out.splitlines()[-1])

  def child(self, tier='hot', abi='', mode='new'):
    return self.result(subprocess.Popen(self.command(tier, abi, mode),
        env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))

  def object(self):
    return next(self.base.rglob('Cached.jit'))

  def test_warm_start_values_steps_and_stats(self):
    interpreted = self.child('off')
    cold = self.child('eager')
    stamp = self.object().stat().st_mtime_ns
    for mode in ('all', 'new'):
      warm = self.child(mode=mode)
      self.assertTrue(warm['jitted'])
      self.assertEqual(warm['values'], interpreted['values'])
      self.assertEqual(warm['steps'], interpreted['steps'])
      self.assertGreater(warm['swapped'], 0)
    self.assertEqual(self.object().stat().st_mtime_ns, stamp)
    self.assertEqual(cold['values'], interpreted['values'])

  def test_image_change_misses(self):
    self.child('eager')
    self.source.write_text(PROGRAM.replace('fib 12', 'fib 13'))
    missed = self.child()
    self.assertFalse(missed['jitted'])
    self.assertIn('233', missed['values'][0])
    self.child('eager')
    self.assertTrue(self.child()['jitted'])

  def test_abi_change_misses(self):
    self.child('eager')
    self.assertFalse(self.child(abi='changed')['jitted'])
    self.child('eager', abi='changed')
    self.assertTrue(self.child(abi='changed')['jitted'])
    self.assertFalse(self.child()['jitted'])

  def test_read_only_products_use_private_cache(self):
    self.child('off')
    products = next(self.base.rglob('Cached.img')).parent
    products.chmod(0o555)
    self.addCleanup(products.chmod, 0o755)
    self.child('eager')
    self.assertFalse((products / 'Cached.jit').exists())
    self.assertTrue(list((self.base / 'private' / 'Cached').glob('*.jit')))
    self.assertTrue(self.child()['jitted'])

  def test_no_writable_location_keeps_compilation_in_memory(self):
    self.child('off')
    products = next(self.base.rglob('Cached.img')).parent
    products.chmod(0o555)
    self.addCleanup(products.chmod, 0o755)
    self.env['SPRITE_JIT_CACHE'] = ''
    self.assertTrue(self.child('eager')['jitted'])
    self.assertFalse(list(self.base.rglob('Cached.jit')))

  def test_two_processes_share_one_object(self):
    self.child('off')  # Prepare front-end products before concurrent writers.
    processes = [subprocess.Popen(self.command('eager'), env=self.env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    results = [self.result(p) for p in processes]
    self.assertEqual(results[0]['values'], results[1]['values'])
    self.assertEqual(len(list(self.base.rglob('Cached.jit'))), 1)
    self.assertTrue(self.child()['jitted'])

  def test_off_reads_nothing(self):
    self.child('eager')
    self.assertFalse(self.child('off')['jitted'])
    self.assertFalse(self.child(mode='off')['jitted'])

  def test_cli_stats_counts_linked_functions(self):
    self.child('eager')
    env = dict(self.env, SPRITE_INTERPRETER_FLAGS='interpret:all,jit:hot,jit_backend:llvm')
    proc = subprocess.run([curry.config.installed_path('bin', 'sprite-exec'),
        '--stats', str(self.source)], env=env, capture_output=True, text=True, timeout=120)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    stats = dict(field.split('=', 1) for field in proc.stderr.splitlines()[-1].split())
    self.assertGreater(int(stats['swapped']), 0)

  def test_later_batches_keep_earlier_functions(self):
    self.child('off')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
llvmjit.compile(M.message.info, 'Cached.message')
print(json.dumps(dict(values=[str(x) for x in curry.eval(M.main)])))
"""
    proc = subprocess.Popen([sys.executable, '-c', code, 'new', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    self.result(proc)
    self.assertTrue(self.child()['jitted'])
    # A partially cached module gains another function in a later process.
    orphan = self.object().parent / '.jit-99999999-abandoned'
    orphan.write_bytes(b'incomplete')
    code = code.replace("llvmjit.compile(M.fib.info, 'Cached.fib')",
        "assert rt.icurry_is_jit(M.fib.info)").replace(
        "llvmjit.compile(M.message.info, 'Cached.message')",
        "llvmjit.compile(M.main.info, 'Cached.main')")
    self.result(subprocess.Popen([sys.executable, '-c', code, 'new', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    self.assertTrue(self.child()['jitted'])
    with self.object().open('rb') as stream:
      _, size = llvmjit._CACHE_PREFIX.unpack(stream.read(llvmjit._CACHE_PREFIX.size))
      index = json.loads(stream.read(size))
    self.assertEqual([len(o['functions']) for o in index['objects']], [1, 1, 1])
    self.assertFalse(orphan.exists())

  def test_hot_batch_links_in_next_process(self):
    self.env['SPRITE_JIT_THRESHOLD'] = '1'
    # Keep evaluating until the real background hot loop has published fib.
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
import time
M = curry.import_(source)
deadline = time.monotonic() + 30
while not rt.icurry_is_jit(M.fib.info):
  list(curry.eval(M.main))
  assert time.monotonic() < deadline, llvmjit.statistics()
  time.sleep(.01)
with llvmjit._lock:
  pass
print(json.dumps(dict(ok=True)))
"""
    self.result(subprocess.Popen([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    self.assertTrue(self.child(mode='all')['jitted'])

  def test_private_budget_preserves_default_slot(self):
    self.child('eager')
    path = self.object()
    before = (path.stat().st_mtime_ns, path.read_bytes())
    code = CHILD.replace("jit_backend='llvm')", "jit_backend='llvm', inline_budget=0)")
    self.result(subprocess.Popen([sys.executable, '-c', code, 'all', 'eager',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    self.assertEqual((path.stat().st_mtime_ns, path.read_bytes()), before)

  def test_reattach_reuses_linked_generation(self):
    self.child('eager')
    code = CHILD + """
linked = len(llvmjit._jit.generations)
with mock.patch.object(llvmjit._jit, 'link_object',
    side_effect=AssertionError('linked twice')):
  curry.reset(interpret='all', jit='hot', jit_backend='llvm')
  M = curry.import_(source)
  assert rt.icurry_is_jit(M.fib.info)
  assert [str(x) for x in curry.eval(M.main)] == values
assert len(llvmjit._jit.generations) == linked
"""
    self.result(subprocess.Popen([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_hierarchical_private_layout(self):
    self.source = self.base / 'Hier' / 'Cached.curry'
    self.source.parent.mkdir()
    self.source.write_text(PROGRAM.replace('module Cached', 'module Hier.Cached'))
    self.child('off')
    products = next(self.base.rglob('Cached.img')).parent
    products.chmod(0o555)
    self.addCleanup(products.chmod, 0o755)
    fallback = self.base / 'private' / 'Hier.Cached'
    fallback.mkdir(parents=True)
    (fallback / 'obsolete.jit').write_bytes(b'old generation')
    self.child('eager')
    self.assertEqual(len(list(fallback.glob('*.jit'))), 1)
    self.assertTrue(self.child()['jitted'])

  def test_cached_step_preserves_exceptions(self):
    prime = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
llvmjit.compile(M.bad.info, 'Cached.bad')
print(json.dumps(dict(ok=True)))
"""
    self.result(subprocess.Popen([sys.executable, '-c', prime, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    code = CHILD + """
# A second object must not invalidate the first object's unwind tables.
llvmjit.compile(M.fib.info, 'Cached.fib')
try:
  list(curry.eval(M.bad))
except curry.EvaluationError as exc:
  assert 'cached error' in str(exc)
else:
  raise AssertionError('cached step lost its exception')
"""
    self.result(subprocess.Popen([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_corrupt_object_is_a_miss(self):
    self.child('eager')
    self.object().write_bytes(b'truncated')
    self.assertFalse(self.child()['jitted'])
    self.child('eager')
    self.assertTrue(self.child()['jitted'])
