'''
Tests for the emission of a let-lifted default branch on the C++ backend
(issue #59).

A case whose default branch body is a bare literal or a nullary constructor,
such as ``_ -> False``, is completed by the front end: the body goes into a
let variable, and every branch the default stands for returns the variable.
The generator assigns the variable from the spelling of the node: false_()
for a pinned constructor, int_(2) for a literal of the tables, a literal node
or a partial node of the module, or Node::create(...).  A variable that the
step only passes on is a plain pointer and takes any spelling.  A Variable (a
scrutinee, the base of a path or of a node assignment, or an alias of one)
has no assignment from a Node *, so the generator stores the node in a cell
of the frame and points the Variable at it, whatever the spelling
(vEmit_compileS_IVarAssign in backends/cxx/compiler.py).

The programs of the front end are in data/curry/CxxEmit.curry.  The shapes
that bind a Variable are hand-built ICurry: the front end passes a scrutinee
to a lifted function as an argument and never binds one to a literal.
'''
import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.backends.cxx import passthrough
from curry.icurry import json as icurry_json
from curry.objects.handle import getHandle
from curry.toolchain import plans
import curry, os, re, tempfile, unittest, zlib

ONLY_CXX = unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )
COMPILED = unittest.skipIf(
    curry.flags['interpret'] != 'off', 'the interpreter writes no C++'
  )

HAND = 'CxxEmitHand'

def expected_failure_on_py(test):
  '''
  The Python backend scrutinizes a variable through Variable.hnf
  (vEmit_compileS_ICaseCons in backends/py/compiler.py).  A variable
  assigned a new node is a raw Node there, which has no hnf, so the ICurry
  of CxxEmitHand raises AttributeError on that backend.  The front end never
  writes the shape.
  '''
  if curry.flags['backend'] == 'py':
    return unittest.expectedFailure(test)
  return test

def generated_text(module):
  '''The C++ text of a compiled module.'''
  shlib = getHandle(module).icurry.metadata['cxx.shlib']
  return cytest.readfile(shlib.sofilename()[:-len('.so')] + '.cpp')

def step_text(text, fullname):
  '''The body of the step function of ``fullname`` in ``text``.'''
  match = re.search(
      r'/\*{6} %s \*{6}/\n(.*?)\n}\n' % re.escape(fullname), text, re.S
    )
  if match is None:
    raise AssertionError('no step function for %s' % fullname)
  return match.group(1)

def hand_module():
  '''
  The module CxxEmitHand.  Each function assigns a variable from a node of
  one spelling and then scrutinizes it, so the generator declares a Variable
  for the variable.  The front end never writes this shape.
  '''
  I = icurry
  def ret(expr):
    return I.IBlock([], [], I.IReturn(expr))
  def int_(value):
    return I.ILit(I.IInt(value))
  def cons(name, arity, expr):
    return I.IConsBranch(name, arity, ret(expr))
  def lit(literal, expr):
    return I.ILitBranch(literal, ret(expr))
  def scrutinize(name, rhs, case):
    '''A nullary function: variable 1 takes ``rhs``; ``case`` reads it.'''
    block = I.IBlock([I.IVarDecl(1)], [I.IVarAssign(1, rhs)], case)
    return I.IFunction('%s.%s' % (HAND, name), 0, body=I.IBody(block))
  color = I.IDataType(
      HAND + '.Color'
    , [
          I.IConstructor('%s.%s' % (HAND, name), 0)
              for name in ('Red', 'Green', 'Blue')
        ]
    )
  functions = [
      # boolVar x = let v = False in case v of False -> x; True -> 0
      I.IFunction(HAND + '.boolVar', 1, body=I.IBody(I.IBlock(
          [I.IVarDecl(1), I.IVarDecl(2)]
        , [
              I.IVarAssign(1, I.IVarAccess(0, [0]))
            , I.IVarAssign(2, I.ICCall('Prelude.False', []))
            ]
        , I.ICaseCons(2, [
              cons('Prelude.False', 0, I.IVar(1))
            , cons('Prelude.True', 0, int_(0))
            ])
        )))
    , scrutinize('intVar', int_(2), I.ICaseLit(1, [
          lit(I.IInt(1), int_(10)), lit(I.IInt(2), int_(20))
        ]))
    , scrutinize('charVar', I.ILit(I.IChar('z')), I.ICaseLit(1, [
          lit(I.IChar('a'), int_(0)), lit(I.IChar('z'), int_(26))
        ]))
    , scrutinize('bigVar', int_(100000), I.ICaseLit(1, [
          lit(I.IInt(0), int_(0)), lit(I.IInt(100000), int_(1))
        ]))
    , scrutinize('floatVar', I.ILit(I.IFloat(2.5)), I.ICaseLit(1, [
          lit(I.IFloat(0.0), int_(0)), lit(I.IFloat(2.5), int_(1))
        ]))
    , scrutinize('nilVar', I.ICCall('Prelude.[]', []), I.ICaseCons(1, [
          cons('Prelude.[]', 0, int_(0)), cons('Prelude.:', 2, int_(1))
        ]))
    , scrutinize('unitVar', I.ICCall('Prelude.()', []), I.ICaseCons(1, [
          cons('Prelude.()', 0, int_(1))
        ]))
    , scrutinize('ctorVar', I.ICCall(HAND + '.Green', []), I.ICaseCons(1, [
          cons(HAND + '.Red', 0, int_(0)), cons(HAND + '.Green', 0, int_(1))
        , cons(HAND + '.Blue', 0, int_(2))
        ]))
    ]
  return I.IModule(HAND, ['Prelude'], [color], functions)

# The spelling of the node each function of CxxEmitHand assigns, and the
# variable that takes it.
HAND_SPELLINGS = {
    'boolVar' : ('_2', r'false_\(\)')
  , 'intVar'  : ('_1', r'int_\(2\)')
  , 'charVar' : ('_1', r"char_\(U'z'\)")
  , 'bigVar'  : ('_1', r'CyL\w+')
  , 'floatVar': ('_1', r'CyL\w+')
  , 'nilVar'  : ('_1', r'nil\(\)')
  , 'unitVar' : ('_1', r'unit\(\)')
  , 'ctorVar' : ('_1', r'Node::create\(&\w+Green\)')
  }

# The values of the functions of CxxEmitHand.
HAND_VALUES = {
    'intVar': 20, 'charVar': 26, 'bigVar': 1, 'floatVar': 1, 'nilVar': 0
  , 'unitVar': 1, 'ctorVar': 1
  }


class TestValues(cytest.TestCase):
  '''The programs give the same values on both backends.'''
  def values(self, *goal):
    return list(curry.eval(*goal, converter='topython'))

  def shown(self, *goal):
    return [str(v) for v in curry.eval(*goal)]

  def test_defaults(self):
    M = curry.import_('CxxEmit')
    ptr = curry.expr(M.Ptr, M.Int)
    self.assertEqual(self.values(M.isPtr, ptr), [True])
    self.assertEqual(self.values(M.isPtr, M.Char), [False])
    self.assertEqual(self.values(M.rank, M.Char), [1])
    self.assertEqual(self.values(M.rank, ptr), [2])
    self.assertEqual(self.values(M.code, M.Int), ['i'])
    self.assertEqual(self.values(M.code, ptr), ['z'])
    self.assertEqual(self.shown(M.paint, M.Int), ['Red'])
    self.assertEqual(self.shown(M.paint, ptr), ['Green'])
    self.assertEqual(self.values(M.nested, ptr, M.Int), [10])
    self.assertEqual(self.values(M.nested, ptr, M.Char), [11])
    self.assertEqual(self.values(M.nested, M.Char, M.Char), [12])
    self.assertEqual(self.values(M.big, M.Int), [1])
    self.assertEqual(self.values(M.big, ptr), [100000])
    self.assertEqual(self.values(M.scale, M.Int), [1.5])
    self.assertEqual(self.values(M.scale, ptr), [2.5])
    self.assertEqual(self.values(M.elems, M.Int), [[1]])
    self.assertEqual(self.values(M.elems, ptr), [[]])
    self.assertEqual(self.values(M.stepped, M.Int, 5), [6])
    self.assertEqual(self.values(M.stepped, ptr, 5), [4])

  def test_lifted_variable_is_plain(self):
    '''
    The front end passes the lifted variable to the lifted case function,
    so it is a plain pointer in both functions (passthrough.py).  The ICurry
    is read as the front end wrote it: an import drops the bodies.
    '''
    plan = plans.makeplan(
        None, plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON
      )
    functions = toolchain.loadcurry(plan, 'CxxEmit', curry.path).functions
    self.assertEqual(passthrough.plain_variables(functions['isPtr']), {1, 2})
    self.assertEqual(
        passthrough.plain_variables(functions['isPtr_CASE0']), {2}
      )


class TestHandBuilt(cytest.TestCase):
  '''
  A Variable assigned a node of each spelling, then scrutinized.  The module
  is written as ICurry-JSON and imported by name, so it is compiled like a
  module of the front end, and no front end runs.
  '''
  @classmethod
  def setUpClass(cls):
    cls.tmpdir = tempfile.TemporaryDirectory()
    subdir = os.path.join(
        cls.tmpdir.name, '.curry', config.intermediate_subdir()
      )
    os.makedirs(subdir)
    text = icurry_json.dumps(hand_module())
    with open(os.path.join(subdir, HAND + '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(text.encode('utf-8')))

  @classmethod
  def tearDownClass(cls):
    cls.tmpdir.cleanup()

  def module(self):
    return curry.import_(HAND, currypath=[self.tmpdir.name] + curry.path)

  @expected_failure_on_py
  def test_values(self):
    M = self.module()
    # The module is built by hand and has no FlatCurry interface, so the
    # typed builder cannot type the call: build it untyped.
    self.assertEqual(
        list(curry.eval(curry.raw_expr(M.boolVar, 7), converter='topython'))
      , [7]
      )
    for name, value in HAND_VALUES.items():
      goal = getattr(M, name)
      self.assertEqual(
          list(curry.eval(goal, converter='topython')), [value], name
        )

  @ONLY_CXX
  @COMPILED
  def test_variable_targets_a_cell(self):
    text = generated_text(self.module())
    for name, (var, spelling) in HAND_SPELLINGS.items():
      step = step_text(text, '%s.%s' % (HAND, name))
      self.assertIn('Variable %s;' % var, step)
      self.assertRegex(step, r'Node \* tmp%s = %s;' % (var, spelling))
      self.assertIn('%s.target = tmp%s;' % (var, var), step)
      self.assertIn('rts->hnf(C, &%s, ' % var, step)
      self.assertNotRegex(step, r'\n  %s = ' % var)


@ONLY_CXX
@COMPILED
class TestGeneratedCode(cytest.TestCase):
  '''The lifted variable of the front end is a plain pointer, whatever the
  spelling of its node.'''
  def test_plain_defaults(self):
    text = generated_text(curry.import_('CxxEmit'))
    plain = [
        ('isPtr', '_2', r'false_\(\)')
      , ('rank', '_2', r'int_\(2\)')
      , ('code', '_2', r"char_\(U'z'\)")
      , ('paint', '_2', r'Node::create\(&\w+Green\)')
      , ('nested', '_3', r'int_\(12\)')
      , ('nested_LET1', '_5', r'int_\(11\)')
      , ('big', '_2', r'CyL\w+')
      , ('scale', '_2', r'CyL\w+')
      , ('elems', '_2', r'nil\(\)')
      , ('step', '_2', r'CyP\w+')
      ]
    for name, var, spelling in plain:
      step = step_text(text, 'CxxEmit.' + name)
      self.assertNotIn('Variable', step)
      self.assertIn('Node * %s = nullptr;' % var, step)
      self.assertRegex(step, r'\n  %s = %s;' % (var, spelling))
    # The lifted case function returns the variable by reference.
    step = step_text(text, 'CxxEmit.isPtr_CASE0')
    self.assertIn('Node * _2 = nullptr;', step)
    self.assertIn('_2 = _0->successor_node(1);', step)
    self.assertIn('return _0->forward_or_copy(_2);', step)
