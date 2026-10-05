'''
Tests for the shared literal nodes of the C++ backend.

The runtime keeps one node for each small integer and each ASCII character
(int_ and char_ in cyrt/builtins.hpp), and a generated module keeps one node
for each of its other literals, made when the module loads (literal_node;
internLiteralNode in backends/cxx/compiler.py).  The nodes live in an arena
outside the heap of the collector for the life of the process
(literal_reserve in cyrt/graph/memory.hpp).  So a step that spells a literal
allocates nothing.  The programs are in data/curry/CxxLiterals.curry.
'''
import cytest # from ./lib; must be first
from curry import common, config
from curry.backends.generic.eval import evaluator
from curry.objects.handle import getHandle
import curry, os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# The cap on the address space of a child, in bytes, and the time it may
# take.  A child loads the compiled module from the cache (see setUpClass).
ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

# A child on the C++ backend with the Prelude loaded.
CHILD = '''
import curry
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
curry.import_('Prelude')
'''

def raw(value):
  '''The node of a value or an expression.'''
  return getattr(value, 'raw_expr', value)

def step(expr, until=None, limit=64):
  '''
  One rewrite step at the root of a raw expression, or steps until ``until``
  holds (see unit_cxx_rewrite.py).
  '''
  for _ in range(limit):
    evaluator.single_step(curry.getInterpreter(), expr)
    if until is None or until(expr):
      return expr
  raise AssertionError('the root did not change in %d steps' % limit)

def result(expr):
  '''
  The result of a step at ``expr``: the expression itself after a rewrite in
  place, or the target of the forward node a larger result leaves.
  '''
  if expr.info.tag == common.T_FWD:
    return expr.successors[0]
  return expr

def evaluated(goal, *args):
  '''The raw node of a nullary function of the test module, evaluated.'''
  expr = curry.raw_expr(goal, *args)
  name = expr.info.name
  step(expr, until=lambda e: e.info.name != name)
  return result(expr)


class TestValues(cytest.TestCase):
  '''The programs give the same values on both backends.'''
  def values(self, *goal):
    return list(curry.eval(*goal, converter='topython'))

  def test_values(self):
    M = curry.import_('CxxLiterals')
    self.assertEqual(self.values(M.small), [(7, 'a')])
    self.assertEqual(self.values(M.large), [(100000, '\u03bb', 2.5)])
    self.assertEqual(self.values(M.largeAgain), [(100000, 0)])
    self.assertEqual(self.values(M.bounds), [[1023, 1024]])
    self.assertEqual(
        self.values(M.eqs), [[True, False, True, True, True, True, True, True]]
      )
    self.assertEqual(self.values(M.unify), [2])
    self.assertEqual(sorted(self.values(M.narrowed)), [(10, 1), (20, 2)])
    self.assertEqual(self.values(M.countDown, 1000), [0])
    self.assertEqual(self.values(M.greeting), ['hi!\u03bb'])
    self.assertEqual(self.values(M.twice), [(1, 1)])

  def test_show(self):
    '''
    One node for both components of (1, 1) shows as two components.  The
    repr form marks a cycle with an ellipsis, not a shared leaf.
    '''
    M = curry.import_('CxxLiterals')
    value, = curry.eval(M.twice)
    self.assertEqual(str(value), '(1, 1)')
    self.assertEqual(repr(raw(value)), '<(,) <Int 1> <Int 1>>')
    value, = curry.eval(M.greeting)
    self.assertEqual(str(value), '"hi!\\955"')


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestTables(cytest.TestCase):
  '''
  The tables of the runtime and the literal nodes of a module, through the
  bindings: small_int, small_char, gc_literal_count, and the successors of
  stepped expressions.
  '''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('CxxLiterals')

  def test_bounds(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    self.assertEqual(cyrt.SMALL_INT_MIN, -128)
    self.assertEqual(cyrt.SMALL_INT_MAX, 1023)
    self.assertEqual(cyrt.SMALL_CHAR_MAX, 127)
    for value in -128, -1, 0, 1, 1023:
      node = cyrt.small_int(value)
      self.assertEqual(node.info.name, 'Int')
      self.assertEqual(curry.topython(node), value)
      self.assertEqual(node.id(), cyrt.small_int(value).id())
      self.assertTrue(cyrt.gc_is_literal(node))
    self.assertEqual(str(cyrt.small_int(1023)), '1023')
    self.assertFalse(cyrt.gc_is_literal(curry.raw_expr(1)))
    self.assertFalse(cyrt.gc_is_literal(None))
    self.assertNotEqual(cyrt.small_int(0).id(), cyrt.small_int(1).id())
    for value in -129, 1024:
      with self.assertRaises(ValueError):
        cyrt.small_int(value)
    for char in '\0', 'a', 'z', '\x7f':
      node = cyrt.small_char(char)
      self.assertEqual(node.info.name, 'Char')
      self.assertEqual(curry.topython(node), char)
      self.assertEqual(node.id(), cyrt.small_char(char).id())
    self.assertEqual(str(cyrt.small_char('a')), "'a'")
    for text in '\x80', '\u03bb', 'ab', '':
      with self.assertRaises(ValueError):
        cyrt.small_char(text)

  def test_small_values_are_shared(self):
    '''A step that spells a small literal uses the node of the table.'''
    from curry.backends.cxx import cyrtbindings as cyrt
    pair = evaluated(self.M.small)
    self.assertEqual(pair.info.name, '(,)')
    seven, a = pair.successors
    self.assertEqual(seven.id(), cyrt.small_int(7).id())
    self.assertEqual(a.id(), cyrt.small_char('a').id())
    self.assertEqual(str(seven), '7')
    self.assertEqual(str(a), "'a'")
    one, other = evaluated(self.M.twice).successors
    self.assertEqual(one.id(), other.id())
    self.assertEqual(one.id(), cyrt.small_int(1).id())

  def test_large_literals_are_module_nodes(self):
    '''
    A literal outside the tables is a node of the module: every occurrence
    in the module is the same node, and it is not a node of a table.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    big, lam, flt = evaluated(self.M.large).successors
    self.assertEqual(str(big), '100000')
    self.assertEqual(curry.topython(lam), '\u03bb')
    self.assertEqual(curry.topython(flt), 2.5)
    again, zero = evaluated(self.M.largeAgain).successors
    self.assertEqual(again.id(), big.id())
    self.assertEqual(zero.id(), cyrt.small_int(0).id())
    self.assertTrue(all(cyrt.gc_is_literal(node) for node in (big, lam, flt)))
    # A second evaluation of the same function spells the same node.
    big2, _, _ = evaluated(self.M.large).successors
    self.assertEqual(big2.id(), big.id())
    last, high = self.listitems(evaluated(self.M.bounds))
    self.assertEqual(last.id(), cyrt.small_int(1023).id())
    self.assertEqual(str(high), '1024')
    self.assertNotEqual(high.id(), big.id())

  def listitems(self, node):
    items = []
    while node.info.name == ':':
      head, node = node.successors
      items.append(head)
    return items

  def test_literal_count(self):
    '''
    The tables are full when the bindings load, and a module adds one node
    per literal outside them when it loads.
    '''
    shlib = getHandle(self.M).icurry.metadata['cxx.shlib']
    text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')
    proc = cytest.run_in_subprocess(CHILD + '''
tables = cyrt.SMALL_INT_MAX - cyrt.SMALL_INT_MIN + 1 + cyrt.SMALL_CHAR_MAX + 1
before = cyrt.gc_literal_count()
assert before >= tables, (before, tables)
M = curry.import_('CxxLiterals')
print(cyrt.gc_literal_count() - before)
''', TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    # The arena also holds the partial applications without arguments of
    # the module (partial_node; see unit_cxx_partial.py); this module spells
    # none.
    self.assertEqual(
        int(proc.stdout)
      , text.count('literal_node(') + text.count('partial_node(')
      )
    self.assertEqual(text.count('literal_node('), 4)

  def test_shared_nodes_survive_collections(self):
    '''
    The nodes of the tables and of a module are outside the heap of the
    collector: after many collections the values that use them are right.
    '''
    n = 2000 if cytest.GC_STRESS else 20000
    proc = cytest.run_in_subprocess(CHILD + '''
M = curry.import_('CxxLiterals')
cyrt.gc_set_threshold(1 << 14)
before = cyrt.gc_collections()
assert next(curry.eval(M.countDown, %(n)d)) == 0
collections = cyrt.gc_collections() - before
assert collections > 0, collections
assert str(cyrt.small_int(5)) == '5'
assert str(cyrt.small_char('a')) == "'a'"
assert next(curry.eval(M.small)) == (7, 'a')
assert next(curry.eval(M.large)) == (100000, '\\u03bb', 2.5)
assert next(curry.eval(M.bounds)) == [1023, 1024]
assert next(curry.eval(M.countDown, 100)) == 0
print('collections', collections)
''' % {'n': n}, TIMEOUT, address_space=ADDRESS_SPACE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertIn('collections', proc.stdout)

  def test_literals_allocate_nothing(self):
    '''
    A loop that spells the literals 0 and 1 in every iteration allocates
    nothing for them.  Each iteration of countDown allocates the lifted case
    function, the comparison, and the difference: three nodes.  Before the
    tables it allocated the two literal nodes as well.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    n = 1000
    before = cyrt.gc_allocation_count()
    value = next(curry.eval(self.M.countDown, n, converter='topython'))
    allocated = cyrt.gc_allocation_count() - before
    self.assertEqual(value, 0)
    self.assertLess(allocated, 4 * n)

  def test_forwarding_a_value_is_refused(self):
    '''
    A value is never a redex.  The bindings refuse to forward a node of a
    primitive value, which may be a shared node.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    one = cyrt.small_int(1)
    with self.assertRaisesRegex(ValueError, 'cannot forward a value'):
      one.forward_to(cyrt.small_int(2))
    with self.assertRaisesRegex(ValueError, 'cannot forward a value'):
      curry.raw_expr(5).forward_to(curry.raw_expr(6))
    with self.assertRaisesRegex(ValueError, 'cannot forward a value'):
      curry.raw_expr('x').forward_to(curry.raw_expr(6))
    self.assertEqual(str(one), '1')
    self.assertEqual(str(cyrt.small_int(1)), '1')

  def test_generated_code(self):
    '''
    The generator spells a small literal as a table lookup and any other
    literal as the node of the module, defined once.
    '''
    shlib = getHandle(self.M).icurry.metadata['cxx.shlib']
    text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')
    for lookup in 'int_(7)', "char_(U'a')", 'int_(0)', 'int_(1)', 'int_(1023)':
      self.assertIn(lookup, text)
    for spelled in 'int_(100000)', 'int_(1024)', 'float_(', "char_(U'\\x3bb')":
      self.assertNotIn(spelled, text)
    node = r'CyL\d+__\d+'
    self.assertRegex(
        text, r'static Node \* const %s = literal_node\(&CyI7Prelude3Int, '
              r'Arg\(100000\)\);' % node
      )
    self.assertRegex(
        text, r'literal_node\(&CyI7Prelude4Char, Arg\(U\'\\x3bb\'\)\);'
      )
    self.assertRegex(text, r'literal_node\(&CyI7Prelude5Float, Arg\(2\.5\)\);')
    self.assertEqual(text.count('Arg(100000)'), 1)
    self.assertRegex(
        text, r'_0->forward_to\(&CyI7Prelude6_Y_m_y, %s, int_\(0\)\);' % node
      )
    self.assertRegex(
        text, r'_0->forward_to\(&CyI7Prelude8_Y_m_m_y, %s, %s, %s\);'
              % (node, node, node)
      )


@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
class TestLiteralTables(cytest.TestCase):
  '''
  int_, char_, float_, literal_node, and the collector on the shared nodes.
  The checks are a C++ program, data/cxx/literals_test.cpp, compiled against
  the installed runtime with its assertions on.
  '''
  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'literals_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-literals-')
    try:
      exe = os.path.join(tmpdir, 'literals_test')
      cmd = [
          config.cxx_tool(), '-std=c++17', '-O2', '-Wall'
        , '-I%s' % config.installed_path('include')
        , source, '-o', exe
        , '-L%s' % libdir, '-lcyrt', '-Wl,-rpath,%s' % libdir
        ]
      proc = subprocess.run(cmd, capture_output=True, text=True)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stderr, '', 'the compiler warned')
      proc = subprocess.run(
          ['timeout', str(TIMEOUT), exe], capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
      self.assertEqual(proc.stdout, 'ok\n')
    finally:
      shutil.rmtree(tmpdir, ignore_errors=True)
