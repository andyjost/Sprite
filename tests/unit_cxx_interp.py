'''
Tests for the ICurry interpreter of the C++ runtime.

The runtime interprets a function from a bytecode (cyrt/icurry.hpp) that the
emitter of the C++ backend writes from the ICurry of the function
(backends/cxx/bytecode.py).  The interpreter flag ``interpret`` selects it:
'new' for the modules without a compiled object, 'all' for every module.  The
programs are in data/curry/CxxInterp.curry; their values under the
interpreter are compared with the values of the compiled code.
'''
import cytest # from ./lib; must be first
from curry import common, config, icurry, inspect, toolchain
from curry.backends.cxx import bytecode, materialize, tiered
from curry.backends.cxx import cyrtbindings as cyrt
from curry.backends.cxx import toolchain as cxx_toolchain
from curry.backends.generic.eval import evaluator
from curry.exceptions import CompileError, EvaluationError
from curry.objects.handle import getHandle
from curry.toolchain import _makecurry, _productcache, plans
from unittest import mock
import contextlib, curry, gc, importlib, itertools, os, shutil, subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS = os.path.join(HERE, 'data', 'curry', 'benchmarks')

# The cap on the address space of a child, in bytes, and the time it may
# take.
ADDRESS_SPACE = 2 << 30
TIMEOUT = 120

ONLY_CXX = unittest.skipIf(
    curry.flags['backend'] != 'cxx', 'these tests drive the C++ backend'
  )

def switch(mode, name='CxxInterp'):
  '''
  Reloads the interpreter with the flag ``interpret`` set to ``mode`` and
  imports the test module.  The runtime keeps one module object per name
  while anything holds it, so the caller must drop its module objects
  first: the garbage is collected before the reload.
  '''
  gc.collect()
  curry.reload({'backend': 'cxx', 'interpret': mode})
  return curry.import_(name)


class Resolver(object):
  '''A resolver of the emitter that answers with names.'''
  TAGS = {
      'Prelude.False': 0, 'Prelude.True': 1, 'Prelude.:': 0, 'Prelude.[]': 1
    , 'M.A': 0, 'M.B': 1, 'M.C': 2
    }
  def symbol(self, name):
    return 'sym:' + name
  def tag(self, name):
    return self.TAGS[name]
  def datatype(self, name):
    return 'type:' + name


def function(arity, block, name='M.f'):
  return icurry.IFunction(name, arity, body=icurry.IBody(block))

def access(vid, base, *path):
  return icurry.IVarAssign(vid, icurry.IVarAccess(base, list(path)))

def lit(value):
  if isinstance(value, bool):
    raise TypeError
  if isinstance(value, int):
    return icurry.ILit(icurry.IInt(value))
  if isinstance(value, float):
    return icurry.ILit(icurry.IFloat(value))
  return icurry.ILit(icurry.IChar(value))

def names(code):
  '''The opcode names of the disassembly of ``code``.'''
  return [line.split()[1] for line in code.disassemble()]


class TestEmitter(cytest.TestCase):
  '''The emitter on hand-built ICurry.'''

  def test_opcodes_agree_with_runtime(self):
    self.assertEqual(list(cyrt.icurry_opcodes()), list(bytecode.OPCODES))
    self.assertEqual(cyrt.ROOT_VAR, bytecode.ROOT_VAR)
    self.assertEqual(cyrt.NO_BRANCH, bytecode.NO_BRANCH)
    self.assertEqual(
        sorted(bytecode.OP.values()), list(range(len(bytecode.OPCODES)))
      )

  def test_pass_through(self):
    # rot3 x y z = Pair3 z x y: three plain loads, a result written into the
    # redex.
    ifun = function(3, icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2), icurry.IVarDecl(3)]
      , [access(1, 0, 0), access(2, 0, 1), access(3, 0, 2)]
      , icurry.IReturn(icurry.ICCall(
            'M.Pair3', [icurry.IVar(3), icurry.IVar(1), icurry.IVar(2)]
          ))
      ))
    code = bytecode.compile_function(ifun, Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 LOAD_ROOT_SUCC r0 0'
      , '   3 LOAD_ROOT_SUCC r1 1'
      , '   6 LOAD_ROOT_SUCC r2 2'
      , '   9 PUSH_REG r2'
      , '  11 PUSH_REG r0'
      , '  13 PUSH_REG r1'
      , "  15 RET_NODE k0<'sym:M.Pair3'> 3"
      ])
    self.assertEqual((code.nregs, code.nvars, code.nstack), (3, 0, 3))
    self.assertEqual(code.consts, ['sym:M.Pair3'])

  def test_case(self):
    # f xs = case xs of [] -> True; (x:_) -> x
    block = icurry.IBlock(
        [icurry.IVarDecl(1)], [access(1, 0, 0)]
      , icurry.ICaseCons(1, [
            icurry.IConsBranch('Prelude.[]', 0, icurry.IBlock(
                [], [], icurry.IReturn(icurry.ICCall('Prelude.True', []))
              ))
          , icurry.IConsBranch('Prelude.:', 2, icurry.IBlock(
                [icurry.IVarDecl(2)], [access(2, 1, 0)]
              , icurry.IReturn(icurry.IVar(2))
              ))
          ])
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 BIND_ROOT v0 [0]'
      , "   4 CASE_CONS v0 k0<'type:Prelude.[]'> [13, 10]"
      , "  10 RET_NODE k1<'sym:Prelude.True'> 0"
      , '  13 LOAD_VAR_SUCC r0 v0 0'
      , '  17 PUSH_REG r0'
      , '  19 RET_REF'
      ])
    self.assertEqual((code.nregs, code.nvars, code.nstack), (1, 1, 1))

  def test_case_without_every_branch(self):
    # A type of three constructors with a branch for the last one only.
    block = icurry.IBlock(
        [icurry.IVarDecl(1)], [access(1, 0, 0)]
      , icurry.ICaseCons(1, [
            icurry.IConsBranch(
                'M.C', 0, icurry.IBlock([], [], icurry.IExempt())
              )
          ])
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 BIND_ROOT v0 [0]'
      , "   4 CASE_CONS v0 k0<'type:M.C'> [-, -, 11]"
      , '  11 EXEMPT'
      ])
    self.assertEqual(code.code[8:10], [bytecode.NO_BRANCH] * 2)

  def test_case_lit(self):
    block = icurry.IBlock(
        [icurry.IVarDecl(1)], [access(1, 0, 0)]
      , icurry.ICaseLit(1, [
            icurry.ILitBranch(icurry.IInt(-1), icurry.IBlock(
                [], [], icurry.IReturn(lit(10))
              ))
          , icurry.ILitBranch(icurry.IInt(5000), icurry.IBlock(
                [], [], icurry.IReturn(lit(20))
              ))
          ])
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 BIND_ROOT v0 [0]'
      , "   4 CASE_LIT v0 k0<('V', 'i', (-1, 5000))> i [-1:15, 5000:18]"
      , "  15 PUSH_CONST k1<('I', 10)>"
      , '  17 RET_REF'
      , "  18 PUSH_CONST k2<('I', 20)>"
      , '  20 RET_REF'
      ])
    # The value -1 as two words of its 64-bit two's complement.
    self.assertEqual(code.code[9:11], [0xffffffff, 0xffffffff])
    for kind, values in ('c', ['a', 'z']), ('f', [0.5, -0.0]):
      branches = [
          icurry.ILitBranch(
              icurry.IChar(v) if kind == 'c' else icurry.IFloat(v)
            , icurry.IBlock([], [], icurry.IReturn(lit(1)))
            )
            for v in values
        ]
      block = icurry.IBlock(
          [icurry.IVarDecl(1)], [access(1, 0, 0)], icurry.ICaseLit(1, branches)
        )
      code = bytecode.compile_function(function(1, block), Resolver())
      self.assertEqual(code.consts[0], ('V', kind, tuple(values)))
      self.assertIn(' %s [' % kind, code.disassemble()[1])

  def test_literals_and_strings(self):
    # f x = g 1 100000 'a' 2.5 "hi" x: the literals are constants, one per
    # value; the string is a node of the step.
    block = icurry.IBlock(
        [icurry.IVarDecl(1)], [access(1, 0, 0)]
      , icurry.IReturn(icurry.IFCall('M.g', [
            lit(1), lit(100000), lit('a'), lit(2.5), icurry.IString('hi')
          , icurry.IVar(1), lit(1)
          ]))
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(names(code), [
        'LOAD_ROOT_SUCC', 'PUSH_CONST', 'PUSH_CONST', 'PUSH_CONST'
      , 'PUSH_CONST', 'MAKE_STRING', 'PUSH_REG', 'PUSH_CONST', 'RET_NODE'
      ])
    self.assertEqual(code.consts, [
        ('I', 1), ('I', 100000), ('C', ord('a')), ('F', 2.5), ('S', 'hi')
      , 'sym:M.g'
      ])
    self.assertEqual(code.nstack, 7)
    # A string as the result is written into the redex.
    block = icurry.IBlock([], [], icurry.IReturn(icurry.IString('text')))
    code = bytecode.compile_function(function(0, block), Resolver())
    self.assertEqual(
        code.disassemble(), ["   0 RET_STRING k0<('S', 'text')>"]
      )
    # A literal as the result is a reference result.
    block = icurry.IBlock([], [], icurry.IReturn(lit(7)))
    code = bytecode.compile_function(function(0, block), Resolver())
    self.assertEqual(names(code), ['PUSH_CONST', 'RET_REF'])
    # -0.0 and 0.0 are two constants.
    block = icurry.IBlock(
        [], [], icurry.IReturn(icurry.IFCall('M.g', [lit(0.0), lit(-0.0)]))
      )
    code = bytecode.compile_function(function(0, block), Resolver())
    self.assertEqual(len(code.consts), 3)

  def test_partial_and_choice(self):
    # f x = (g x ? h) where h is a function value: a partial application
    # with an argument, one without, and a choice.
    block = icurry.IBlock(
        [icurry.IVarDecl(1)], [access(1, 0, 0)]
      , icurry.IReturn(icurry.IOr(
            icurry.IFPCall('M.g', 1, [icurry.IVar(1)])
          , icurry.IFPCall('M.h', 2, [])
          ))
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 LOAD_ROOT_SUCC r0 0'
      , '   3 PUSH_REG r0'
      , "   5 MAKE_PARTIAL k0<'sym:M.g'> 1"
      , "   8 PUSH_CONST k1<('P', 'sym:M.h', 2)>"
      , "  10 RET_NODE k2<'sym:Prelude.?'> 2"
      ])
    # A partial application as the result is a reference result; a choice
    # inside an argument is a node.
    block = icurry.IBlock(
        [], [], icurry.IReturn(icurry.IFPCall('M.g', 1, [
            icurry.IOr(lit(1), lit(2))
          ]))
      )
    code = bytecode.compile_function(function(0, block), Resolver())
    self.assertEqual(names(code), [
        'PUSH_CONST', 'PUSH_CONST', 'MAKE', 'MAKE_PARTIAL', 'RET_REF'
      ])

  def test_free_and_recursive_let(self):
    # xs = n : ys; ys = 1 : xs; with a free variable beside them.  The cell
    # referred to before it exists reads as null, then is patched.
    block = icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2), icurry.IVarDecl(3)
          , icurry.IFreeDecl(4)]
      , [
            access(1, 0, 0)
          , icurry.IVarAssign(2, icurry.ICCall(
                'Prelude.:', [icurry.IVar(1), icurry.IVar(3)]
              ))
          , icurry.IVarAssign(3, icurry.ICCall(
                'Prelude.:', [lit(1), icurry.IVar(2)]
              ))
          , icurry.INodeAssign(2, [1], icurry.IVar(3))
          ]
      , icurry.IReturn(icurry.IFCall('M.g', [icurry.IVar(2), icurry.IVar(4)]))
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 FREE_REG r2'
      , '   2 LOAD_ROOT_SUCC r0 0'
      , '   5 PUSH_REG r0'
      , '   7 PUSH_REG r1'
      , "   9 MAKE k0<'sym:Prelude.:'> 2"
      , '  12 STORE_VAR v0'
      , "  14 PUSH_CONST k1<('I', 1)>"
      , '  16 PUSH_VAR v0'
      , "  18 MAKE k0<'sym:Prelude.:'> 2"
      , '  21 STORE_REG r1'
      , '  23 PUSH_REG r1'
      , '  25 SET_SUCC v0 [1]'
      , '  29 PUSH_VAR v0'
      , '  31 PUSH_REG r2'
      , "  33 RET_NODE k2<'sym:M.g'> 2"
      ])
    self.assertEqual((code.nregs, code.nvars, code.nstack), (3, 1, 2))

  def test_aliases_and_paths(self):
    # y = x with x scrutinized: both Variables; a path of two entries; an
    # access inside an argument.
    block = icurry.IBlock(
        [icurry.IVarDecl(1), icurry.IVarDecl(2), icurry.IVarDecl(3)]
      , [
            access(1, 0, 0), icurry.IVarAssign(2, icurry.IVar(1))
          , access(3, 1, 0, 1)
          ]
      , icurry.ICaseCons(2, [
            icurry.IConsBranch('M.A', 0, icurry.IBlock(
                [], [], icurry.IReturn(icurry.IFCall('M.g', [
                    icurry.IVar(3), icurry.IVarAccess(1, [1])
                  , icurry.IVarAccess(0, [0, 0])
                  ]))
              ))
          ])
      )
    code = bytecode.compile_function(function(1, block), Resolver())
    self.assertEqual(code.disassemble(), [
        '   0 BIND_ROOT v0 [0]'
      , '   4 COPY_VAR v1 v0'
      , '   7 BIND_VAR v2 v0 [0, 1]'
      , "  13 CASE_CONS v1 k0<'type:M.A'> [18]"
      , '  18 PUSH_VAR v2'
      , '  20 PUSH_SUCC v0 1'
      , '  23 PUSH_PATH root [0, 0]'
      , "  28 RET_NODE k1<'sym:M.g'> 3"
      ])
    self.assertEqual((code.nregs, code.nvars), (0, 3))

  def test_external_and_builtin(self):
    ifun = icurry.IFunction('M.f', 1, body=icurry.IExternal('M.f'))
    code = bytecode.compile_function(ifun, Resolver())
    self.assertEqual(names(code), ['MAKE_STRING', 'RET_NODE'])
    self.assertEqual(code.consts[1], 'sym:Prelude.prim_error')
    self.assertIn('not defined', code.consts[0][1])
    ifun = icurry.IFunction('M.f', 1, body=icurry.IBuiltin())
    self.assertRaisesRegex(
        CompileError, 'built-in', bytecode.compile_function, ifun, Resolver()
      )

  def test_errors(self):
    # An unboxed literal, a path from a plain variable, a case on the redex.
    block = icurry.IBlock(
        [], [], icurry.IReturn(icurry.IFCall('M.g', ['text']))
      )
    self.assertRaisesRegex(
        CompileError, 'unboxed', bytecode.compile_function
      , function(0, block), Resolver()
      )
    block = icurry.IBlock(
        [], [], icurry.ICaseCons(0, [
            icurry.IConsBranch(
                'M.A', 0, icurry.IBlock([], [], icurry.IExempt())
              )
          ])
      )
    self.assertRaisesRegex(
        CompileError, 'redex', bytecode.compile_function
      , function(0, block), Resolver()
      )

  def test_disassemble_consts(self):
    code = [bytecode.OP['PUSH_CONST'], 0, bytecode.OP['RET_REF']]
    self.assertEqual(
        list(bytecode.disassemble(code)), ['   0 PUSH_CONST k0', '   2 RET_REF']
      )


@ONLY_CXX
class TestValues(cytest.TestCase):
  '''
  The programs give the same values under the interpreter as the compiled
  code gives.  The values are taken with the flag off first, then the
  interpreter reloads with the flag on and the values are taken again.
  '''
  GOALS = [
      ('fact', 10), ('sumList', [1, 2, 3, 4]), ('area', ('Circle', 2))
    , ('area', ('Rect', 3, 4)), ('area', ('Dot',)), ('classify', ('Circle', 0))
    , ('classify', ('Rect', 2, 2)), ('classify', ('Rect', 2, 3))
    , ('rot3', 1, 2, 3), ('firstOf', ('Pair3', 7, 8, 9)), ('second', 1, 2)
    , ('keepShape', 1, ('Rect', 1, 2)), ('mapPlus', 10, [1, 2, 3])
    , ('higher', 5), ('compose3', 10), ('bigInt',), ('chars',), ('floats', 2.0)
    , ('greeting',), ('digitName', 1), ('digitName', 7), ('negName', -1)
    , ('negName', 0), ('negName', 5), ('vowel', 'e'), ('vowel', 'x')
    , ('halfOrOne', 0.5), ('halfOrOne', 1.0), ('halfOrOne', 3.0)
    , ('withFree', 41), ('lastOf', [1, 2, 3]), ('splitFree', [1, 2])
    , ('perm', [1, 2, 3]), ('coin',), ('perms', [3, 1, 2]), ('setPass',)
    , ('noDup', [1, 2, 3]), ('noDup', [1, 2, 1]), ('cyc', 1), ('aliasPass', 5)
    , ('several', 3), ('firstOrZero', []), ('firstOrZero', [9, 8])
    , ('ioAdd', 20), ('shout', 'abc'), ('showAll', [1, 2]), ('countDown', 1000)
    , ('walk', [1, 2, 3])
    ]

  def expression(self, M, goal):
    name, args = goal[0], goal[1:]
    def convert(arg):
      if isinstance(arg, tuple):
        return curry.expr(getattr(M, arg[0]), *[convert(a) for a in arg[1:]])
      return arg
    return curry.expr(getattr(M, name), *[convert(a) for a in args])

  def values(self, M):
    results = {}
    for i, goal in enumerate(self.GOALS):
      expr = self.expression(M, goal)
      results[i] = sorted(str(v) for v in curry.eval(expr, converter=None))
    return results

  def value(self, results, name, *args):
    return results[self.GOALS.index((name,) + args)]

  @cytest.hardreset
  def test_values(self):
    M = curry.import_('CxxInterp')
    expected = self.values(M)
    self.assertEqual(self.value(expected, 'fact', 10), ['3628800'])
    self.assertEqual(self.value(expected, 'perm', [1, 2, 3]), sorted([
        '[1, 2, 3]', '[2, 1, 3]', '[2, 3, 1]', '[1, 3, 2]', '[3, 1, 2]'
      , '[3, 2, 1]'
      ]))
    self.assertEqual(self.value(expected, 'chars'), ['"az\\955\\n"'])
    for mode in 'new', 'all':
      M = None
      M = switch(mode)
      interpreted = cyrt.icurry_is_interpreted(M.fact.info)
      self.assertEqual(interpreted, mode == 'all', mode)
      self.assertEqual(
          cyrt.icurry_is_interpreted(curry.symbol('Prelude.map').info)
        , mode == 'all', mode
        )
      if mode == 'all':
        self.assertEqual(self.values(M), expected)

  @cytest.hardreset
  def test_failure(self):
    M = switch('all')
    # headOf [] fails: no value.
    self.assertEqual(list(curry.eval(M.headOf, [])), [])
    self.assertRaisesRegex(
        EvaluationError, 'boom'
      , lambda: list(curry.eval(curry.expr(M.boom, 1)))
      )


@ONLY_CXX
class TestLoader(cytest.TestCase):
  '''
  The flag selects what is interpreted: with 'new', a module compiled from
  a string, and not a module with a compiled object; with 'all', every
  module, the Prelude included.  The built-in functions keep their steps.
  '''
  TEXT = '''
import CxxInterp
double :: Int -> Int
double x = x + x
main :: Int
main = double (CxxInterp.fact 3)
'''

  @cytest.hardreset
  def test_new(self):
    M = switch('new')
    # The compiled object of the module was used.
    self.assertIsNotNone(getHandle(M).icurry.metadata.get('cxx.shlib'))
    self.assertFalse(cyrt.icurry_is_interpreted(M.fact.info))
    before = cyrt.icurry_count()
    N = curry.compile(self.TEXT, mode='module')
    self.assertIsNone(getHandle(N).icurry.metadata.get('cxx.shlib'))
    self.assertTrue(cyrt.icurry_is_interpreted(N.double.info))
    self.assertTrue(cyrt.icurry_is_interpreted(N.main.info))
    self.assertEqual(cyrt.icurry_count(), before + 2)
    self.assertEqual(list(curry.eval(N.main, converter='topython')), [12])
    # An expression compiles to an interpreted function.
    e = curry.compile('CxxInterp.fact 5 + 1', mode='expr', imports=[M])
    self.assertEqual(next(curry.eval(e, converter='topython')), 121)
    # The bytecode of an interpreted function.
    bc = cyrt.icurry_bytecode(N.double.info)
    self.assertEqual(
        sorted(bc), ['code', 'nconsts', 'nregs', 'nstack', 'nvars']
      )
    self.assertEqual(bc['nregs'], 1)
    self.assertEqual(bc['nvars'], 0)
    self.assertEqual(list(bytecode.disassemble(bc['code'])), [
        '   0 LOAD_ROOT_SUCC r0 0', '   3 PUSH_REG r0', '   5 PUSH_REG r0'
      , '   7 RET_NODE k0 2'
      ])
    self.assertIsNone(cyrt.icurry_bytecode(M.fact.info))
    self.assertIsNone(cyrt.icurry_bytecode(curry.symbol('Prelude.:').info))

  @cytest.hardreset
  def test_all(self):
    M = switch('all')
    self.assertIsNone(getHandle(M).icurry.metadata.get('cxx.shlib'))
    self.assertTrue(cyrt.icurry_is_interpreted(M.fact.info))
    prelude = curry.import_('Prelude')
    self.assertIsNone(getHandle(prelude).icurry.metadata.get('cxx.shlib'))
    self.assertTrue(cyrt.icurry_is_interpreted(prelude.map.info))
    self.assertTrue(cyrt.icurry_is_interpreted(prelude.length.info))
    # A built-in keeps the step of the runtime.
    self.assertFalse(
        cyrt.icurry_is_interpreted(curry.symbol('Prelude.plusInt').info)
      )
    self.assertFalse(
        cyrt.icurry_is_interpreted(curry.symbol('Prelude.apply').info)
      )
    # Set functions.
    setf = curry.import_('Control.SetFunctions')
    self.assertFalse(cyrt.icurry_is_interpreted(setf.set1.info))
    self.assertTrue(cyrt.icurry_is_interpreted(setf.sortValues.info))
    self.assertGreater(cyrt.icurry_count(), 1000)
    self.assertEqual(
        list(curry.eval(
            curry.expr(prelude.length, [1, 2, 3]), converter='topython'
          ))
      , [3]
      )

  @cytest.hardreset
  def test_attach_refusals(self):
    M = switch('off')
    code = [bytecode.OP['EXEMPT']]
    # A static table: a compiled function, a built-in.
    for info in M.fact.info, curry.symbol('Prelude.plusInt').info:
      self.assertRaisesRegex(
          ValueError, 'static', cyrt.icurry_attach, info, code, [], 0, 0, 0
        )
    # A constructor.
    self.assertRaisesRegex(
        ValueError, 'not a function', cyrt.icurry_attach
      , M.Circle.info, code, [], 0, 0, 0
      )
    # A function interpreted already.
    M = None
    M = switch('all')
    self.assertRaisesRegex(
        ValueError, 'has a step', cyrt.icurry_attach
      , M.fact.info, code, [], 0, 0, 0
      )
    # A bad constant.
    info = getHandle(M).backend_handle.create_infotable(
        'fresh', 1, common.T_FUNC, 0
      )
    self.assertRaisesRegex(
        TypeError, 'constant', cyrt.icurry_attach, info, code, [1], 0, 0, 0
      )
    self.assertRaisesRegex(
        ValueError, 'kind', cyrt.icurry_attach, info, code, [('X', 1)], 0, 0, 0
      )
    self.assertFalse(cyrt.icurry_is_interpreted(info))
    # The flag is read back.
    self.assertEqual(curry.flags['interpret'], 'all')


@ONLY_CXX
class TestSteps(cytest.TestCase):
  '''
  One step of an interpreted function at the root of a raw expression: the
  redex is rewritten in place or forwarded, as for compiled code (see
  unit_cxx_rewrite.py).
  '''
  @classmethod
  def setUpClass(cls):
    cls.M = switch('all')

  @classmethod
  def tearDownClass(cls):
    # The module object goes before the interpreter of the environment
    # comes back (see switch).
    cls.M = None
    gc.collect()
    importlib.reload(curry)
    gc.collect()

  def step(self, expr, until, limit=64):
    for _ in range(limit):
      evaluator.single_step(curry.getInterpreter(), expr)
      if until(expr):
        return expr
    raise AssertionError('the root did not change in %d steps' % limit)

  def test_tail_call_in_place(self):
    e = curry.raw_expr(self.M.walk, [1, 2, 3])
    start = str(e)
    self.step(e, lambda e: str(e) != start)
    self.assertEqual(e.info.tag, common.T_FUNC)
    self.assertEqual(e.info.name, 'walk')
    self.assertEqual(str(e), str(curry.raw_expr(self.M.walk, [2, 3])))

  def test_constructor_in_place(self):
    e = curry.raw_expr(self.M.rot3, 1, 2, 3)
    self.step(e, lambda e: e.info.name != 'rot3')
    self.assertEqual(e.info.name, 'Pair3')
    self.assertEqual(str(e), 'Pair3 3 1 2')

  def test_reference_results(self):
    e = curry.raw_expr(self.M.second, 1, 2)
    self.step(e, lambda e: e.info.name != 'second')
    self.assertEqual(e.info.name, 'Int')
    self.assertEqual(str(e), '2')
    e = curry.raw_expr(self.M.keepShape, 1, curry.raw_expr(self.M.Rect, 1, 2))
    self.step(e, lambda e: e.info.name != 'keepShape')
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertEqual(str(next(curry.eval(e))), 'Rect 1 2')

  def test_pinned_result_is_forwarded(self):
    e = curry.raw_expr(self.M.vowel, 'a')
    self.step(e, lambda e: e.info.name != 'vowel')
    self.assertEqual(e.info.tag, common.T_FWD)
    self.assertEqual(str(next(curry.eval(e))), 'True')

  def test_string_result_in_place(self):
    e = curry.raw_expr(self.M.greeting)
    self.step(e, lambda e: e.info.name != 'greeting')
    self.assertEqual(e.info.name, '_biString')
    self.assertEqual(str(next(curry.eval(e))), '"hello, world"')

  def test_tail_calls_allocate_nothing(self):
    e = curry.raw_expr(self.M.walk, list(range(100)))
    before = cyrt.gc_allocation_count()
    self.assertEqual(next(curry.eval(e, converter='topython')), 0)
    self.assertLess(cyrt.gc_allocation_count() - before, 20)


@ONLY_CXX
class TestPrograms(cytest.TestCase):
  '''
  Benchmark programs under the interpreter, in children: the values and the
  step counts of the compiled code, in plain mode and in the stress mode of
  the collector.
  '''
  def run_child(self, program, mode, stress=False):
    # The child collects at every step only when asked: a program of a few
    # million steps does not end in time otherwise.
    env = dict(os.environ)
    env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:%s' % mode
    env['CURRYPATH'] = BENCHMARKS
    env.pop('SPRITE_GC_STRESS', None)
    if stress:
      env['SPRITE_GC_STRESS'] = '1'
    cmd = [
        'prlimit', '--as=%d' % ADDRESS_SPACE, 'timeout', str(TIMEOUT)
      , config.installed_path('bin', 'sprite-exec'), '--stats', '-m', program
      ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    stats = dict(
        item.split('=', 1)
          for item in proc.stderr.strip().splitlines()[-1].split()
      )
    return proc.stdout.strip(), int(stats['steps'])

  def test_programs(self):
    for program, value in ('Peano', None), ('Fib', 'True'), ('Last', 'True'):
      expected, steps = self.run_child(program, 'off')
      if value is not None:
        self.assertEqual(expected, value)
      for mode in 'new', 'all':
        self.assertEqual(
            self.run_child(program, mode), (expected, steps), program
          )

  def test_stress_mode(self):
    expected, steps = self.run_child('Last', 'off')
    self.assertEqual(
        self.run_child('Last', 'all', stress=True), (expected, steps)
      )


@ONLY_CXX
class TestFirstUse(cytest.TestCase):
  '''
  Under 'off' a module imported from an ICurry object compiles on its first
  use (issue #102).  The toolchain never saw the module, so its functions
  carry the trap step of the runtime (cyrt/module.hpp) until the first call
  of one of them writes the C++ of the ICurry object beside the source,
  compiles it and swaps the steps (materialize.first_use).  With the compile
  turned off, or failed, the trap raises the documented error instead of
  crashing the process.
  '''
  TEXT = '''
module %(name)s where
double :: Int -> Int
double x = x + x
main :: Int
main = double 21
boom :: Int
boom = error "boom"
'''
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-firstuse-')
    gc.collect()
    curry.reload({'backend': 'cxx', 'interpret': 'off'})
    gc.collect()
    curry.path.insert(0, self.tmpdir)
    self.currypath = list(curry.path)

  def tearDown(self):
    gc.collect()
    shutil.rmtree(self.tmpdir, ignore_errors=True)
    super().tearDown()

  def write(self, text=TEXT, stem='CxxFirstUse'):
    '''Writes a module under a new name.  Returns the name.'''
    name = '%s%d' % (stem, next(self.counter))
    with open(os.path.join(self.tmpdir, name + '.curry'), 'w') as stream:
      stream.write(text % {'name': name})
    return name

  def icurry(self, name):
    '''The ICurry of the module ``name``, as the plan writes it: no object.'''
    plan = plans.makeplan(
        None, plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON
      )
    return toolchain.loadcurry(plan, name, self.currypath)

  def import_(self, name):
    '''Imports the module ``name`` from its ICurry object.'''
    return curry.import_(self.icurry(name), currypath=self.currypath)

  def product(self, name, suffix):
    return os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), name + suffix
      )

  def assertTrapped(self, M, *names):
    for name in names:
      info = getattr(M, name).info
      self.assertTrue(cyrt.is_trapped(info), name)
      self.assertFalse(info.has_step, name)
    self.assertTrue(materialize.is_pending(M))

  def assertCompiled(self, M, *names):
    for name in names:
      info = getattr(M, name).info
      self.assertFalse(cyrt.is_trapped(info), name)
      self.assertTrue(info.has_step, name)
    self.assertFalse(materialize.is_pending(M))

  @cytest.hardreset
  def test_compiled_on_first_use(self):
    name = self.write()
    M = self.import_(name)
    h = getHandle(M)
    self.assertTrapped(M, 'double', 'main', 'boom')
    self.assertIsNone(h.icurry.metadata.get('cxx.shlib'))
    sofile = self.product(name, '.so')
    self.assertFalse(os.path.exists(sofile))
    # An expression built before the compile holds the tables the object
    # binds to (the shim of tiered.py).
    e = curry.expr(M.double, 5)
    before = curry.stats()['swapped']
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertCompiled(M, 'double', 'main', 'boom')
    self.assertEqual(curry.stats()['swapped'] - before, 3)
    # The object beside the source, with its stamp and the generated file.
    self.assertTrue(os.path.isfile(sofile))
    self.assertTrue(os.path.isfile(sofile + '.abi'))
    self.assertTrue(os.path.isfile(self.product(name, '.cpp')))
    self.assertEqual(os.path.realpath(h.sofilename), os.path.realpath(sofile))
    self.assertIn('/****** %s.main ******/' % name, inspect.getimpl(M.main))
    self.assertEqual(list(curry.eval(e, converter='topython')), [10])
    # No second compile.
    mtime = os.path.getmtime(sofile)
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertEqual(os.path.getmtime(sofile), mtime)
    self.assertRaisesRegex(
        EvaluationError, 'boom', lambda: list(curry.eval(M.boom))
      )

  @cytest.hardreset
  def test_trap_without_the_compile(self):
    '''The error of the trap step, with the compile turned off.'''
    name = self.write()
    M = self.import_(name)
    pattern = r"cannot evaluate function '%s\.main': the function has no " \
              r"compiled code \(its module was imported from an ICurry " \
              r"object under interpret:off\): the compile on first use is " \
              r"turned off" % name
    with mock.patch.object(materialize, 'COMPILE_ON_FIRST_USE', False):
      self.assertRaisesRegex(
          EvaluationError, pattern, lambda: list(curry.eval(M.main))
        )
      self.assertTrapped(M, 'double', 'main', 'boom')
      self.assertFalse(os.path.exists(self.product(name, '.so')))
      # The single step of the evaluator raises it too.
      self.assertRaisesRegex(
          EvaluationError, pattern, evaluator.single_step
        , curry.getInterpreter(), curry.raw_expr(M.main)
        )
      # A function nested in another module's evaluation names itself.
      self.assertRaisesRegex(
          EvaluationError, r"cannot evaluate function '%s\.double'" % name
        , lambda: list(curry.eval(curry.expr(M.double, 1)))
        )
    # With the compile on again the module compiles and runs.
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertCompiled(M, 'double', 'main', 'boom')

  @cytest.hardreset
  def test_trap_after_a_failed_compile(self):
    '''The error names the failure; the module stays trapped.'''
    name = self.write()
    M = self.import_(name)
    def fail(self_, file_in, currypath, **ignored):
      raise CompileError('g++ exited with status 1')
    with mock.patch.object(cxx_toolchain.Cpp2So, '__call__', fail):
      with self.assertLogs('curry.backends.cxx.materialize', 'WARNING') as logs:
        self.assertRaisesRegex(
            EvaluationError
          , r"cannot evaluate function '%s\.main': .*: the compile failed: "
            r"g\+\+ exited with status 1" % name
          , lambda: list(curry.eval(M.main))
          )
    self.assertTrue(
        any('cannot compile module %r on its first use' % name in line
            for line in logs.output)
      , logs.output
      )
    self.assertTrapped(M, 'double', 'main', 'boom')
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertCompiled(M, 'double', 'main', 'boom')

  @cytest.hardreset
  def test_pending_import_compiles_first(self):
    '''
    A module imported from an ICurry object that imports another: the
    import compiles first, because the object names the object of its
    import.
    '''
    a = self.write()
    b = self.write('''
module %%(name)s where
import %s
twice :: Int -> Int
twice x = double (double x)
''' % a)
    A = self.import_(a)
    B = self.import_(b)
    self.assertTrapped(A, 'double', 'main')
    self.assertTrapped(B, 'twice')
    self.assertEqual(list(curry.eval(B.twice, 3, converter='topython')), [12])
    self.assertCompiled(A, 'double', 'main')
    self.assertCompiled(B, 'twice')
    for name in a, b:
      self.assertTrue(os.path.isfile(self.product(name, '.so')), name)
    self.assertEqual(list(curry.eval(A.main, converter='topython')), [42])

  @cytest.hardreset
  def test_without_a_source_file(self):
    '''
    An ICurry object without a source file compiles into a directory of the
    process: nothing beside the source.
    '''
    name = self.write()
    imodule = self.icurry(name)
    imodule.filename = None
    M = curry.import_(imodule, currypath=self.currypath)
    self.assertTrapped(M, 'main')
    self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertCompiled(M, 'double', 'main', 'boom')
    self.assertFalse(os.path.exists(self.product(name, '.so')))
    sofile = getHandle(M).sofilename
    self.assertTrue(sofile.startswith(tiered._tmpdir()), sofile)
    self.assertTrue(os.path.isfile(sofile))

  @cytest.hardreset
  def test_other_modes_do_not_trap(self):
    '''Under the interpreter the functions get bytecode, as before.'''
    name = self.write()
    for mode in 'new', 'tiered':
      gc.collect()
      curry.reload({'backend': 'cxx', 'interpret': mode})
      gc.collect()
      curry.path.insert(0, self.tmpdir)
      self.currypath = list(curry.path)
      M = self.import_(name)
      self.assertFalse(cyrt.is_trapped(M.main.info))
      self.assertTrue(cyrt.icurry_is_interpreted(M.main.info))
      self.assertFalse(materialize.is_pending(M))
      self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
      M = None
      tiered.cancel()
      tiered.wait(10)

  def object_of(self, name):
    '''Compiles the module ``name`` as the plan does.  Nothing is loaded.'''
    plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    sofile = _makecurry.makecurry(plan, name, self.currypath)
    self.assertEqual(os.path.realpath(sofile), os.path.realpath(self.product(name, '.so')))
    return sofile

  def cache_entry(self, name):
    '''The entry of the product cache for the source of ``name``, or None.'''
    cpp2so = cxx_toolchain.Cpp2So(curry.getInterpreter())
    key = cpp2so.product_key(
        os.path.join(self.tmpdir, name + '.curry'), self.currypath
      )
    return _productcache.lookup(
        cpp2so.digest(), key, [name + '.cpp', name + '.so']
      )

  def use_scratch(self):
    '''
    Moves the sources of the test under tests/.cache: a source under the
    temporary directory of the system stays out of the product cache
    (_productcache.excluded), and a test of the cache needs one that does
    not.
    '''
    cachedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
    os.makedirs(cachedir, exist_ok=True)
    scratch = tempfile.mkdtemp(dir=cachedir, prefix='firstuse-')
    self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
    self.tmpdir = scratch
    curry.path.insert(0, scratch)
    self.currypath = list(curry.path)

  @contextlib.contextmanager
  def count_compiles(self):
    '''Counts the calls of Cpp2So while the block runs.'''
    calls = []
    original = cxx_toolchain.Cpp2So.__call__
    def counted(self_, *args, **kwds):
      calls.append(args[0])
      return original(self_, *args, **kwds)
    with mock.patch.object(cxx_toolchain.Cpp2So, '__call__', counted):
      yield calls

  @cytest.hardreset
  def test_transformed_object_leaves_the_products(self):
    '''
    An ICurry object changed in memory is not the translation of the
    source: its products go into a directory of the process, never beside
    the source or into the product cache, which a later import of the
    module by name would load (the review of issue #102).
    '''
    self.use_scratch()
    name = self.write('''
module %(name)s where
main :: Int
main = 1
other :: Int
other = 2
''')
    imodule = self.icurry(name)
    a, b = imodule.functions['main'], imodule.functions['other']
    a.body, b.body = b.body, a.body
    M = curry.import_(imodule, currypath=self.currypath)
    self.assertTrapped(M, 'main', 'other')
    with self.count_compiles() as calls:
      self.assertEqual(list(curry.eval(M.main, converter='topython')), [2])
    self.assertEqual(len(calls), 1)
    self.assertCompiled(M, 'main', 'other')
    for suffix in '.cpp', '.so', '.so.abi':
      self.assertFalse(os.path.exists(self.product(name, suffix)), suffix)
    sofile = getHandle(M).sofilename
    self.assertTrue(sofile.startswith(tiered._tmpdir()), sofile)
    if _productcache.enabled():
      self.assertIsNone(self.cache_entry(name))

  @cytest.hardreset
  def test_translation_is_recognized(self):
    '''
    The object the plan gives, after the import changed it in place (the
    merge, the passes), is the translation on disk; an object with another
    body, or without a JSON beside its source, is not.
    '''
    name = self.write()
    interp = curry.getInterpreter()
    imodule = self.icurry(name)
    M = curry.import_(imodule, currypath=self.currypath)
    self.assertTrue(materialize.is_translation(interp, imodule))
    main = imodule.functions['main']
    body = main.body
    main.body = imodule.functions['boom'].body
    self.assertFalse(materialize.is_translation(interp, imodule))
    main.body = body
    self.assertTrue(materialize.is_translation(interp, imodule))
    for suffix in '.json.z', '.json':
      try:
        os.unlink(self.product(name, suffix))
      except FileNotFoundError:
        pass
    self.assertFalse(materialize.is_translation(interp, imodule))
    imodule.filename = None
    self.assertFalse(materialize.is_translation(interp, imodule))

  @cytest.hardreset
  def test_current_object_is_adopted(self):
    '''
    A current object beside the source, whose generated file has the text
    of the object in hand, is adopted on the first use: no compile, as
    sprite-make --so skips a current object.
    '''
    name = self.write()
    sofile = self.object_of(name)
    mtime = os.path.getmtime(sofile)
    M = self.import_(name)
    self.assertTrapped(M, 'double', 'main', 'boom')
    with self.count_compiles() as calls:
      self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertEqual(calls, [])
    self.assertCompiled(M, 'double', 'main', 'boom')
    self.assertEqual(os.path.getmtime(sofile), mtime)
    self.assertEqual(
        os.path.realpath(getHandle(M).sofilename), os.path.realpath(sofile)
      )

  @cytest.hardreset
  def test_cached_object_is_restored(self):
    '''
    Without an object beside the source, the first use asks the product
    cache before the compiler, as the plan does.
    '''
    if not _productcache.enabled():
      self.skipTest('the product cache is off')
    self.use_scratch()
    name = self.write()
    sofile = self.object_of(name)
    self.assertIsNotNone(self.cache_entry(name))
    for suffix in '.cpp', '.so', '.so.abi':
      os.unlink(self.product(name, suffix))
    M = self.import_(name)
    with self.count_compiles() as calls:
      self.assertEqual(list(curry.eval(M.main, converter='topython')), [42])
    self.assertEqual(calls, [])
    self.assertCompiled(M, 'double', 'main', 'boom')
    self.assertTrue(os.path.isfile(sofile))
    self.assertTrue(os.path.isfile(self.product(name, '.cpp')))
    self.assertEqual(
        os.path.realpath(getHandle(M).sofilename), os.path.realpath(sofile)
      )

  @cytest.hardreset
  def test_no_second_compile_after_the_adopt(self):
    '''
    A table the adopted object left trapped (the object has no step of its
    name) raises at every call and never compiles its module again.
    '''
    name = self.write()
    M = self.import_(name)
    adopted = {'ok': True, 'swapped': 0, 'output': '', 'error': ''}
    pattern = r"cannot evaluate function '%s\.main': .*: the compiled " \
              r"object has no step for it" % name
    with self.count_compiles() as calls:
      with mock.patch.object(cyrt, 'tiered_adopt', return_value=adopted):
        self.assertRaisesRegex(
            EvaluationError, pattern, lambda: list(curry.eval(M.main))
          )
      self.assertEqual(len(calls), 1)
      self.assertTrue(cyrt.is_trapped(M.main.info))
      self.assertFalse(materialize.is_pending(M))
      self.assertRaisesRegex(
          EvaluationError, pattern, lambda: list(curry.eval(M.main))
        )
      self.assertEqual(len(calls), 1)
