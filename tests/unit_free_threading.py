'''Python-side concurrency and publication protocols.

On an ordinary build the GIL still serializes Python bytecode: these tests
exercise ownership, publication, and lock order there, but do not prove the
absence of Python data races. CI also runs them on 3.14t without the GIL.
Two Curry evaluations still serialize their steps at the runtime heap;
parallel Curry execution (epic #28) is outside this contract.
'''
import cytest # from ./lib; must be first
import curry, os, sys, sysconfig, unittest

CHILD = '''
import cytest, curry, concurrent.futures, contextlib, importlib, json, os
import pathlib, subprocess, sys, tempfile, threading, time, zlib
from unittest import mock
from curry import config
from curry.objects.handle import getHandle
from curry.toolchain import _productcache, _productlock, _system, plans
from curry.backends.cxx import toolchain, materialize

def together(*functions):
  barrier = threading.Barrier(len(functions))
  def run(function):
    barrier.wait(timeout=20)
    return function()
  with concurrent.futures.ThreadPoolExecutor(max_workers=len(functions)) as pool:
    jobs = [pool.submit(run, function) for function in functions]
    return [job.result(timeout=60) for job in jobs]

def json_module(directory, name, value=42):
  productdir = os.path.join(directory, '.curry', config.intermediate_subdir())
  os.makedirs(productdir, exist_ok=True)
  path = os.path.join(productdir, name + '.json.z')
  with open(path, 'wb') as stream:
    stream.write(zlib.compress(cytest.json_module(name, value).encode()))
  return path
'''

class TestFreeThreading(cytest.TestCase):
  def child(self, code, timeout=120):
    proc = cytest.run_in_subprocess(CHILD + code, timeout, address_space=4 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.splitlines(), ['ok'])

  def test_extension_keeps_the_requested_gil_mode(self):
    if sysconfig.get_config_var('Py_GIL_DISABLED'):
      self.assertEqual(sys._is_gil_enabled(), os.environ.get('PYTHON_GIL') == '1')

  def test_import_build_evaluate_and_consume(self):
    self.child('''
curry.reset(interpret='new')
with tempfile.TemporaryDirectory() as directory:
  filename = os.path.join(directory, 'ThreadSurface.curry')
  with open(filename, 'w') as stream:
    stream.write('module ThreadSurface where\\ninc :: Int -> Int\\ninc x = x + 1\\n')
  # Prepare only the frontend products; both threads materialize the module.
  plan = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON)
  curry.toolchain.makecurry(plan, filename, [directory], is_sourcefile=True)
  def work():
    module = curry.import_(pathlib.Path(filename))
    for n in range(8):
      assert curry.eval(module.inc(n)).one() == n + 1
      assert list(curry.eval(curry.term([n, n+1]))) == [[n, n+1]]
      assert curry.eval(curry.parse('%d + 2' % n)).one() == n + 2
      assert curry.info(module).symbols['inc'].signature == 'Int -> Int'
    assert 'inc' in getattr(module, '.symbols')
    assert curry.modules['ThreadSurface'] is module
    return module
  from curry.interpreter.import_ import load
  from curry import icurry
  building, observed = threading.Event(), threading.Event()
  load_symbols = load.loadSymbols
  def paused(interp, obj, module, **kwds):
    if isinstance(obj, icurry.IModule) and obj.fullname == 'ThreadSurface':
      building.set()
      assert observed.wait(20)
    return load_symbols(interp, obj, module, **kwds)
  def observe():
    assert building.wait(20)
    try:
      assert 'ThreadSurface' not in cytest.raw.interp().modules
      assert 'ThreadSurface' not in curry.modules
    finally:
      observed.set()
  with mock.patch.object(load, 'loadSymbols', paused):
    first, second, _ = together(work, work, observe)
  assert first is second
  assert set(curry.modules) == {'Prelude', 'ThreadSurface'}, list(curry.modules)
print('ok')
''')

  def test_reset_makes_another_threads_term_and_results_stale(self):
    self.child('''
curry.reset(interpret='new')
held = threading.Event()
reset = threading.Event()
def retain():
  term = curry.term([1, 2])
  results = curry.eval(term)
  started = curry.eval(curry.choice(1, 2))
  assert next(started) in (1, 2)
  held.set()
  assert reset.wait(20)
  for operation in (lambda: curry.eval(term).one(), lambda: next(results), lambda: next(started)):
    try:
      operation()
    except curry.StaleError:
      pass
    else:
      raise AssertionError('an old-session object was accepted')
def retire():
  assert held.wait(20)
  curry.reset(interpret='new')
  reset.set()
together(retain, retire)
assert curry.eval(curry.term(3)).one() == 3
print('ok')
''')

  def test_two_threads_compile_and_import_the_same_module(self):
    self.child('''
curry.reset(interpret='off')
with tempfile.TemporaryDirectory() as directory:
  json_module(directory, 'ThreadCompile')
  interp = cytest.raw.interp()
  # Every native metadata entry must be outside a file-production lock.
  from curry.backends.cxx.curryrtbindings import _curryrtbindings as native
  original = native._metadata_call
  def metadata(action):
    assert not getattr(_productlock._local, 'held', {}), 'product -> heap'
    return original(action)
  def work():
    module = interp.import_('ThreadCompile', currypath=[directory])
    assert list(interp.eval(cytest.raw.expr(getHandle(module).symbols['goal']))) == [42]
    assert curry.modules['ThreadCompile'] is module
    return module
  with mock.patch.object(native, '_metadata_call', metadata):
    first, second = together(work, work)
  assert first is second
print('ok')
''')

  @cytest.linux_only('compiles and swaps a module through the shim of the tiered mode; macOS is issue #162, step 2')
  def test_first_use_compiles_while_a_producer_prepares_native_imports(self):
    self.child('''
curry.reset(interpret='off')
with tempfile.TemporaryDirectory() as directory:
  filename = os.path.join(directory, 'ThreadTrap.curry')
  with open(filename, 'w') as stream:
    stream.write('module ThreadTrap where\\ngoal :: Int\\ngoal = 42\\n')
  frontend = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON)
  jsonfile = curry.toolchain.makecurry(frontend, filename, [directory], is_sourcefile=True)
  imodule = curry.toolchain.loadjson(jsonfile)
  interp = cytest.raw.interp()
  module = interp.import_(imodule, currypath=[directory])
  info = getHandle(module).symbols['goal'].info
  from curry.backends.cxx import curryrtbindings as native
  assert native.is_trapped(info), 'the first-use compile became eager'
  cppfile = materialize.product_file(imodule)
  interp.save(module, cppfile, module_main=False)
  ready, trapped, attempted = threading.Event(), threading.Event(), threading.Event()
  original_dependency = toolchain.Cpp2So._sofilename
  original_compile = materialize.compile_pending
  def dependency(step, name, currypath=None):
    if threading.current_thread().name == 'product-producer':
      ready.set()
      assert trapped.wait(20)
      attempted.set()
    return original_dependency(step, name, currypath)
  def compile_pending(entry):
    trapped.set()
    assert attempted.wait(20)
    return original_compile(entry)
  def producer():
    threading.current_thread().name = 'product-producer'
    return toolchain.Cpp2So(interp)(cppfile, [directory])
  def evaluate():
    assert ready.wait(20)
    assert curry.eval(module.goal).one() == 42
  with mock.patch.object(toolchain.Cpp2So, '_sofilename', dependency), \
       mock.patch.object(materialize, 'compile_pending', compile_pending):
    together(producer, evaluate)
  assert not native.is_trapped(info)
print('ok')
''')

  def test_forced_compile_preserves_a_product_under_a_reader(self):
    self.child('''
curry.reset(interpret='off')
with tempfile.TemporaryDirectory() as directory:
  jsonfile = json_module(directory, 'ThreadRecompile')
  interp = cytest.raw.interp()
  plan = plans.makeplan(interp, plans.MAKE_ALL | plans.ZIP_JSON)
  sofile = curry.toolchain.makecurry(plan, 'ThreadRecompile', [directory])
  cppfile = sofile[:-3] + '.cpp'
  before = toolchain.Cpp2So.product_snapshot(sofile)
  compiling, read = threading.Event(), threading.Event()
  real_pexec = _system.pexec
  def pexec(cmd, *args, **kwds):
    if '-shared' in cmd and cppfile not in cmd and any('.compile-' in x for x in cmd):
      compiling.set()
      assert read.wait(20)
    return real_pexec(cmd, *args, **kwds)
  def writer():
    return toolchain.Cpp2So(interp)(cppfile, [directory])
  def reader():
    assert compiling.wait(20)
    assert toolchain.Cpp2So.product_snapshot(sofile) == before
    module = curry.load(sofile)
    values = list(interp.eval(cytest.raw.expr(getHandle(module).symbols['goal'])))
    assert values == [42], values
    read.set()
  with mock.patch.object(_system, 'pexec', pexec):
    together(writer, reader)
  assert before != toolchain.Cpp2So.product_snapshot(sofile)
  assert toolchain.Cpp2So(interp).stamp_is_current(sofile)
print('ok')
''')

  def test_product_lock_has_thread_ownership(self):
    self.child('''
with tempfile.TemporaryDirectory() as directory:
  filename = os.path.join(directory, 'Owned.cpp')
  entered, attempted, release, second = [threading.Event() for _ in range(4)]
  def first():
    with _productlock.locked(filename):
      with _productlock.locked(filename): # recursion belongs to this owner
        entered.set()
        assert attempted.wait(20)
        assert not second.wait(.1)
        release.set()
  def other():
    assert entered.wait(20)
    attempted.set()
    with _productlock.locked(filename) as waited:
      assert release.is_set() and waited
      second.set()
  together(first, other)
  assert second.is_set()
print('ok')
''')

  def test_python_import_hook_cannot_publish_an_old_session_after_reset(self):
    self.child('''
curry.reset(interpret='new')
with tempfile.TemporaryDirectory() as directory:
  json_module(directory, 'ThreadHook')
  curry.path.insert(0, directory)
  from curry.interpreter.import_ import load
  from curry import icurry
  building, release = threading.Event(), threading.Event()
  real_load = load.loadSymbols
  def paused(interp, obj, module, **kwds):
    if isinstance(obj, icurry.IModule) and obj.fullname == 'ThreadHook':
      building.set()
      assert release.wait(20)
    return real_load(interp, obj, module, **kwds)
  def importer():
    return importlib.import_module('curry.lib.ThreadHook')
  def resetter():
    assert building.wait(20)
    release.set()
    curry.reset(interpret='new')
  with mock.patch.object(load, 'loadSymbols', paused):
    old, _ = together(importer, resetter)
  assert 'curry.lib.ThreadHook' not in sys.modules
  try:
    curry.info(old)
  except curry.StaleError:
    pass
  else:
    raise AssertionError('hook retained an old-session module')
  current = importer()
  assert current is curry.modules['ThreadHook'] and current is not old
  assert len([hook for hook in sys.meta_path
      if getattr(hook, 'LIBPATH', None) == 'curry.lib.']) == 1
print('ok')
''')

  def test_cache_two_processes_and_two_threads(self):
    self.child('''
with tempfile.TemporaryDirectory() as directory:
  root = os.path.join(directory, 'cache')
  code = """
import curry, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
from curry.toolchain import _productcache
root, base = sys.argv[1:]
os.makedirs(base)
barrier = threading.Barrier(2)
def writer(number):
  source = os.path.join(base, str(number))
  os.mkdir(source)
  paths = []
  for suffix in ('.cpp', '.so', '.so.abi'):
    path = os.path.join(source, 'M' + suffix)
    with open(path, 'wb') as stream:
      stream.write((base + str(number)).encode() * 1000)
    paths.append(path)
  barrier.wait()
  for i in range(8):
    _productcache.store('digest', 'key', paths, cache_root=root)
    target = os.path.join(source, 'read')
    os.makedirs(target, exist_ok=True)
    placed = _productcache.restore('digest', 'key', target,
        ['M.cpp', 'M.so', 'M.so.abi'], cache_root=root)
    contents = [open(path, 'rb').read() for path in placed.values()]
    assert len(set(contents)) == 1
with ThreadPoolExecutor(2) as pool:
  list(pool.map(writer, range(2)))
"""
  children = [subprocess.Popen([sys.executable, '-c', code, root,
      os.path.join(directory, str(n))], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      for n in range(2)]
  for child in children:
    out, err = child.communicate(timeout=60)
    assert child.returncode == 0, err.decode()
  entry = _productcache.lookup('digest', 'key', ['M.cpp', 'M.so', 'M.so.abi'], root)
  assert len({open(path, 'rb').read() for path in entry.values()}) == 1
  assert not any(name.endswith(('.tmp', '.old'))
      for parent, dirs, files in os.walk(root) for name in dirs + files)
print('ok')
''')

  def test_metadata_caches_publish_one_complete_object(self):
    self.child('''
from curry.utility.proptree import proptree
from curry.toolchain.flat2icurry import flatcurry as fc, interfaces
with tempfile.TemporaryDirectory() as directory:
  filename = os.path.join(directory, 'ThreadInterface.fint')
  with open(filename, 'w') as stream:
    stream.write(fc.show(fc.Prog('ThreadInterface', [], [], [], [])))
  def work():
    tree = proptree({'thread_field': {'value': 42}})
    interface = interfaces.load_interface(filename)
    assert tree.thread_field.value == 42 and interface.name == 'ThreadInterface'
    return type(tree), type(tree.thread_field), interface
  first, second = together(work, work)
  assert all(a is b for a, b in zip(first, second))
print('ok')
''')

  def test_child_environment_leaves_python_gil_to_the_user(self):
    from curry.backends.cxx import tiered
    from unittest import mock
    for value in (None, '0', '1'):
      env = os.environ.copy()
      env.pop('PYTHON_GIL', None)
      if value is not None:
        env['PYTHON_GIL'] = value
      with mock.patch.dict(os.environ, env, clear=True):
        child = dict(item.split('=', 1) for item in tiered._environment(cytest.raw.interp()))
        self.assertEqual(child.get('PYTHON_GIL'), value)
