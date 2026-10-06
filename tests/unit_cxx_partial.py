'''
Tests for the flat partial applications of the C++ backend.

A partial application is one node: the missing count, the info table of the
head, and the arguments in the slots after them (PartApplicNode in
cyrt/builtins.hpp).  Each number of arguments has an info table of its own
(partapplic_info); apply appends an argument in one allocation
(Node::extend_partial).  A function used as a value, a partial application
without arguments, is one node per module, made when the module loads
(partial_node; internPartialNode in backends/cxx/compiler.py).  The programs
are in data/curry/CxxPartial.curry.
'''
import cytest # from ./lib; must be first
from curry import common, config
from curry.backends.cxx import compiler as cxx_compiler
from curry.backends.generic.eval import evaluator
from curry.objects.handle import getHandle
import curry, os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 120

def raw(value):
  '''The node of a value or an expression.'''
  return getattr(value, 'raw_expr', value)

def step(expr, until=None, limit=64):
  '''
  One rewrite step at the root of a raw expression, or steps until ``until``
  holds (see unit_cxx_rewrite.py).
  '''
  for _ in range(limit):
    if expr.info.tag != common.T_FUNC:
      raise AssertionError('the root is not a function application: %r' % expr)
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


class TestValues(cytest.TestCase):
  '''The programs give the same values on both backends.'''
  def values(self, *goal):
    return list(curry.eval(*goal, converter='topython'))

  def test_apply(self):
    M = curry.import_('CxxPartial')
    self.assertEqual(self.values(M.zero), [6])
    self.assertEqual(self.values(M.one), [6])
    self.assertEqual(self.values(M.two), [6])
    self.assertEqual(self.values(M.twice), [12])
    self.assertEqual(str(next(curry.eval(M.justs))), '[Just 1, Just 2]')
    self.assertEqual(self.values(M.sections), [[2, 3, 6]])
    self.assertEqual(self.values(M.loop, 0, 100), [100])
    self.assertEqual(self.values(M.applyInc, 5, 0), [6])
    self.assertEqual(self.values(M.app, M.inc, 41), [42])
    self.assertEqual(self.values(M.app, curry.raw_expr(M.plus3, 1, 2), 3), [6])

  def test_many_arguments(self):
    M = curry.import_('CxxPartial')
    total = 36 * 37 // 2
    self.assertEqual(self.values(M.manyPartial), [total])
    self.assertEqual(self.values(M.manyApply), [total])
    self.assertEqual(self.values(M.many, *range(1, 37)), [total])

  def test_set_functions(self):
    M = curry.import_('CxxPartial')
    self.assertEqual(self.values(M.set3Values), [[4, 5]])
    self.assertEqual(self.values(M.set0Value), [[1, 2]])
    self.assertEqual(self.values(M.set1Lambda), [[1, 10]])
    # The choice is in the argument, outside the set function: two values.
    self.assertEqual(sorted(self.values(M.set1Partial)), [[6], [7]])
    # The choice is in an argument again: two sets of one value.
    total = 36 * 37 // 2
    self.assertEqual(
        sorted(self.values(M.set2Many)), [[total - 35], [total]]
      )

  def test_show(self):
    '''
    A partial application with arguments is written (f a b), one without
    arguments f; a function value shared by two positions is written twice.
    '''
    M = curry.import_('CxxPartial')
    self.assertEqual(str(curry.raw_expr(M.plus3, 1, 2)), '(plus3 1 2)')
    self.assertEqual(str(curry.raw_expr(M.plus3)), 'plus3')
    value, = curry.eval(M.partials)
    self.assertEqual(str(value), '[(plus3 1 2), (plus3 1 2)]')
    value, = curry.eval(M.incTwice)
    self.assertEqual(str(value), '(inc, inc)')

  def test_equality(self):
    '''Partial applications are compared by head, count, and arguments.'''
    M = curry.import_('CxxPartial')
    e = lambda *args: curry.raw_expr(*args)
    self.assertEqual(e(M.plus3, 1), e(M.plus3, 1))
    self.assertEqual(e(M.plus3), e(M.plus3))
    self.assertEqual(e(M.plus3, 1, [2, 3]), e(M.plus3, 1, [2, 3]))
    self.assertNotEqual(e(M.plus3, 1), e(M.plus3, 2))
    self.assertNotEqual(e(M.plus3, 1), e(M.plus3, 1, 2))
    self.assertNotEqual(e(M.plus3, 1), e(M.plus2, 1))
    self.assertNotEqual(e(M.plus3), e(M.plus2))


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestLayout(cytest.TestCase):
  '''The nodes through the bindings: the slots, the info tables, apply.'''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('CxxPartial')

  def assertPartial(self, node, missing, args):
    self.assertEqual(node.info.name, '_PartApplic')
    self.assertTrue(node.info.is_partial)
    self.assertEqual(node.info.arity, 2 + len(args))
    self.assertEqual(node.info.format, 'ix' + 'p' * len(args))
    self.assertEqual(node.successors[0], missing)
    self.assertEqual(
        [curry.topython(s) for s in node.successors[2:]], args
      )

  def test_slots(self):
    M = self.M
    self.assertPartial(curry.raw_expr(M.plus3), 3, [])
    self.assertPartial(curry.raw_expr(M.plus3, 1), 2, [1])
    self.assertPartial(curry.raw_expr(M.plus3, 1, 2), 1, [1, 2])
    # The head is slot 1, an unboxed pointer; the same for every count.
    heads = set(
        curry.raw_expr(M.plus3, *args).successors[1]
            for args in ([], [1], [1, 2])
      )
    self.assertEqual(len(heads), 1)
    self.assertNotEqual(heads, {curry.raw_expr(M.plus2).successors[1]})

  def test_many_arguments(self):
    '''A partial application beyond the cached range of the family.'''
    M = self.M
    for n in 31, 32, 33, 35:
      args = list(range(1, n + 1))
      self.assertPartial(curry.raw_expr(M.many, *args), 36 - n, args)
    a = curry.raw_expr(M.many, *range(1, 34))
    b = curry.raw_expr(M.many, *range(1, 34))
    self.assertEqual(a.info.arity, 35)
    self.assertIs(a.info, b.info)

  def test_apply_extends(self):
    '''
    apply on an incomplete partial application allocates one node, with the
    arguments inline and one argument fewer missing.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    M = self.M
    apply_ = curry.symbol('Prelude.apply')
    e = curry.raw_expr(apply_, curry.raw_expr(M.plus3, 1), 2)
    before = cyrt.gc_allocation_count()
    step(e)
    self.assertEqual(cyrt.gc_allocation_count() - before, 1)
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertPartial(result(e), 1, [1, 2])
    # The same for a function value.
    e = curry.raw_expr(apply_, curry.raw_expr(M.plus3), 7)
    step(e)
    self.assertPartial(result(e), 2, [7])

  def test_apply_completes(self):
    '''
    The last apply writes the function node: into the redex when it fits
    (two arguments), into a new node otherwise, the arguments in order.
    '''
    M = self.M
    apply_ = curry.symbol('Prelude.apply')
    e = curry.raw_expr(apply_, curry.raw_expr(M.plus2, 1), 2)
    step(e)
    self.assertEqual(e.info.name, 'plus2')
    self.assertEqual([curry.topython(s) for s in e.successors], [1, 2])
    e = curry.raw_expr(apply_, curry.raw_expr(M.plus3, 1, 2), 3)
    step(e)
    self.assertEqual(e.info.tag, common.T_FWD)
    node = result(e)
    self.assertEqual(node.info.name, 'plus3')
    self.assertEqual([curry.topython(s) for s in node.successors], [1, 2, 3])
    args = list(range(1, 36))
    e = curry.raw_expr(apply_, curry.raw_expr(M.many, *args), 36)
    step(e)
    node = result(e)
    self.assertEqual(node.info.name, 'many')
    self.assertEqual([curry.topython(s) for s in node.successors], args + [36])

  def test_repr(self):
    M = self.M
    self.assertEqual(repr(curry.raw_expr(M.plus3)), '<_PartApplic 3 plus3>')
    self.assertEqual(
        repr(curry.raw_expr(M.plus3, 1, 2))
      , '<_PartApplic 1 plus3 <Int 1> <Int 2>>'
      )
    value, = curry.eval(M.incTwice)
    self.assertEqual(
        repr(raw(value)), '<(,) <_PartApplic 1 inc> <_PartApplic 1 inc>>'
      )

  def test_copy(self):
    '''A copy of a partial application keeps its arguments.'''
    M = self.M
    e = curry.raw_expr(M.plus3, 1, [2])
    for c in e.copy(), e.__deepcopy__():
      self.assertPartial(c, 1, [1, [2]])
      self.assertEqual(c, e)
      self.assertNotEqual(c.id(), e.id())


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestSharedFunctionValues(cytest.TestCase):
  '''
  A partial application without arguments spelled by a step is a node of
  the module: made once at load, outside the heap of the collector.
  '''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('CxxPartial')

  def function_value(self):
    '''
    The function value a step of applyInc puts into its result: applyInc x
    _ = app inc x is rewritten in place to apply inc x (app is an alias of
    apply, which the optimizer inlines).
    '''
    e = curry.raw_expr(self.M.applyInc, 5, 0)
    step(e, until=lambda e: e.info.name == 'apply')
    return e.successors[0]

  def test_shared(self):
    from curry.backends.cxx import cyrtbindings as cyrt
    node = self.function_value()
    self.assertEqual(node.info.name, '_PartApplic')
    self.assertEqual(node.successors[0], 1)
    self.assertTrue(cyrt.gc_is_literal(node))
    # One node for every execution of the step.
    self.assertEqual(self.function_value().id(), node.id())
    # A node made from Python is a heap node; it is equal to the shared one.
    made = curry.raw_expr(self.M.inc)
    self.assertFalse(cyrt.gc_is_literal(made))
    self.assertEqual(made, node)

  def test_loop_allocates_nothing_for_the_function(self):
    '''
    Every iteration of loop spells inc, applies it, and counts down.  It
    allocates five nodes (the lifted case, its comparison, the application,
    the difference, and the sum); the function value is not one of them (a
    file of format 7 allocated six).
    '''
    from curry.backends.cxx import cyrtbindings as cyrt
    n = 1000
    before = cyrt.gc_allocation_count()
    self.assertEqual(curry.topython(next(curry.eval(self.M.loop, 0, n))), n)
    nodes = cyrt.gc_allocation_count() - before
    self.assertLess(nodes, 6 * n)

  def test_forwarding_a_shared_node_is_refused(self):
    node = self.function_value()
    with self.assertRaisesRegex(ValueError, 'cannot forward the shared node'):
      node.forward_to(curry.raw_expr(1))
    self.assertEqual(node.info.name, '_PartApplic')

  def test_stepping_a_value_is_refused(self):
    '''
    single_step refuses a root without a step (a constructor, a value, a
    forward node) instead of calling a null pointer.
    '''
    for expr in self.function_value(), curry.raw_expr(1), curry.raw_expr([]):
      with self.assertRaisesRegex(ValueError, 'cannot step a node'):
        evaluator.single_step(curry.getInterpreter(), expr)

  def test_survives_collections(self):
    '''The values are right after many collections in a child.'''
    proc = cytest.run_in_subprocess('''
import curry
from curry.backends.cxx import cyrtbindings as cyrt
curry.reload({'backend': 'cxx', 'defaultconverter': 'topython'})
M = curry.import_('CxxPartial')
cyrt.gc_set_threshold(1 << 12)
before = cyrt.gc_collections()
for _ in range(8):
  assert next(curry.eval(M.loop, 0, 3000)) == 3000
  assert next(curry.eval(M.manyApply)) == 666
  assert sorted(curry.eval(M.set2Many)) == [[631], [666]]
print(cyrt.gc_collections() - before)
''', TIMEOUT, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertGreaterEqual(int(proc.stdout), 4)

  @cytest.skipIfInterpreted('the test reads the generated code of CxxPartial')
  def test_generated_code(self):
    shlib = getHandle(self.M).icurry.metadata['cxx.shlib']
    text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')
    self.assertIn('// FORMAT: %d' % cxx_compiler.FORMAT_VERSION, text)
    # One shared node per function value, made at load.
    self.assertEqual(
        text.count('= partial_node(&CyI10CxxPartial3inc, 1);'), 1
      )
    self.assertIn('partial_node(&CyI10CxxPartial5plus3, 3);', text)
    self.assertIn('partial_node(&CyI7Prelude4Just, 1);', text)
    # A partial application with arguments is allocated with them inline;
    # none without arguments is allocated.
    self.assertIn('Node::create_partial(&CyI10CxxPartial5plus3, int_(1))', text)
    self.assertNotRegex(text, r'Node::create_partial\(&[A-Za-z0-9_]+\)')
    # The steps use the shared nodes.
    self.assertRegex(
        text, r'Node::create\(&CyI7Prelude5apply, CyP[0-9]+__[0-9]+, '
      )


@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
class TestRuntime(cytest.TestCase):
  '''
  The info-table family, create_partial, extend_partial, from_partial,
  rewrite_from_partial, partial_node, the copier, the equality, and the
  collector on the flat layout.  The checks are a C++ program,
  data/cxx/partial_test.cpp, compiled against the installed runtime with its
  assertions on.
  '''
  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'partial_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-partial-')
    try:
      exe = os.path.join(tmpdir, 'partial_test')
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
