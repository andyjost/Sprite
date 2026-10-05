'''
Tests for the plain pointer reads of the C++ backend.

A step builds a Variable for every argument it reads: the slot, the path from
the redex, and the set guards crossed.  An argument that the step only passes
on needs none of that, so the generator reads it as a plain Node * through
Node::successor_node or Variable::successor_node (backends/cxx/passthrough.py
states the rule; cyrt/graph/node.hxx and indexing.hxx hold the reads).  The
programs are in data/curry/CxxPassThrough.curry.
'''
import cytest # from ./lib; must be first
from curry import config, icurry
from curry.backends.cxx import passthrough
from curry.objects.handle import getHandle
import curry, os, re, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 120

class TestValues(cytest.TestCase):
  '''The programs give the same values on both backends.'''
  def values(self, *goal):
    return sorted(str(v) for v in curry.eval(*goal))

  def test_arguments(self):
    M = curry.import_('CxxPassThrough')
    self.assertEqual(self.values(M.rot3, 1, 2, 3), ['(3, 1, 2)'])
    self.assertEqual(self.values(M.second, 1, 2), ['2'])
    self.assertEqual(
        self.values(M.second, 1, curry.expr(M.addOne, 41)), ['42']
      )
    self.assertEqual(self.values(M.twiceOver, 5), ['[10, 6]'])
    self.assertEqual(self.values(M.orPass, 1, 2), ['1', '2'])
    self.assertEqual(self.values(M.aliasPass, 3), ['(3, 3)'])
    self.assertEqual(self.values(M.withFree, 7), ['7'])

  def test_pattern_variables(self):
    M = curry.import_('CxxPassThrough')
    self.assertEqual(self.values(M.firstOf, curry.expr(M.big, 4)), ['4'])
    self.assertEqual(self.values(M.plainHead), ['42'])

  def test_forward_node_in_slot(self):
    # seq evaluates b through one reference; the slot of keep then holds a
    # forward node to the larger result.
    M = curry.import_('CxxPassThrough')
    self.assertEqual(self.values(M.fwdInSlot, 1), ['(1, T3 1 1 1)'])

  def test_recursive_let(self):
    M = curry.import_('CxxPassThrough')
    self.assertEqual(self.values(M.cyc, 1), ['[1, 2, 1, 2, 1]'])

  def test_set_guards(self):
    # A choice in the argument of a set function is outside it: two values,
    # one set each.  A function that passes the argument on keeps its guard.
    M = curry.import_('CxxPassThrough')
    self.assertEqual(self.values(M.setPass), ['[2]', '[3]'])
    self.assertEqual(self.values(M.setPass2), ['[2]', '[3]'])
    self.assertEqual(self.values(M.setWrap), ['[Just 1]', '[Just 2]'])
    self.assertEqual(self.values(M.setHead), ['[2]', '[3]'])
    # A choice made inside the set function stays inside: one set.
    self.assertEqual(self.values(M.setInner), ['[6, 7]'])
    self.assertEqual(self.values(M.setCons), ['[2, 3]'])


class TestAnalysis(cytest.TestCase):
  '''plain_variables on hand-built ICurry.'''
  def function(self, arity, block):
    return icurry.IFunction('M.f', arity, body=icurry.IBody(block))

  def access(self, vid, base, *path):
    return icurry.IVarAssign(vid, icurry.IVarAccess(base, list(path)))

  def test_pass_through(self):
    # f x y = g y x: both arguments are plain.
    ifun = self.function(2, icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2)]
      , [self.access(1, 0, 0), self.access(2, 0, 1)]
      , icurry.IReturn(icurry.IFCall('M.g', [icurry.IVar(2), icurry.IVar(1)]))
      ))
    self.assertEqual(passthrough.plain_variables(ifun), {1, 2})

  def test_scrutinee(self):
    # f x = case x of C a -> g a x: x is a Variable, a is plain.
    branch = icurry.IConsBranch('M.C', 1, icurry.IBlock(
        [icurry.IVarDecl(2)], [self.access(2, 1, 0)]
      , icurry.IReturn(icurry.IFCall('M.g', [icurry.IVar(2), icurry.IVar(1)]))
      ))
    ifun = self.function(1, icurry.IBlock(
        [icurry.IVarDecl(1)], [self.access(1, 0, 0)]
      , icurry.ICaseCons(1, [branch])
      ))
    self.assertEqual(passthrough.plain_variables(ifun), {2})
    # The same with a case on a literal.
    lit = icurry.ILitBranch(icurry.IInt(0), icurry.IBlock(
        [], [], icurry.IReturn(icurry.IVar(1))
      ))
    ifun = self.function(1, icurry.IBlock(
        [icurry.IVarDecl(1)], [self.access(1, 0, 0)], icurry.ICaseLit(1, [lit])
      ))
    self.assertEqual(passthrough.plain_variables(ifun), set())

  def test_path_base_and_length(self):
    # A variable that is the base of a path, in an argument or in an
    # assignment, is a Variable; a path of two entries is a Variable too.
    ifun = self.function(1, icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2), icurry.IVarDecl(3)]
      , [self.access(1, 0, 0), self.access(2, 1, 1), self.access(3, 0, 0, 1)]
      , icurry.IReturn(icurry.IFCall('M.g', [
            icurry.IVar(2), icurry.IVar(3), icurry.IVarAccess(2, [0])
          ]))
      ))
    self.assertEqual(passthrough.plain_variables(ifun), set())

  def test_recursive_let(self):
    # let xs = x : ys; ys = 1 : xs: xs is patched (a Variable), ys is plain
    # although it is used before it is assigned.
    cons = lambda h, t: icurry.ICCall('Prelude.:', [h, t])
    ifun = self.function(1, icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2), icurry.IVarDecl(3)]
      , [
            self.access(1, 0, 0)
          , icurry.IVarAssign(2, cons(icurry.IVar(1), icurry.IVar(3)))
          , icurry.IVarAssign(
                3, cons(icurry.ILit(icurry.IInt(1)), icurry.IVar(2))
              )
          , icurry.INodeAssign(2, [1], icurry.IVar(3))
          ]
      , icurry.IReturn(icurry.IFCall('M.g', [icurry.IVar(2)]))
      ))
    self.assertEqual(passthrough.plain_variables(ifun), {1, 3})

  def test_aliases(self):
    # y = x: both plain, or both Variables when one of them is scrutinized.
    def make(stmt):
      return self.function(1, icurry.IBlock(
          [icurry.IVarDecl(1), icurry.IVarDecl(2)]
        , [self.access(1, 0, 0), icurry.IVarAssign(2, icurry.IVar(1))]
        , stmt
        ))
    ifun = make(icurry.IReturn(icurry.IFCall('M.g', [icurry.IVar(2)])))
    self.assertEqual(passthrough.plain_variables(ifun), {1, 2})
    branch = icurry.IConsBranch('M.C', 0, icurry.IBlock(
        [], [], icurry.IReturn(icurry.IVar(1))
      ))
    ifun = make(icurry.ICaseCons(2, [branch]))
    self.assertEqual(passthrough.plain_variables(ifun), set())

  def test_other_declarations(self):
    # A free variable is a pointer already and not reported; a variable
    # assigned twice, or never, is left alone; a partial application and a
    # choice take plain arguments.
    ifun = self.function(1, icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IFreeDecl(2), icurry.IVarDecl(3)
          , icurry.IVarDecl(4)]
      , [
            self.access(1, 0, 0), self.access(3, 0, 0), self.access(3, 0, 0)
          ]
      , icurry.IReturn(icurry.IOr(
            icurry.IFPCall('M.g', 1, [icurry.IVar(1), icurry.IVar(2)])
          , icurry.IVar(4)
          ))
      ))
    self.assertEqual(passthrough.plain_variables(ifun), {1})

  def test_no_body(self):
    ifun = icurry.IFunction('M.f', 1, body=icurry.IExternal('M.f'))
    self.assertEqual(passthrough.plain_variables(ifun), set())


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
class TestGeneratedCode(cytest.TestCase):
  '''The generator applies the rule to each shape of use.'''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.import_('CxxPassThrough')
    shlib = getHandle(cls.M).icurry.metadata['cxx.shlib']
    cls.text = cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')

  def step(self, name):
    '''The text of the step function of ``name``.'''
    match = re.search(
        r'/\*{6} CxxPassThrough\.%s \*{6}/\n(.*?)\n}\n' % re.escape(name)
      , self.text, re.S
      )
    self.assertIsNotNone(match, name)
    return match.group(1)

  def test_arguments_are_plain(self):
    text = self.step('rot3')
    self.assertNotIn('Variable', text)
    for i in 1, 2, 3:
      self.assertIn('Node * _%d = nullptr;' % i, text)
      self.assertIn('_%d = _0->successor_node(%d);' % (i, i - 1), text)
    self.assertIn(
        'return _0->rewrite(&CyI7Prelude8_Y_m_m_y, _3, _1, _2);', text
      )
    text = self.step('second')
    self.assertNotIn('Variable', text)
    self.assertIn('return _0->forward_or_copy(_2);', text)
    text = self.step('twiceOver')
    self.assertNotIn('Variable', text)
    self.assertIn('Node::create_partial(&CyI14CxxPassThrough4plus, _1)', text)

  def test_scrutinee_is_a_variable(self):
    text = self.step('firstOf')
    self.assertIn('Variable _1;', text)
    self.assertIn('_1 = _0[0];', text)
    self.assertIn('rts->hnf(C, &_1, ', text)
    # The pattern variable is read from the Variable.
    self.assertIn('Node * _2 = nullptr;', text)
    self.assertIn('_2 = _1.successor_node(0);', text)
    self.assertIn('return _0->forward_or_copy(_2);', text)

  def test_recursive_let(self):
    # The patched cell is a Variable; the cell that is referred to before it
    # exists is a plain pointer, null until assigned.
    text = self.step('cyc')
    self.assertIn('Variable _2;', text)
    self.assertIn('Node * _3 = nullptr;', text)
    self.assertRegex(
        text, r'Node \* tmp_2 = Node::create\(&CyI7Prelude2_C, _1, _3\);'
      )
    self.assertIn('_2.target = tmp_2;', text)
    self.assertIn('_2.set_successor(1, _3);', text)

  def test_free_variable(self):
    text = self.step('withFree')
    self.assertNotIn('Variable', text)
    self.assertIn('auto _2 = rts->freshvar();', text)
    self.assertIn('_1 = _0->successor_node(0);', text)


@unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
@unittest.skipIf(shutil.which('objdump') is None, 'objdump is not installed')
class TestStepFunctions(cytest.TestCase):
  '''
  The steps of tak and fibgen build no Variable: their code refers to none
  of the functions a Variable brings in (the release of its inline storage,
  the guarded rvalue), and the generated text declares none.
  '''
  BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')
  # The release of the inline storage, the constructor and destructor of
  # Variable, and the slow path of rvalue.
  VARIABLE = re.compile(r'smallvec_free|8Variable[CD][12]E|guarded_rvalue')

  def module(self, name):
    curry.import_(name, currypath=[self.BENCHMARKS] + curry.path)
    base = os.path.join(
        self.BENCHMARKS, '.curry', config.intermediate_subdir(), name
      )
    self.assertTrue(os.path.exists(base + '.so'), base)
    return base

  def references(self, sofile):
    '''Maps each step function of a compiled module to the symbols it names.'''
    proc = subprocess.run(
        ['objdump', '-d', '--no-show-raw-insn', sofile]
      , capture_output=True, text=True, check=True
      )
    refs = {}
    current = None
    for line in proc.stdout.splitlines():
      match = re.match(r'^[0-9a-f]+ <([^>]+)>:$', line)
      if match:
        name = match.group(1)
        current = name if name.startswith('CyF') else None
        continue
      if current is not None:
        for match in re.finditer(r'<([^>@+]+)', line):
          refs.setdefault(current, set()).add(match.group(1))
    return refs

  def test_tak_and_fibgen_make_no_variable(self):
    for name, step in ('Tak1', 'CyF4Tak13tak'), ('Fib', 'CyF3Fib6fibgen'):
      base = self.module(name)
      refs = self.references(base + '.so')
      self.assertIn(step, refs)
      bad = sorted(r for r in refs[step] if self.VARIABLE.search(r))
      self.assertEqual(bad, [], '%s refers to %s' % (step, bad))
      text = cytest.readfile(base + '.cpp')
      match = re.search(
          r'\ntag_type %s\(RuntimeState[^\n]*\n\{\n(.*?)\n\}\n' % step
        , text, re.S
        )
      self.assertIsNotNone(match, step)
      self.assertNotIn('Variable', match.group(1))
      self.assertIn('successor_node', match.group(1))


@unittest.skipIf(config.cxx_tool() is None, 'no C++ compiler is installed')
class TestSuccessorNode(cytest.TestCase):
  '''
  Node::successor_node and Variable::successor_node on hand-built nodes.  The
  checks are a C++ program, data/cxx/successor_node_test.cpp, compiled against
  the installed runtime with its assertions on.
  '''
  def test_program(self):
    source = os.path.join(HERE, 'data', 'cxx', 'successor_node_test.cpp')
    libdir = config.installed_path('lib')
    tmpdir = tempfile.mkdtemp(prefix='sprite-successor-')
    try:
      exe = os.path.join(tmpdir, 'successor_node_test')
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
