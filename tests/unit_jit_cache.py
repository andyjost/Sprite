'''Persistent LLVM objects: fresh-process relocation, keys and publication.'''
import cytest # from ./lib; must be first
import curry
from curry.backends.cxx import elf, llvmjit
import contextlib, io, json, os, pathlib, subprocess, sys, tempfile, unittest
from unittest import mock

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
import curry, json, os, sys
from curry.backends.cxx import curryrtbindings as rt, llvmjit
from unittest import mock
mode, tier, source, abi = sys.argv[1:]
# Windows chmod cannot make a directory unwritable. Exercise the store's
# permission branch there with the same mode bits used by the POSIX tests.
readonly = os.environ.get('SPRITE_TEST_JIT_READONLY')
if readonly:
  stat = os.stat
  def readonly_stat(path, *args, **kwargs):
    result = stat(path, *args, **kwargs)
    if os.path.normcase(os.fspath(path)) == os.path.normcase(readonly):
      fields = list(result)
      fields[0] &= ~0o222
      return os.stat_result(fields)
    return result
  os.stat = readonly_stat
if abi:
  llvmjit._abi_digest = lambda: ['changed ABI']
curry.reset(interpret=mode, jit=tier, jit_backend='llvm')
if tier == 'off' or mode == 'off':
  llvmjit._read_cache = mock.Mock(side_effect=AssertionError('disabled cache read'))
M = curry.import_(source)
before = rt.icurry_is_jit(M.fib.info)
values = [str(x) for x in curry.eval(M.main)]
print(json.dumps(dict(before=before, jitted=rt.icurry_is_jit(M.fib.info),
    bad_jitted=rt.icurry_is_jit(M.bad.info), compiled=llvmjit.statistics()['functions'],
    linked=llvmjit.statistics()['linked'], values=values,
    steps=curry.stats()['steps'], swapped=curry.stats()['swapped'])))
'''


def traced_code(code, delay=100):
  # The parent's usual bound is 120 s. Arm before importing the runtime so
  # import, evaluation, publication and interpreter shutdown all leave stacks.
  return ('import faulthandler; faulthandler.dump_traceback_later(%r, repeat=True)\n'
          % delay) + code


class TestJITCache(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    if not llvmjit.available():
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

  def start(self, command, *, dump_after=100, **kwargs):
    command = list(command)
    if command[:2] == [sys.executable, '-c']:
      command[2] = traced_code(command[2], dump_after)
    elif command[:2] == [sys.executable, '-m']:
      module = command[2]
      code = 'import runpy, sys; sys.argv[0] = %r; runpy.run_module(%r, run_name="__main__")' % (module, module)
      command = [sys.executable, '-c', traced_code(code, dump_after)] + command[3:]
    else:
      raise ValueError('expected a Python -c or -m child')
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('stderr', subprocess.PIPE)
    kwargs.setdefault('text', True)
    process = subprocess.Popen(command, **kwargs)
    self.addCleanup(self.stop, process)
    return process

  @staticmethod
  def stop(process):
    if process.poll() is None:
      process.kill()
    return process.communicate(timeout=30)

  def output(self, process, timeout=120):
    try:
      out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
      out, err = self.stop(process)
      print('Timed out child %d stderr:\n%s' % (process.pid, err), file=sys.stderr, flush=True)
      exc.output, exc.stderr = out, err
      raise
    self.assertEqual(process.returncode, 0, out + err)
    return out, err

  def result(self, process, timeout=120):
    out, err = self.output(process, timeout)
    return json.loads(out.splitlines()[-1])

  def child(self, tier='hot', abi='', mode='new'):
    return self.result(self.start(self.command(tier, abi, mode),
        env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))

  def object(self):
    return next(self.base.rglob('Cached.jit'))

  def test_child_timeout_reaps_process(self):
    process = self.start([sys.executable, '-c', 'import time; time.sleep(60)'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, dump_after=.1)
    with contextlib.redirect_stderr(io.StringIO()) as log:
      with self.assertRaises(subprocess.TimeoutExpired) as caught:
        self.result(process, timeout=3)
    self.assertIn('Timeout (', log.getvalue())
    self.assertIn('<module>', caught.exception.stderr)
    self.assertIsNotNone(process.poll())

  def test_warm_start_values_steps_and_stats(self):
    interpreted = self.child('off')
    cold = self.child('eager')
    stamp = self.object().stat().st_mtime_ns
    for mode in ('all', 'new'):
      warm = self.child(mode=mode)
      self.assertFalse(warm['before'])
      self.assertTrue(warm['jitted'])
      self.assertFalse(warm['bad_jitted'])
      self.assertEqual(warm['compiled'], 0)
      self.assertEqual(warm['swapped'], warm['linked'])
      self.assertLess(warm['linked'], 50)
      self.assertEqual(warm['values'], interpreted['values'])
      self.assertEqual(warm['steps'], interpreted['steps'])
      self.assertGreater(warm['swapped'], 0)
    self.assertEqual(self.object().stat().st_mtime_ns, stamp)
    self.assertEqual(cold['values'], interpreted['values'])

  def test_resolver_registration_does_not_hold_jit_lock(self):
    self.child('eager')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
install = rt.icurry_install_cached
def checked(items):
  assert not llvmjit._lock.locked(), 'heap acquisition under the JIT lock'
  return install(items)
with mock.patch.object(rt, 'icurry_install_cached', side_effect=checked) as registration:
  M = curry.import_(source)
assert registration.called
assert not rt.icurry_is_jit(M.fib.info)
assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
print(json.dumps(dict(ok=True)))
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_shutdown_cancels_unlinked_hot_work(self):
    self.child('off')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
parse = llvmjit._jit.llvm.parse_assembly
def stopping(text):
  module = parse(text)
  llvmjit._hot_enabled = False
  return module
with llvmjit._lock:
  try:
    with mock.patch.object(llvmjit._jit.llvm, 'parse_assembly', side_effect=stopping), mock.patch.object(llvmjit._jit, 'link_object', side_effect=AssertionError('shutdown work linked')):
      llvmjit._jit.compile_batch([(M.fib.info, 'Cached.fib')], post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.fib.info,)})
  finally:
    llvmjit._hot_enabled = True
assert not rt.icurry_is_jit(M.fib.info)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_each_native_object_contains_only_its_step(self):
    if sys.platform == 'darwin':
      self.skipTest('the native objects of macOS are Mach-O; the reader reads ELF')
    self.child('eager')
    path = self.object()
    with path.open('rb') as stream:
      _, size = llvmjit._CACHE_PREFIX.unpack(stream.read(llvmjit._CACHE_PREFIX.size))
      index = json.loads(stream.read(size))
    objects = llvmjit._read_cache(path, index['key'])
    symbols = [records[0][1] for records, _ in objects]
    for records, obj in objects:
      data = obj.read()
      if not data.startswith(b'\x7fELF'):
        objects.close()
        self.skipTest('the symbol reader reads ELF, not COFF; fresh-process linking is tested separately')
      native = elf.read_symbols(data)
      own = records[0][1]
      self.assertIn(own, native)
      for other in symbols:
        if other != own:
          self.assertNotIn(other, native)

  def test_eager_links_at_load(self):
    self.child('eager')
    warm = self.child('eager')
    self.assertTrue(warm['before'])
    self.assertTrue(warm['bad_jitted'])
    self.assertEqual(warm['compiled'], 0)

  def test_payload_checked_only_on_resolution(self):
    self.child('eager')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
import os
with mock.patch.object(llvmjit._Object, 'read', side_effect=AssertionError('early payload read')):
  M = curry.import_(source)
assert not rt.icurry_is_jit(M.fib.info)
context = llvmjit._jit.modules[M.fib.info.address]
records, obj = context.object_for('Cached.fib')
# Change only this object's bytes, retaining size and the header's mtime.
stat = os.stat(obj.path)
with open(obj.path, 'r+b') as stream:
  stream.seek(obj.offset + obj.entry['size'] - 1)
  value = stream.read(1)
  stream.seek(-1, 1)
  stream.write(bytes([value[0] ^ 1]))
os.utime(obj.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
with mock.patch.object(obj, 'read', wraps=obj.read) as read:
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
assert not rt.icurry_is_jit(M.fib.info)
assert 'Cached.fib' in context.failed
assert read.call_count == 1
print(json.dumps(dict(ok=True)))
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_link_failure_does_not_poison_other_functions(self):
    self.child('eager')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
link = llvmjit._jit.link_object
attempted = set()
def failing(obj, records, addresses, name):
  assert name not in attempted, 'a failed ORC library name was reused'
  attempted.add(name)
  if records[0][0] == 'Cached.fib':
    raise RuntimeError('missing cached symbol')
  return link(obj, records, addresses, name)
with mock.patch.object(llvmjit._jit, 'link_object', side_effect=failing):
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
  assert len(list(curry.eval(M.message))) == 1
assert not rt.icurry_is_jit(M.fib.info)
assert rt.icurry_is_jit(M.message.info)
print(json.dumps(dict(ok=True)))
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_hot_queue_uses_cached_object(self):
    self.child('eager')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
bad_obj = context.object_for('Cached.bad')[1]
read = llvmjit._Object.read
def checked(obj):
  assert obj.entry is not bad_obj.entry, 'unused object read'
  return read(obj)
with mock.patch.object(llvmjit._Object, 'read', checked), mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  with llvmjit._lock:
    llvmjit._jit.compile_batch([(M.fib.info, 'Cached.fib'), (M.message.info, 'Cached.message')], post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.fib.info, M.message.info,)})
  before = llvmjit.statistics()['linked']
  assert llvmjit._resolve_cached(M.fib.info.address)
  assert llvmjit.statistics()['linked'] == before
  rt.icurry_apply_posted()
assert rt.icurry_is_jit(M.fib.info)
assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
print(json.dumps(dict(ok=True)))
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def run_code(self, body):
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + body
    return self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_unexpected_resolver_exception_warns_once(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
original = context.resolve
def unexpected(name, **kwargs):
  if name == 'Cached.fib':
    raise AttributeError('unexpected hook failure')
  return original(name, **kwargs)
with mock.patch.object(context, 'resolve', side_effect=unexpected) as resolve, mock.patch.object(llvmjit.logger, 'warning') as warning:
  for _ in range(2):
    assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
  assert llvmjit._resolve_cached(M.fib.info.address) == 0
assert [call.args[0] for call in resolve.call_args_list].count('Cached.fib') == 1
assert warning.call_count == 1
assert 'Cached.fib' in context.failed
assert not rt.icurry_is_jit(M.fib.info)
print(json.dumps(dict(ok=True)))
""")

  def test_binding_rejects_invalid_hook_result_and_exception(self):
    self.child('eager')
    for result in ('None', "(_ for _ in ()).throw(AttributeError('bad hook'))"):
      self.run_code("""
M = curry.import_(source)
hook = mock.Mock(side_effect=lambda address: RESULT)
def resolve(address):
  return hook(address) if address == M.fib.info.address else llvmjit._resolve_cached(address)
rt.icurry_set_cache_hook(resolve)
for _ in range(2):
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
assert hook.call_count == 1
assert not rt.icurry_is_jit(M.fib.info)
print(json.dumps(dict(ok=True)))
""".replace('RESULT', result))

  def test_failed_resolution_recompiled_by_hot_batch(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
obj = context.object_for('Cached.fib')[1]
with mock.patch.object(obj, 'read', side_effect=ValueError('corrupt JIT object')):
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
  assert not rt.icurry_is_jit(M.fib.info)
  with llvmjit._lock:
    llvmjit._jit.compile_batch([(M.fib.info, 'Cached.fib')], post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.fib.info,)})
rt.icurry_apply_posted()
assert rt.icurry_is_jit(M.fib.info)
assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
objects = llvmjit._read_cache(context.local, context.key)
names = [records[0][0] for records, obj in objects]
assert names.count('Cached.fib') == 1
print(json.dumps(dict(ok=True)))
""")
    self.assertTrue(self.child()['jitted'])

  def test_replacement_after_attachment_preserves_resolution_and_publication(self):
    self.check_replacement_after_attachment()

  def test_blocked_replacement_after_attachment_uses_private_publication(self):
    self.check_replacement_after_attachment(blocked=True)

  def check_replacement_after_attachment(self, blocked=False):
    self.child('off')
    self.run_code("""
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
print(json.dumps(dict(ok=True)))
""")
    publisher = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
llvmjit.compile(M.message.info, 'Cached.message')
context = llvmjit._jit.modules[M.message.info.address]
objects = llvmjit._read_cache(context.local, context.key)
names = {records[0][0] for records, obj in objects}
objects.close()
assert names in ({'Cached.fib'}, {'Cached.fib', 'Cached.message'}), names
if 'Cached.message' not in names:
  # Replacing an open destination can fail on Windows despite delete sharing.
  # The writer must then have published to its private-cache fallback.
  objects = llvmjit._read_cache(context.private, context.key)
  private_names = {records[0][0] for records, obj in objects}
  objects.close()
  assert private_names == {'Cached.fib', 'Cached.message'}, private_names
print(json.dumps(dict(names=sorted(names))))
"""
    if blocked:
      publisher = publisher.replace("llvmjit.compile(M.message.info, 'Cached.message')", """
context = llvmjit._jit.modules[M.message.info.address]
replace = llvmjit.os.replace
def replace_unpinned(src, dst):
  if dst == context.local:
    raise PermissionError('open destination')
  return replace(src, dst)
with mock.patch.object(llvmjit.os, 'replace', replace_unpinned):
  llvmjit.compile(M.message.info, 'Cached.message')
""")
    published = self.run_code("""
import subprocess
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
old = context.index
publisher = subprocess.run([sys.executable, '-c', PUBLISHER, 'all', 'hot', source, ''],
    check=True, timeout=60, stdout=subprocess.PIPE, text=True)
expected = {'Cached.fib', 'Cached.message', 'Cached.main'}
# A fresh loader must see the fallback even while the older local file exists.
probe = subprocess.run([sys.executable, '-c', PROBE, 'all', 'hot', source, ''],
    check=True, timeout=30, stdout=subprocess.PIPE, text=True)
assert old.stream.fileno() >= 0
assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
assert rt.icurry_is_jit(M.fib.info)
assert 'Cached.fib' not in context.failed
llvmjit.compile(M.main.info, 'Cached.main')
objects = llvmjit._read_cache(context.local, context.key)
names = {records[0][0] for records, obj in objects}
objects.close()
if os.path.exists(context.private):
  # A refused replacement leaves the complete publication in the union.
  objects = llvmjit._read_cache(context.private, context.key)
  names.update(records[0][0] for records, obj in objects)
  objects.close()
assert names == expected, (names, expected)
print(json.dumps(dict(names=sorted(names))))
""".replace('PUBLISHER', repr(traced_code(publisher, 50))).replace('PROBE', repr(traced_code(
        CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
with mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  assert [str(x) for x in curry.eval(M.message)] == ['cached literal']
assert rt.icurry_is_jit(M.message.info)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
""", 20))))
    # A third process must see the publication made while the first reader
    # held the old generation, plus the first reader's newly added function.
    warm = self.child()
    self.assertTrue(warm['jitted'])
    self.assertEqual(warm['compiled'], 0)
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
names = set(context.cached)
assert names == set(EXPECTED), names
with mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  assert '144' in str(list(curry.eval(M.main))[0])
assert rt.icurry_is_jit(M.main.info)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
""".replace('EXPECTED', repr(published['names'])))

  def seed_private_duplicate(self):
    self.child('off')
    self.run_code("""
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
context = llvmjit._jit.modules[M.fib.info.address]
replace = llvmjit.os.replace
def blocked_local(src, dst):
  if dst == context.local:
    raise PermissionError('open destination')
  return replace(src, dst)
with mock.patch.object(llvmjit.os, 'replace', side_effect=blocked_local):
  llvmjit.compile(M.message.info, 'Cached.message')
assert os.path.exists(context.private)
print(json.dumps(dict(ok=True)))
""")

  def test_load_retries_local_when_merge_removes_private_between_reads(self):
    self.check_load_during_merge()

  def test_load_unions_private_when_merge_is_refused_between_reads(self):
    self.check_load_during_merge(blocked=True)

  def check_load_during_merge(self, blocked=False):
    self.seed_private_duplicate()
    self.run_code("""
M = curry.import_(source)
jit = llvmjit._jit
writer = jit.modules[M.fib.info.address]
jit.object_generations.pop(writer.runtime_key)
reader = llvmjit._CachedModule(jit, writer.path, writer.header,
    [(info, name) for name, info in writer.items.items()])
read = llvmjit._read_cache
replace = llvmjit.os.replace
def publish(src, dst):
  if BLOCKED and dst == reader.local:
    raise PermissionError('open destination')
  return replace(src, dst)
reads = []
def interleaved(path, *args, **kwargs):
  reads.append(path)
  if path == reader.private:
    assert reads == [reader.local, reader.private]
    # Publish after the reader pins old local, before it opens private.
    with mock.patch.object(llvmjit, '_read_cache', read), \
        mock.patch.object(llvmjit.os, 'replace', side_effect=publish):
      writer.store()
    # Linux replaces the pinned local file and removes private, forcing the
    # local re-read. Windows normally refuses replacement and keeps private;
    # the forced-refusal variant exercises that union branch on Linux too.
    if BLOCKED:
      assert os.path.exists(reader.private)
    elif os.name != 'nt':
      assert not os.path.exists(reader.private)
  found = read(path, *args, **kwargs)
  if reads == [reader.local]:
    assert {records[0][0] for records, _ in found} == {'Cached.fib'}
  return found
with mock.patch.object(llvmjit, '_read_cache', side_effect=interleaved):
  assert reader.load(jit)
if os.path.exists(reader.private):
  assert reads == [reader.local, reader.private], reads
  local = read(reader.local, reader.key)
  private = read(reader.private, reader.key)
  try:
    assert {records[0][0] for records, _ in local} == {'Cached.fib'}
    assert {records[0][0] for records, _ in private} == {'Cached.fib', 'Cached.message'}
  finally:
    local.close()
    private.close()
else:
  assert reads == [reader.local, reader.private, reader.local], reads
  local = read(reader.local, reader.key)
  try:
    assert {records[0][0] for records, _ in local} == {'Cached.fib', 'Cached.message'}
  finally:
    local.close()
assert set(reader.cached) == {'Cached.fib', 'Cached.message'}
with mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  for name in reader.cached:
    assert reader.resolve(name)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
""".replace('BLOCKED', repr(blocked)))

  def test_corrupt_local_duplicate_resolves_from_private_without_compiling(self):
    self.seed_private_duplicate()
    path = self.object()
    stamp = path.stat().st_mtime_ns
    with path.open('r+b') as stream:
      _, size = llvmjit._CACHE_PREFIX.unpack(stream.read(llvmjit._CACHE_PREFIX.size))
      entries = json.loads(stream.read(size))['objects']
      self.assertEqual(entries[0]['functions'][0][0], 'Cached.fib')
      offset = stream.tell()
      byte = stream.read(1)
      stream.seek(offset)
      stream.write(bytes([byte[0] ^ 255]))
    os.utime(path, ns=(stamp, stamp))
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
obj = context.object_for('Cached.fib')[1]
fallback = obj.entry['_fallback']
assert not obj.entry.get('_native')
assert not fallback.entry.get('_native')
with mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
assert obj.entry.get('_dropped')
assert fallback.entry.get('_native')
assert rt.icurry_is_jit(M.fib.info)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
""")

  def test_touched_envelope_merges_verified_functions(self):
    self.child('eager')
    path = self.object()
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 4000000000))
    self.run_code("""
import os
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
assert not context.cached
llvmjit.compile(M.fib.info, 'Cached.fib')
objects = llvmjit._read_cache(context.local, context.key)
assert {records[0][0] for records, obj in objects} >= {'Cached.fib', 'Cached.message', 'Cached.bad', 'Cached.main'}
assert os.stat(context.local).st_mtime_ns % 2000000000 == 0
assert all(llvmjit._object_bytes(obj) for records, obj in objects)
print(json.dumps(dict(ok=True)))
""")
    self.assertEqual(self.child('eager')['compiled'], 0)

  def test_failed_publication_preserves_attached_generation(self):
    self.child('eager')
    self.run_code("""
import pathlib
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
path = pathlib.Path(context.local)
before = path.read_bytes()
for name in context.cached:
  assert context.resolve(name)
assert all(entry.get('_native') for entry in context.index.entries)
context.root = None
with mock.patch.object(llvmjit.os, 'replace', side_effect=PermissionError('sharing violation')):
  context.store()
assert path.read_bytes() == before
assert context.index is None
assert all(isinstance(obj, bytes) and obj for _, obj in context.objects)
assert context.objects is llvmjit._jit.object_generations[context.runtime_key]
assert all(isinstance(obj, bytes) for _, obj in context.cached.values())
assert not list(path.parent.glob('.jit-*'))
objects = llvmjit._read_cache(path, context.key)
assert all(obj.read() for records, obj in objects)
assert objects.stream.closed
print(json.dumps(dict(ok=True)))
""")
    self.assertEqual(self.child('eager')['compiled'], 0)

  def test_positioned_read_without_pread(self):
    from concurrent.futures import ThreadPoolExecutor
    stream = tempfile.TemporaryFile()
    stream.write(bytes(range(256)) * 4)
    stream.flush()
    index = llvmjit._IndexedObjects('unused', [{}], stream)
    self.addCleanup(index.close)
    with mock.patch.object(llvmjit.os, 'pread', None, create=True):
      with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda offset: index.read_at(offset, 32), range(256)))
    self.assertEqual(results, [(bytes(range(256)) * 4)[i:i + 32] for i in range(256)])
    index.close()
    with self.assertRaises(ValueError):
      index.read_at(0, 1)

  def test_small_payload_overwritten_after_attachment_is_corrupt(self):
    import hashlib, zlib
    path = self.base / 'small.jit'
    payload = zlib.compress(b'original object')
    entry = dict(functions=[['F.f', 's0', []]], size=len(payload),
        digest=hashlib.sha256(payload).hexdigest())
    stamp = 2000000000
    header = dict(key='small', objects=[entry], size=0, mtime_ns=stamp)
    while True:
      encoded = json.dumps(header).encode('ascii')
      size = llvmjit._CACHE_PREFIX.size + len(encoded) + len(payload)
      if header['size'] == size:
        break
      header['size'] = size
    data = llvmjit._CACHE_PREFIX.pack(llvmjit._CACHE_MAGIC, len(encoded)) + encoded + payload
    # Keep the entire envelope inside a buffered reader's initial prefetch.
    self.assertLess(len(data), 4096)
    for pread in (getattr(os, 'pread', None), None):
      with self.subTest(pread=pread is not None):
        path.write_bytes(data)
        os.utime(path, ns=(stamp, stamp))
        objects = llvmjit._read_cache(path, 'small')
        self.addCleanup(objects.close)
        obj = next(iter(objects))[1]
        with path.open('r+b', buffering=0) as writer:
          writer.seek(obj.offset)
          writer.write(bytes([payload[0] ^ 1]))
        os.utime(path, ns=(stamp, stamp))
        with mock.patch.object(llvmjit.os, 'pread', pread, create=True):
          with self.assertRaisesRegex(ValueError, 'corrupt JIT object'):
            obj.read()
        self.assertTrue(objects.stream.closed)

  def test_generation_open_errors_and_process_liveness(self):
    with self.assertRaises(OSError):
      llvmjit._open_cache(self.base / 'missing.jit')
    self.assertTrue(llvmjit._process_alive(os.getpid()))
    self.assertTrue(llvmjit._process_alive(0))
    process = self.start([sys.executable, '-c', 'pass'], dump_after=20)
    self.output(process, timeout=30)
    self.assertFalse(llvmjit._process_alive(process.pid))

  def test_resolver_runs_between_hot_sub_batches(self):
    self.child('eager')
    self.run_code("""
import threading, time
M = curry.import_(source)
jit = llvmjit._jit
started, resolved = threading.Event(), threading.Event()
sizes = []
def slow(items, **kwargs):
  sizes.append(len(items))
  if len(sizes) == 1:
    started.set()
    time.sleep(.1)
  else:
    assert resolved.wait(2), 'resolver blocked by the whole hot group'
def worker():
  llvmjit._compile_groups(jit, [(M.bad.info, 'Cached.bad')] * 64, post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.bad.info, M.fib.info)})
with mock.patch.object(jit, 'compile_batch', side_effect=slow):
  thread = threading.Thread(target=worker)
  thread.start()
  assert started.wait(2)
  start = time.perf_counter()
  assert llvmjit._resolve_cached(M.fib.info.address)
  elapsed = time.perf_counter() - start
  resolved.set()
  thread.join(5)
  assert not thread.is_alive()
assert sizes == [32, 32], sizes
assert elapsed < 1, elapsed
print(json.dumps(dict(ok=True, wait_ms=elapsed * 1000)))
""")

  def test_sub_batches_publish_once_per_module(self):
    context = mock.Mock(objects=[])
    jit = mock.Mock(modules={1: context})
    def compiled(items, **kwargs):
      self.assertTrue(llvmjit._lock.locked())
      self.assertLessEqual(len(items), 32)
      self.assertFalse(kwargs['store'])
      context.objects.append(items)
      context.dirty = True
      return context
    jit.compile_batch.side_effect = compiled
    with mock.patch.object(llvmjit.curryrt, 'icurry_address', return_value=1):
      llvmjit._compile_groups(jit, [(1, 'M.f')] * 64)
    self.assertEqual(jit.compile_batch.call_count, 2)
    context.store.assert_called_once_with(messages=[])

  def test_shutdown_publishes_completed_sub_batch(self):
    self.child('off')
    self.run_code("""
import threading, time
M = curry.import_(source)
jit = llvmjit._jit
context = jit.modules[M.fib.info.address]
compile_batch = jit.compile_batch
second, stopped = threading.Event(), threading.Event()
calls = []
def fake(items, **kwargs):
  calls.append(len(items))
  if len(calls) == 1:
    return compile_batch([(M.fib.info, 'Cached.fib')], **kwargs)
  second.set()
  deadline = time.monotonic() + 5
  while llvmjit._hot_enabled:
    assert time.monotonic() < deadline
    time.sleep(.001)
  assert not stopped.is_set(), 'shutdown returned before publication'
def stop():
  assert second.wait(5)
  llvmjit._stop_hot_tier()
  stopped.set()
thread = threading.Thread(target=stop)
thread.start()
with mock.patch.object(jit, 'compile_batch', side_effect=fake):
  llvmjit._compile_groups(jit, [(M.bad.info, 'Cached.bad')] * 64, post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.bad.info, M.fib.info)})
thread.join(5)
assert stopped.is_set()
assert calls == [32, 32]
objects = llvmjit._read_cache(context.local, context.key)
assert [records[0][0] for records, obj in objects] == ['Cached.fib']
assert all(obj.read() for records, obj in objects)
print(json.dumps(dict(ok=True)))
""")
    self.assertTrue(self.child()['jitted'])

  def test_sub_batches_publish_actual_contexts_after_reattach(self):
    old, new = mock.Mock(dirty=False), mock.Mock(dirty=False)
    jit = mock.Mock(modules={1: old})
    def compiled(items, **kwargs):
      context = jit.modules[1]
      context.dirty = True
      if context is old:
        # An interleaved compile can store and shrink the object list.
        old.objects = []
        jit.modules[1] = new
      return context
    jit.compile_batch.side_effect = compiled
    with mock.patch.object(llvmjit.curryrt, 'icurry_address', return_value=1):
      llvmjit._compile_groups(jit, [(1, 'M.f')] * 64)
    old.store.assert_called_once_with(messages=[])
    new.store.assert_called_once_with(messages=[])

  def test_failure_before_read_preserves_object(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
entry = context.cached['Cached.fib']
with mock.patch.object(rt, 'icurry_bytecode', return_value=None):
  assert context.resolve('Cached.fib') == 0
assert not entry.get('_released')
assert not entry.get('_dropped')
context.failed.clear()
bc = rt.icurry_bytecode(M.fib.info)
with mock.patch.object(rt, 'icurry_bytecode', return_value=dict(bc, consts={})):
  assert context.resolve('Cached.fib') == 0
assert not entry.get('_released')
assert not entry.get('_dropped')
assert context.object_for('Cached.fib')[1].read()
print(json.dumps(dict(ok=True)))
""")

  def test_dropped_entry_after_store_recompiles(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
context.release('Cached.fib')
# Prevent publication from recovering the explicitly dropped object on disk.
with open(context.local, 'r+b') as stream:
  stream.write(b'invalid!')
context.store()
assert 'Cached.fib' not in context.cached
with llvmjit._lock:
  llvmjit._jit.compile_batch([(M.fib.info, 'Cached.fib')], post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.fib.info,)})
rt.icurry_apply_posted()
assert rt.icurry_is_jit(M.fib.info)
print(json.dumps(dict(ok=True)))
""")

  def test_ir_dump_identifies_qualified_functions(self):
    dump = self.base / 'dump'
    self.env['SPRITE_JIT_DUMP'] = str(dump)
    self.child('eager')
    text = '\n'.join(path.read_text() for path in dump.glob('*.ll'))
    self.assertRegex(text, r'; Cached\.fib\ndefine [^\n]*@"?s[0-9a-f]+"?\(')

  def test_resolver_skips_step_already_compiled_by_worker(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
context = llvmjit._jit.modules[M.fib.info.address]
with mock.patch.object(context, 'resolve', side_effect=AssertionError('resolved twice')):
  assert llvmjit._resolve_cached(M.fib.info.address) == 0
print(json.dumps(dict(ok=True)))
""")

  def test_index_closes_after_last_resolution_and_can_publish(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
index = context.index
assert not index.stream.closed
for name in context.cached:
  assert context.resolve(name)
assert index.stream.closed
assert all(entry.get('_native') for entry in index.entries)
context.store()
assert context.index is not index
assert context.objects is context.index
assert context.objects is llvmjit._jit.object_generations[context.runtime_key]
assert all('_native' not in entry for entry in context.index.entries)
assert all(context.object_for(name)[1].index is context.index for name in context.cached)
assert all('_native' not in obj.entry for _, obj in context.cached.values())
objects = llvmjit._read_cache(context.local, context.key)
assert len(objects) == len(context.cached)
assert all(llvmjit._object_bytes(obj) for _, obj in objects)
assert objects.stream.closed
print(json.dumps(dict(ok=True)))
""")

  def test_closed_index_preserves_verified_objects_after_image_replacement(self):
    self.child('off')
    self.run_code("""
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
print(json.dumps(dict(ok=True)))
""")
    publisher = CHILD[:CHILD.index('M = curry.import_(source)')] + """
from pathlib import Path
path = Path(source)
path.write_text(path.read_text().replace('cached literal', 'changed literal'))
M = curry.import_(source)
llvmjit.compile(M.message.info, 'Cached.message')
print(json.dumps(dict(ok=True)))
"""
    self.run_code("""
import subprocess
from curry.backends.cxx import image
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
for name in context.cached:
  assert context.resolve(name)
assert context.index.stream.closed
subprocess.run([sys.executable, '-c', PUBLISHER, 'all', 'hot', source, ''],
    check=True, timeout=60, stdout=subprocess.PIPE, text=True)
assert image.read(context.path) != context.header
local = open(context.local, 'rb').read()
llvmjit.compile(M.main.info, 'Cached.main')
assert open(context.local, 'rb').read() == local
objects = llvmjit._read_cache(context.private, context.key)
assert {records[0][0] for records, _ in objects} == {'Cached.fib', 'Cached.main'}
assert all(llvmjit._object_bytes(obj) for _, obj in objects)
assert objects.stream.closed
print(json.dumps(dict(ok=True)))
""".replace('PUBLISHER', repr(traced_code(publisher, 50))))
    self.source.write_text(PROGRAM)
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
with mock.patch.object(llvmjit._Batch, 'emit', side_effect=AssertionError('cache hit compiled')):
  assert [str(x) for x in curry.eval(M.fib(12))] == ['144']
  assert '144' in str(list(curry.eval(M.main))[0])
assert rt.icurry_is_jit(M.fib.info)
assert rt.icurry_is_jit(M.main.info)
assert llvmjit.statistics()['functions'] == 0
print(json.dumps(dict(ok=True)))
""")

  def test_detach_closes_unresolved_index(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
jit = llvmjit._jit
context = jit.modules[M.fib.info.address]
index = context.index
view = context.object_for('Cached.bad')[1]
assert view.index is index
assert not view.index.stream.closed
header = dict(context.header, body='changed')
with mock.patch.object(llvmjit._CachedModule, 'load', return_value=False):
  llvmjit.attach_cache(context.path, header,
      [(info, name) for name, info in context.items.items()])
assert index.stream.closed
assert context.resolve('Cached.bad') == 0
assert 'Cached.bad' in context.failed
with llvmjit._lock:
  jit.compile_batch([(M.bad.info, 'Cached.bad')], post=True,
      work={rt.icurry_address(info): rt.icurry_work(curry._interpreter_._its, info)
            for info in (M.bad.info,)})
rt.icurry_apply_posted()
assert rt.icurry_is_jit(M.bad.info)
print(json.dumps(dict(ok=True)))
""")

  def test_failed_objects_release_descriptor(self):
    self.child('eager')
    self.run_code("""
M = curry.import_(source)
context = llvmjit._jit.modules[M.fib.info.address]
index = context.index
with mock.patch.object(llvmjit._IndexedObjects, 'read_at', return_value=b'bad payload'):
  for name in context.cached:
    assert context.resolve(name) == 0
  context.store()
assert index.stream.closed
assert not context.objects
print(json.dumps(dict(ok=True)))
""")

  def test_invalid_compressed_payload_releases_descriptor(self):
    import hashlib
    payload = b'not a zlib stream'
    stream = tempfile.TemporaryFile()
    self.addCleanup(stream.close)
    stream.write(payload)
    stream.flush()
    entry = dict(functions=[['F.f', 's0', []]], _offset=0,
        size=len(payload), digest=hashlib.sha256(payload).hexdigest())
    index = llvmjit._IndexedObjects('unused', [entry], stream)
    with self.assertRaisesRegex(ValueError, 'compressed'):
      index.view(entry)[1].read()
    self.assertTrue(stream.closed)

  def test_short_symbols_are_unique(self):
    self.child('eager')
    with self.object().open('rb') as stream:
      _, size = llvmjit._CACHE_PREFIX.unpack(stream.read(llvmjit._CACHE_PREFIX.size))
      index = json.loads(stream.read(size))
    symbols = [entry['functions'][0][1] for entry in index['objects']]
    self.assertEqual(len(set(symbols)), len(symbols))
    self.assertTrue(all(len(symbol) <= 4 for symbol in symbols))

  def test_old_format_is_a_miss(self):
    self.child('eager')
    with self.object().open('r+b') as stream:
      stream.write(b'SPRTJIT3')
    self.assertFalse(self.child()['jitted'])

  def test_stage_switch_skips_fill(self):
    import importlib.util
    root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location('jit_build_package',
        root / 'scripts/build-package.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with mock.patch.dict(os.environ, SPRITE_STAGE_JIT_CACHE='0'):
      code = module.jit_cache_fill(['Missing'])
    process = self.start([sys.executable, '-c', code], dump_after=20)
    out, err = self.output(process, timeout=30)
    self.assertEqual(out.count('fill skipped'), 1)
    self.assertNotIn('import curry', code)

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
    if os.name == 'nt':
      self.env['SPRITE_TEST_JIT_READONLY'] = str(products)
    self.child('eager')
    self.assertFalse((products / 'Cached.jit').exists())
    self.assertTrue(list((self.base / 'private' / 'Cached').glob('*.jit')))
    self.assertTrue(self.child()['jitted'])

  def test_no_writable_location_keeps_compilation_in_memory(self):
    self.child('off')
    products = next(self.base.rglob('Cached.img')).parent
    products.chmod(0o555)
    self.addCleanup(products.chmod, 0o755)
    if os.name == 'nt':
      self.env['SPRITE_TEST_JIT_READONLY'] = str(products)
    self.env['SPRITE_JIT_CACHE'] = ''
    self.assertTrue(self.child('eager')['jitted'])
    self.assertFalse(list(self.base.rglob('Cached.jit')))

  def test_two_processes_share_one_object(self):
    self.child('off')  # Prepare front-end products before concurrent writers.
    processes = [self.start(self.command('eager'), env=self.env,
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
    # sprite-exec delegates to this module; enter it through Python so the
    # watchdog is armed before its imports on both platforms.
    proc = self.start([sys.executable, '-m', 'curry',
        '--stats', str(self.source)], env=env)
    out, err = self.output(proc)
    stats = dict(field.split('=', 1) for field in err.splitlines()[-1].split())
    self.assertGreater(int(stats['swapped']), 0)

  def test_later_batches_keep_earlier_functions(self):
    self.child('off')
    code = CHILD[:CHILD.index('M = curry.import_(source)')] + """
M = curry.import_(source)
llvmjit.compile(M.fib.info, 'Cached.fib')
llvmjit.compile(M.message.info, 'Cached.message')
print(json.dumps(dict(values=[str(x) for x in curry.eval(M.main)])))
list(curry.eval(M.message))
assert rt.icurry_is_jit(M.message.info)
"""
    proc = self.start([sys.executable, '-c', code, 'new', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    self.result(proc)
    self.assertTrue(self.child()['jitted'])
    # A partially cached module gains another function in a later process.
    orphan = self.object().parent / '.jit-99999999-abandoned'
    orphan.write_bytes(b'incomplete')
    live = self.object().parent / ('.jit-%d-live' % os.getpid())
    live.write_bytes(b'in progress')
    code = code.replace("llvmjit.compile(M.fib.info, 'Cached.fib')",
        "list(curry.eval(M.fib(12))); assert rt.icurry_is_jit(M.fib.info)").replace(
        "llvmjit.compile(M.message.info, 'Cached.message')",
        "llvmjit.compile(M.main.info, 'Cached.main')")
    self.result(self.start([sys.executable, '-c', code, 'new', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    self.assertTrue(self.child()['jitted'])
    with self.object().open('rb') as stream:
      _, size = llvmjit._CACHE_PREFIX.unpack(stream.read(llvmjit._CACHE_PREFIX.size))
      index = json.loads(stream.read(size))
    self.assertEqual([len(o['functions']) for o in index['objects']], [1, 1, 1])
    self.assertFalse(orphan.exists())
    self.assertTrue(live.exists())

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
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))
    self.assertTrue(self.child(mode='all')['jitted'])

  def test_private_budget_preserves_default_slot(self):
    self.child('eager')
    path = self.object()
    before = (path.stat().st_mtime_ns, path.read_bytes())
    code = CHILD.replace("jit_backend='llvm')", "jit_backend='llvm', inline_budget=0)")
    self.result(self.start([sys.executable, '-c', code, 'all', 'eager',
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
  assert not rt.icurry_is_jit(M.fib.info)
  assert [str(x) for x in curry.eval(M.main)] == values
assert len(llvmjit._jit.generations) == linked
"""
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
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
    if os.name == 'nt':
      self.env['SPRITE_TEST_JIT_READONLY'] = str(products)
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
    self.result(self.start([sys.executable, '-c', prime, 'all', 'hot',
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
    self.result(self.start([sys.executable, '-c', code, 'all', 'hot',
        str(self.source), ''], env=self.env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True))

  def test_corrupt_object_is_a_miss(self):
    self.child('eager')
    self.object().write_bytes(b'truncated')
    self.assertFalse(self.child()['jitted'])
    self.child('eager')
    self.assertTrue(self.child()['jitted'])
