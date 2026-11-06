"""Data.Global initialization belongs to the caller's encapsulated search."""
import cytest # from ./lib; must be first
from pathlib import Path
import tempfile
import curry
from unit_cpm_primitives import NAMED_GLOBALS


class TestIssue215(cytest.TestCase):
  @cytest.with_flags(interpret='all', jit='off', rotation='steps:65536',
                    checker=True)
  def test_named_global_resumes_ground_pair_x_first(self):
    self.check_resumed_ground_pair(first=0)

  @cytest.with_flags(interpret='all', jit='off', rotation='steps:65536',
                    checker=True)
  def test_named_global_resumes_ground_pair_y_first(self):
    self.check_resumed_ground_pair(first=1)

  def check_resumed_ground_pair(self, first):
    from curry import inspect
    from curry.backends.cxx import curryrtbindings as native
    module = curry.compile(NAMED_GLOBALS + '''
goal :: Int -> Int -> GlobalT (Int,Int)
goal x y = globalT "CPM.pair" (x,y)
readOld :: IO (Int,Int)
readOld = readGlobalT (GlobalT "CPM.pair")
''')
    variables = [curry.term(curry.free(name, type='Int'))._node
                 for name in ('x', 'y')]
    rts = native.RuntimeState(cytest.raw.interp(),
                             cytest.raw.expr(module.goal, *variables))
    try:
      def assert_waiting():
        with self.assertRaises(curry.SuspensionError):
          next(rts.generate_values())
        self.assertEqual(rts.queue_size, 1)
        with self.assertRaisesRegex(curry.EvaluationError, 'not initialized'):
          curry.eval(module.readOld).one()
      assert_waiting()
      vids = [inspect.fwd_chain_target(var).successors[0] for var in variables]
      bindings = (17, 23)
      native.checker_debug_bind(rts, vids[first], cytest.raw.expr(bindings[first]))
      assert_waiting()
      last = 1 - first
      native.checker_debug_bind(rts, vids[last], cytest.raw.expr(bindings[last]))
      handles = list(rts.generate_values())
      self.assertEqual([str(handle) for handle in handles], ['GlobalT "CPM.pair"'])
      self.assertEqual(curry.eval(module.readOld).one(), bindings)
      self.assertEqual(rts.queue_size, 0)
    finally:
      rts.close()

  @cytest.with_flags(interpret='all', jit='off', rotation='steps:65536',
                    checker=True)
  def test_named_global_suspension_keeps_alternative_and_resumes(self):
    from curry.backends.cxx import curryrtbindings as native
    module = curry.compile(NAMED_GLOBALS + '''
goal :: Int -> GlobalT Int
goal x = globalT "CPM.suspended" x ? globalT "CPM.suspended" 42
readOld :: IO Int
readOld = readGlobalT (GlobalT "CPM.suspended")
''')
    x = curry.term(curry.free('x', type='Int'))._node
    rts = native.RuntimeState(cytest.raw.interp(), cytest.raw.expr(module.goal, x))
    try:
      handle = next(rts.generate_values())
      self.assertEqual(str(handle), 'GlobalT "CPM.suspended"')
      self.assertEqual(curry.eval(module.readOld).one(), 42)
      self.assertEqual(rts.queue_size, 1)
      # Bind the remaining configuration's variable, using the checker's
      # existing binding hook to resume the same evaluation and capsule.
      from curry import inspect
      vid = inspect.fwd_chain_target(x).successors[0]
      native.checker_debug_bind(rts, vid, cytest.raw.expr(17))
      handles = list(rts.generate_values())
      self.assertEqual(len(handles), 1)
      self.assertEqual(str(handles[0]), str(handle))
      self.assertEqual(curry.eval(module.readOld).one(), 42)
    finally:
      rts.close()

  @cytest.with_flags(interpret='all', jit='off', rotation='steps:1000')
  def test_named_global_competing_store_keeps_multiplicity_error(self):
    module = curry.compile(NAMED_GLOBALS + '''
slow :: Int -> Int
slow n = if n == 0 then 22 else slow (n-1)
goal :: GlobalT Int
goal = globalT "CPM.competing" (11 ? slow 20000)
     ? globalT "CPM.competing" 42
readOld :: IO Int
readOld = readGlobalT (GlobalT "CPM.competing")
''')
    values = iter(curry.eval(module.goal))
    next(values)
    self.assertEqual(curry.eval(module.readOld).one(), 42)
    with self.assertRaisesRegex(curry.EvaluationError,
        'global CPM.competing has more than one initial value'):
      next(values)
    self.assertEqual(curry.eval(module.readOld).one(), 42)

  @cytest.with_flags(interpret='all', jit='off', rotation='steps:1000')
  def test_named_global_competing_single_value_keeps_stored_entry(self):
    module = curry.compile(NAMED_GLOBALS + '''
slow :: Int -> Int
slow n = if n == 0 then 22 else slow (n-1)
goal :: GlobalT Int
goal = globalT "CPM.single" (slow 20000) ? globalT "CPM.single" 42
readOld :: IO Int
readOld = readGlobalT (GlobalT "CPM.single")
''')
    values = iter(curry.eval(module.goal))
    next(values)
    self.assertEqual(curry.eval(module.readOld).one(), 42)
    next(values)
    self.assertEqual(list(values), [])
    self.assertEqual(curry.eval(module.readOld).one(), 42)

  def test_named_global_initializer_uses_callers_binding(self):
    module = curry.compile(NAMED_GLOBALS + '''
goal :: IO Int
goal = x =:= 42 &> readGlobalT (globalT "CPM.bound" (x+1)) where x free
''')
    self.assertEqual(curry.eval(module.goal).one(), 43)

  def test_named_global_initializer_uses_callers_choice(self):
    module = curry.compile(NAMED_GLOBALS + '''
goal :: GlobalT Int
goal = if x == 22 then globalT "CPM.decided" (x+1) else failed
  where x = 11 ? 22
''')
    handle = curry.eval(module.goal).one()
    self.assertEqual(curry.eval(module.readGlobalT(handle)).one(), 23)

  @cytest.with_flags(interpret='all', jit='off', rotation='steps:7')
  def test_named_global_multiple_initial_values_after_rotation(self):
    module = curry.compile(NAMED_GLOBALS + '''
slow :: Int -> Int
slow n = if n == 0 then 22 else slow (n-1)
goal :: IO Int
goal = readGlobalT (globalT "CPM.multiple" (11 ? slow 200))
readOld :: IO Int
readOld = readGlobalT (GlobalT "CPM.multiple")
''')
    with self.assertRaisesRegex(curry.EvaluationError,
        'global CPM.multiple has more than one initial value'):
      curry.eval(module.goal).one()
    with self.assertRaisesRegex(curry.EvaluationError, 'not initialized'):
      curry.eval(module.readOld).one()

  def test_named_global_failed_initialization_leaves_no_entry(self):
    module = curry.compile(NAMED_GLOBALS + '''
initialize :: Int -> IO Int
initialize n = readGlobalT (globalT "CPM.retry" n)
readOld :: IO Int
readOld = readGlobalT (GlobalT "CPM.retry")
empty :: IO Int
empty = initialize failed
''')
    self.assertEqual(list(curry.eval(module.empty)), [])
    with self.assertRaisesRegex(curry.EvaluationError, 'not initialized'):
      curry.eval(module.readOld).one()
    self.assertEqual(curry.eval(module.initialize(42)).one(), 42)
    self.assertEqual(curry.eval(module.readOld).one(), 42)

  def test_named_global_python_initializer_and_reentry(self):
    from curry.backends.cxx import curryrtbindings as native
    from curry.interpreter import Interpreter
    first = cytest.raw.interp()
    second = Interpreter(flags={'interpret': 'all', 'jit': 'off'})
    calls = []
    def callback(n):
      calls.append(n)
      # The bridge itself types this result through the caller's signature
      # table; reentry must also obey the ordinary host callback rules.
      return first.eval(pa.addOne(n)).one() + second.eval(pb.ten).one()
    native.register_primitive('GlobalInitializer.callback', 1, callback)
    source = '''module GlobalInitializer where
callback :: Int -> Int
callback external
addOne :: Int -> Int
addOne n = n+1
ten :: Int
ten = 10
'''
    pa, pb = first.compile(source), second.compile(source)
    source = NAMED_GLOBALS.replace('data GlobalT',
        'import GlobalInitializer\ndata GlobalT') + '''
initialize :: Int -> IO Int
initialize n = readGlobalT (globalT "CPM.python" (callback n))
'''
    a, b = first.compile(source), second.compile(source)
    self.assertEqual(first.eval(a.initialize(31)).one(), 42)
    self.assertEqual(second.eval(b.initialize(51)).one(), 62)
    self.assertEqual(calls, [31, 51])
    self.assertEqual(first.eval(a.initialize(0)).one(), 42)
    self.assertEqual(second.eval(b.initialize(0)).one(), 62)
    self.assertEqual(calls, [31, 51])

  def test_named_global_collection_during_initialization(self):
    import gc
    from curry.backends.cxx import curryrtbindings as native
    seen = []
    def sample(n):
      seen.append(native.gc_collections())
      return n
    native.register_primitive('GlobalCollection.sample', 1, sample)
    curry.compile('''module GlobalCollection where
sample :: Int -> Int
sample external
''')
    module = curry.compile(NAMED_GLOBALS.replace('data GlobalT',
        'import GlobalCollection\ndata GlobalT') + '''
goal :: IO [Int]
goal = readGlobalT (globalT "CPM.collecting" (map sample [1..300]))
''')
    gc.collect()
    native.gc_collect()
    threshold = native.gc_threshold()
    try:
      native.gc_set_threshold(64)
      self.assertEqual(curry.eval(module.goal).one(), list(range(1, 301)))
    finally:
      native.gc_set_threshold(threshold)
    self.assertEqual(len(seen), 300)
    self.assertGreater(seen[-1], seen[0])
    native.gc_verify()

  def test_named_global_replacement_and_destruction_release_values(self):
    import gc
    import weakref
    from curry.backends.cxx import curryrtbindings as native
    from curry.interpreter import Interpreter
    source = NAMED_GLOBALS.replace('data GlobalT',
        'import System.IO\ndata GlobalT') + '''
handle :: GlobalT Handle
handle = globalT "CPM.handle" stdin
storeHandle :: String -> IO ()
storeHandle path = do
  h <- openFile path WriteMode
  hPutChar h 'x'
  writeGlobalT handle h
replace :: IO ()
replace = writeGlobalT handle stdout
readHandle :: IO Handle
readHandle = readGlobalT handle
'''
    def collect():
      gc.collect()
      # MPS finalization can require another trace after the first message.
      native.gc_collect()
      native.gc_collect()
    with tempfile.TemporaryDirectory() as directory:
      interp = Interpreter(flags={'interpret': 'all', 'jit': 'off'})
      module = interp.compile(source)
      replaced = Path(directory) / 'replaced'
      interp.eval(module.storeHandle(str(replaced))).one()
      collect()
      self.assertEqual(replaced.read_bytes(), b'')
      interp.eval(module.replace).one()
      collect()
      self.assertEqual(replaced.read_bytes(), b'x')
      destroyed = Path(directory) / 'destroyed'
      interp.eval(module.storeHandle(str(destroyed))).one()
      collect()
      self.assertEqual(destroyed.read_bytes(), b'')
      ref = weakref.ref(interp)
      del module, interp
      collect()
      self.assertIsNone(ref())
      self.assertEqual(destroyed.read_bytes(), b'x')

  @cytest.skipUnlessGcBackend('mps', 'requires a moving collector')
  def test_named_global_mps_moves_stored_handle(self):
    import gc
    from curry.backends.cxx import curryrtbindings as native
    module = curry.compile(NAMED_GLOBALS.replace('data GlobalT',
        'import System.IO\ndata GlobalT') + '''
storeHandle :: String -> IO ()
storeHandle path = do
  h <- openFile path WriteMode
  writeGlobalT (globalT "CPM.moving" stdin) h
readHandle :: IO Handle
readHandle = readGlobalT (GlobalT "CPM.moving")
useHandle :: IO ()
useHandle = do
  h <- readHandle
  hPutChar h 'm'
  hClose h
''')
    def address():
      # Handles keep identity across the store's copying boundaries. Keep
      # only an integer address so Python does not pin the stored node.
      return cytest.raw.values(module.readHandle).one().id()
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'moving'
      curry.eval(module.storeHandle(str(path))).one()
      before = address()
      moved = False
      for _ in range(10):
        gc.collect()
        native.gc_collect()
        if address() != before:
          moved = True
          break
      self.assertTrue(moved, 'the stored handle never moved')
      native.gc_verify()
      curry.eval(module.useHandle).one()
      self.assertEqual(path.read_bytes(), b'm')
