import cytest # from ./lib; must be first
from curry.backends.cxx import cyrtbindings as cyrt
from curry.objects.handle import getHandle
from curry.utility.binding import binding
from curry import common, config, inspect
import ctypes, curry, json, os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'curry')

class TestCxxRuntime(cytest.TestCase):
  def testModuleCreation(self):
    count_modules = lambda: len(cyrt.Module.getall())
    # Earlier tests in the same process may leave the Prelude loaded, so count
    # relative to the state at entry.
    base = count_modules()
    self.assertNotIn('Hello', cyrt.Module.getall())

    # Create.
    Hello = cyrt.Module.find_or_create('Hello')
    self.assertEqual(count_modules(), base + 1)
    self.assertIs(cyrt.Module.getall()['Hello'], Hello)

    # Attributes.
    self.assertEqual(Hello.name, 'Hello')

    # Recreate.
    Hello2 = cyrt.Module.find_or_create('Hello')
    self.assertIs(Hello, Hello2)

    # Delete
    del Hello, Hello2
    self.assertEqual(count_modules(), base)

  def testTypeCreation(self):
    Hello = cyrt.Module.find_or_create('Hello')

    Cons = Hello.create_infotable(':', 2, common.T_CTOR  , common.F_LIST_TYPE)
    Nil = Hello.create_infotable('[]', 0, common.T_CTOR+1, common.F_LIST_TYPE)
    List = Hello.create_type('[]', [Cons, Nil], 0)

    self.assertEqual(Cons.arity, 2)
    self.assertEqual(Cons.flags, common.F_LIST_TYPE)
    self.assertEqual(Cons.format, 'pp')
    self.assertEqual(Cons.name, ':')
    self.assertEqual(Cons.tag, common.T_CTOR)
    # self.assertIs(Cons.step, None)
    # self.assertIs(Cons.typecheck, None)
    self.assertIs(Cons.typedef, List)

    self.assertIs(List.constructors[0], Cons)
    self.assertIs(List.constructors[1], Nil)

@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestCxxProcess(cytest.TestCase):
  '''
  Tests that run the C++ backend in a subprocess: a program that runs out of
  memory, and the order of a program's output.  The programs are in
  data/curry/CxxRuntime.curry.
  '''
  TIMEOUT = 120

  @classmethod
  def setUpClass(cls):
    # Compile the module once here.  The children then load it from the cache.
    curry.import_('CxxRuntime')

  @cytest.skipIfGcStress('the program keeps every node reachable')
  @cytest.skipUnlessGcBackend(
      'wdgc', 'near the address-space cap MPS collects instead of failing; '
              'the child does not end in time'
    )
  def test_out_of_memory_raises_MemoryError(self):
    '''
    An audit finding: when malloc failed, node allocation returned a null
    pointer, and the process crashed or aborted.  std::bad_alloc now leaves
    the step functions and the scheduler, and pybind11 turns it into
    MemoryError.  The child runs under a 1 GiB address-space cap.  The
    backend needs about 100 MB at load.  The program keeps every cell of
    its list reachable, so the collector frees nothing (see unit_cxx_gc.py
    for a program that completes under the cap).
    '''
    code = '''
import curry, os
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('CxxRuntime')
try:
  next(curry.eval(M.unbounded))
except MemoryError:
  os._exit(42)
os._exit(1)
'''
    proc = cytest.run_in_subprocess(code, self.TIMEOUT, address_space=1 << 30)
    self.assertEqual(
        proc.returncode, 42
      , 'the child ended with status %s; stderr:\n%s'
            % (proc.returncode, proc.stderr)
      )

  def test_program_output_precedes_value(self):
    '''
    An audit finding: the program wrote to the C standard output buffer, and
    Python printed the value from its own, so sprite-exec showed ``()``
    before the text of putStrLn when the output was a pipe.  The C buffer is
    now flushed when control returns to Python.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx'
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec(), '-m', 'CxxRuntime']
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, 'Hello from Curry\n()\n')

class TestBackendOption(cytest.TestCase):
  '''
  The ``-b,--backend`` option of sprite-exec.  It overrides a ``backend`` flag
  from SPRITE_INTERPRETER_FLAGS, in both directions.
  '''
  TIMEOUT = 120

  def backend_seen(self, option, flag):
    '''
    Starts the interactive prompt of sprite-exec with ``-b option`` while the
    environment names ``flag``, and returns what the prompt prints for the
    backend flag.
    '''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:' + flag
    cmd = ['timeout', str(self.TIMEOUT), config.sprite_exec(), '-b', option]
    proc = subprocess.run(
        cmd, env=env, input="print('backend', __package__.flags['backend'])\n"
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def test_backend_option_overrides_flag(self):
    self.assertIn('backend cxx', self.backend_seen('cxx', 'py'))
    self.assertIn('backend py', self.backend_seen('py', 'cxx'))


# Issue #124
# ==========

# The child of the reload tests: the nullary goals of ReloadBinding under
# each mode of the flag ``interpret`` in turn, with a reload between the
# modes, and the compiled modules of the Curry library mapped after each
# reload (from /proc/self/maps; None where there is none), as JSON.  The
# module is a local of a function: a module held across the reload keeps
# the object of the earlier interpreter, and the Prelude's with it, mapped,
# and the sequence of the issue is not run.
RELOAD_CHILD = '''
import curry, gc, json, os
from curry import inspect
from curry.common import T_FUNC
def goals(M):
  return sorted(
      name for name, sym in inspect.symbols(M).items()
          if sym.info.tag == T_FUNC and sym.info.arity == 0
    )
def run():
  M = curry.import_('ReloadBinding')
  return {
      name: sorted(str(v) for v in curry.eval(getattr(M, name)))
          for name in goals(M)
    }
def mapped():
  try:
    with open('/proc/self/maps') as stream:
      lines = stream.read().splitlines()
  except OSError:
    return None
  return sorted(set(
      os.path.basename(line.split()[-1]) for line in lines
          if '/.curry/' in line and line.endswith('.so')
    ))
out = {'values': [], 'mapped': []}
for mode in %(modes)r:
  curry.reload({'backend': 'cxx', 'interpret': mode})
  gc.collect()
  out['mapped'].append(mapped())
  out['values'].append(run())
print(json.dumps(out))
'''

# The values of the goals of ReloadBinding.
RELOAD_VALUES = {
    'bound': ['0', '1', '2', '7']
  , 'bound3': ['0', '1', '3', '9']
  }


class TestReloadBindingValues(cytest.TestCase):
  '''The goals of ReloadBinding on the current backend.'''
  def test_values(self):
    M = curry.import_('ReloadBinding')
    values = {
        name: sorted(str(v) for v in curry.eval(getattr(M, name)))
            for name in RELOAD_VALUES
      }
    self.assertEqual(values, RELOAD_VALUES)


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestReloadAfterCompiledObject(cytest.TestCase):
  '''
  Issue #124.  A process that evaluated the goals of a module loaded from
  its compiled object, then reloaded the interpreter into interpret:all and
  evaluated the same goals, died with a segmentation fault in procS at the
  goal that applies the binding of a free variable at a fork
  (RuntimeState::apply_binding).  The runtime builds that node with its own
  table of &> (CyI7Prelude12BindingGuard of cyrt/currylib/prelude.hpp,
  seq_Info then), which the runtime library exported under the mangled
  name of the Curry function Prelude.seq.  The compiled Prelude defines that symbol too, so its
  dynamic initializer wrote the table of seq over the table of the runtime
  when the object was loaded, and the unload of the object at the reload
  left the step of the table pointing into unmapped memory.  The table
  carries a name of its own now.  The tests run the sequence in a child,
  from interpret:off and from tiered, with the object of the module
  compiled first; the trigger is the compiled Prelude, not the object of
  the module.
  '''
  TIMEOUT = 300
  ADDRESS_SPACE = 2 << 30

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-reload-')
    shutil.copy(os.path.join(DATA, 'ReloadBinding.curry'), self.tmpdir)

  def tearDown(self):
    shutil.rmtree(self.tmpdir, ignore_errors=True)
    super().tearDown()

  def compile_module(self):
    '''Compiles the copy of the module to its object with sprite-make.'''
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:off'
    env['CURRYPATH'] = self.tmpdir
    cmd = [
        'prlimit', '--as=%d' % self.ADDRESS_SPACE, 'timeout', str(self.TIMEOUT)
      , config.installed_path('bin', 'sprite-make'), '--so', '-z', 'ReloadBinding'
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    sofile = os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), 'ReloadBinding.so'
      )
    self.assertTrue(os.path.isfile(sofile), sofile)

  def child(self, modes):
    with binding(os.environ, 'CURRYPATH', self.tmpdir):
      proc = cytest.run_in_subprocess(
          RELOAD_CHILD % {'modes': modes}, self.TIMEOUT
        , address_space=self.ADDRESS_SPACE
        )
    self.assertEqual(
        proc.returncode, 0
      , 'the child (%s) ended with status %s; stdout:\n%s\nstderr:\n%s'
            % (' then '.join(modes), proc.returncode, proc.stdout, proc.stderr)
      )
    return json.loads(proc.stdout.strip().splitlines()[-1])

  def check(self, modes):
    self.compile_module()
    out = self.child(modes)
    # The second pass starts after the unload of every object of the first:
    # the sequence of the issue.
    if out['mapped'][1] is not None:
      self.assertEqual(out['mapped'][1], [])
    self.assertEqual(out['values'], [RELOAD_VALUES, RELOAD_VALUES])

  def test_reload_from_compiled_into_interpreter(self):
    self.check(('off', 'all'))

  def test_reload_from_tiered_into_interpreter(self):
    self.check(('tiered', 'all'))


class _DlInfo(ctypes.Structure):
  _fields_ = [
      ('dli_fname', ctypes.c_char_p), ('dli_fbase', ctypes.c_void_p)
    , ('dli_sname', ctypes.c_char_p), ('dli_saddr', ctypes.c_void_p)
    ]

def _symbol_of(address):
  '''
  The file of the loaded object that holds ``address`` and the name of the
  dynamic symbol at that address there, or None for each that is not
  known (dladdr).
  '''
  for lib in (None, 'libdl.so.2'):
    try:
      dladdr = ctypes.CDLL(lib).dladdr
    except (OSError, AttributeError):
      continue
    dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DlInfo)]
    dladdr.restype = ctypes.c_int
    info = _DlInfo()
    if not dladdr(ctypes.c_void_p(address), ctypes.byref(info)):
      return None, None
    where = None if not info.dli_fname else os.path.realpath(info.dli_fname.decode())
    symbol = None
    if info.dli_sname and info.dli_saddr == address:
      symbol = info.dli_sname.decode()
    return where, symbol
  return None, None

def _static(table):
  '''Whether an info table or a data type belongs to a compiled object.'''
  flags = table.flags
  if isinstance(flags, str):
    # The flags of a DataType are a char.
    flags = ord(flags)
  return bool(flags & common.F_STATIC_OBJECT)

def _address_of(lib, symbol):
  '''
  The address of the data ``symbol`` as ``lib`` (a ctypes.CDLL) resolves
  it: its own definition first, then those of the objects it needs.  None
  when none resolves it.
  '''
  try:
    return ctypes.addressof(ctypes.c_char.in_dll(lib, symbol))
  except ValueError:
    return None


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestLibraryTablesInTheirObjects(cytest.TestCase):
  '''
  No table of a module of the Curry library loaded from its compiled object
  is defined by the object and by the runtime library both.  The dynamic
  linker binds every reference to the first definition in the global
  scope, so the dynamic initializer of the object writes its table over the
  table of the runtime, and an unload of the object leaves the table of the
  runtime pointing into unmapped memory (issue #124: the table of
  Prelude.seq over the table of the &> of the runtime, both under the
  symbol CyI7Prelude3seq).  A table of the module that lies in the runtime
  library is a built-in the object imports and does not define (the
  built-ins of the Prelude; Values of Control.SetFunctions).
  '''
  def test_tables(self):
    interp = curry.getInterpreter()
    libcyrt_path = config.installed_path('lib', 'libcyrt.so')
    libcyrt = os.path.realpath(libcyrt_path)
    runtime = ctypes.CDLL(libcyrt_path)
    checked = 0
    for M in (interp.prelude, interp.setfunctions):
      h = getHandle(M)
      if h.sofilename is None:
        continue
      sofile = os.path.realpath(h.sofilename)
      shlib = ctypes.CDLL(h.sofilename)
      for name, sym in sorted(inspect.symbols(M).items()):
        where, symbol = _symbol_of(sym.info.address)
        self.assertIn(
            where, (libcyrt, sofile)
          , 'the table of %s.%s lies in %s' % (h.fullname, name, where)
          )
        if where == libcyrt and symbol is not None:
          self.assertEqual(
              _address_of(shlib, symbol), _address_of(runtime, symbol)
            , 'the object of %s and the runtime library both define %s, '
              'the table of %s.%s' % (h.fullname, symbol, h.fullname, name)
            )
        checked += 1
    if not checked:
      self.skipTest('no module of the library is loaded from its object')

  def test_no_table_made_at_run_time(self):
    '''
    Every type and constructor of a module of the library loaded from its
    object is a static table, of the object or of the runtime library: the
    materializer makes none at run time.  The merge of the built-ins lists
    types of the Prelude without their material that the runtime does not
    register (the tuples from (,,) up, and (->)), and the record of the
    object carries them.  The materializer asked for a built-in alone before
    it made the tables of a type; when get_builtin_type stopped answering
    for a static table of the object (issue #113) it made a second table
    per type and constructor, which replaced the entry of the module, and
    under tiered execution the clear at a reload kept the tables and the
    object with them (the regression of
    test_reload_from_tiered_into_interpreter).
    '''
    interp = curry.getInterpreter()
    checked = 0
    for M in (interp.prelude, interp.setfunctions):
      h = getHandle(M)
      if h.sofilename is None:
        continue
      module = h.backend_handle
      for itype in h.icurry.types.values():
        typedef = module.get_type(itype.name)
        self.assertIsNotNone(
            typedef, 'module %s has no type %s' % (h.fullname, itype.name)
          )
        self.assertTrue(
            _static(typedef)
          , 'the type %s.%s was made at run time' % (h.fullname, itype.name)
          )
        for ictor in itype.constructors:
          info = module.get_infotable(ictor.name)
          self.assertIsNotNone(
              info, 'module %s has no table %s' % (h.fullname, ictor.name)
            )
          self.assertTrue(
              _static(info)
            , 'the table of %s.%s was made at run time'
                  % (h.fullname, ictor.name)
            )
          checked += 1
    if not checked:
      self.skipTest('no module of the library is loaded from its object')
