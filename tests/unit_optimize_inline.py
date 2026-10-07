'''
Tests for the ICurry optimizer: the inliner (inline_calls; O2 and O3 of the
performance program).

A saturated call of a non-recursive function whose body is an expression of
at most ``inline_budget`` nodes is replaced by the body (O2).  A saturated
call ``g (K a b)`` of a non-recursive function whose body is one case on that
parameter, with a branch for ``K``, is replaced by the body of the branch,
with the fields for the pattern variables (O3).  Every argument, field, or
local expression that the body uses more than once is bound to a fresh
variable of the caller's block first, so that it is built once (call-time
choice); a free variable of the body is a fresh free variable of the caller.
The results are rewritten again, with the saturation of apply chains, so the
dictionary chain of a class method on a constant dictionary resolves: x /= y
on Int is not (eqInt x y).  Each function records the body it had before the
pass, when it is small and non-recursive, under analysis.INLINE_KEY, so a
module loaded from its compiled form still tells it to its importers.

The helpers come from unit_optimize.py: ModuleTestCase writes modules into a
temporary directory; a module imported from its ICurry object shows the
optimized structure (icurry_of with inline=True), and a module imported by
name gives values.  The unoptimized form of a program is the same text under
another name, imported from its ICurry object with the key of the pass set,
which the framework reads as "this pass ran".  Every test of values compares
the optimized program with the unoptimized one, on both backends.
'''
import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.icurry import analysis, types
from curry.interpreter import optimize
from curry.toolchain import plans
from curry.toolchain._loadcurry import loadjson
from unit_optimize import ModuleTestCase, call, function, ifcalls
from unit_optimize_applies import applies, known_applies
import curry, os

def passkey():
  return '%s.opt.inline_calls' % curry.flags['backend']

def lit(value):
  return types.ILit(types.IInt(value))

def result_of(ifun):
  '''The expression that the top block of ``ifun`` returns.'''
  return ifun.body.block.stmt.expr

def fresh_assigns(ifun):
  '''The assignments of the top block that are not parameter bindings.'''
  return [
      assign for assign in ifun.body.block.assigns
             if not isinstance(assign.expr, types.IVarAccess)
    ]

def freedecls(ifun):
  return [
      decl for decl in ifun.body.block.vardecls
           if isinstance(decl, types.IFreeDecl)
    ]

def pair(*exprs):
  return types.ICCall('Prelude.(,)', list(exprs))

def external(name, arity):
  return function(name, arity, [], None, body=types.IExternal('M.' + name))


class TestInlineAnalysis(cytest.TestCase):
  '''The shapes, the recursion test, and the inliner on hand-built ICurry.'''

  def test_node_count(self):
    '''A variable counts nothing; every node built counts one.'''
    self.assertEqual(analysis.node_count(types.IVar(1)), 0)
    self.assertEqual(analysis.node_count(lit(1)), 1)
    self.assertEqual(analysis.node_count(types.IString('ab')), 1)
    acall = types.IFCall('M.f', [types.IVar(1), lit(2)])
    self.assertEqual(analysis.node_count(acall), 2)
    self.assertEqual(analysis.node_count(types.IOr(acall, lit(0))), 4)
    self.assertEqual(
        analysis.node_count(
            types.ICCall('M.K', [types.IFPCall('M.f', 1, [types.IVar(1)])])
          )
      , 2
      )

  def test_expression_body(self):
    # dup x = (x, x)
    dup = function(
        'dup', 1, [(1, [0])]
      , types.IReturn(pair(types.IVar(1), types.IVar(1)))
      )
    shape = analysis.body_shape(dup.body, 1)
    self.assertIsInstance(shape, analysis.ExpressionBody)
    self.assertEqual(shape.params, {1: 0})
    self.assertEqual(shape.locals, [])
    self.assertEqual(shape.frees, [])
    self.assertEqual(shape.size, 1)
    self.assertEqual(shape.uses, {1: 2})
    # withLet x = let y = f x in (y, y): a local.
    block = types.IBlock(
        [types.IVarDecl(1), types.IVarDecl(2)]
      , [ types.IVarAssign(1, types.IVarAccess(0, [0]))
        , types.IVarAssign(2, types.IFCall('M.f', [types.IVar(1)]))
        ]
      , types.IReturn(pair(types.IVar(2), types.IVar(2)))
      )
    shape = analysis.body_shape(types.IFuncBody(block), 1)
    self.assertEqual([vid for vid, _ in shape.locals], [2])
    self.assertEqual(shape.size, 2)
    self.assertEqual(shape.uses, {1: 1, 2: 2})
    # freeVal = x where x free
    block = types.IBlock(
        [types.IFreeDecl(1)], [], types.IReturn(types.IVar(1))
      )
    shape = analysis.body_shape(types.IFuncBody(block), 0)
    self.assertEqual(shape.frees, [1])
    self.assertEqual(shape.size, 0)
    self.assertEqual(shape.result, types.IVar(1))
    # Two variables bound to one parameter (test_two_variables_one_parameter
    # inlines the shape).
    both = function(
        'both', 1, [(1, [0]), (2, [0])]
      , types.IReturn(pair(types.IVar(1), types.IVar(2)))
      )
    shape = analysis.body_shape(both.body, 1)
    self.assertEqual(shape.params, {1: 0, 2: 0})
    self.assertEqual(shape.uses, {1: 1, 2: 1})

  def branches(self):
    '''The branches of sel (K a _) = (a, a); sel N = (0, 0); sel E = failed.'''
    k = types.IConsBranch('M.K', 2, types.IBlock(
        [types.IVarDecl(2)]
      , [types.IVarAssign(2, types.IVarAccess(1, [0]))]
      , types.IReturn(pair(types.IVar(2), types.IVar(2)))
      ))
    n = types.IConsBranch('M.N', 0, types.IBlock(
        [], [], types.IReturn(pair(lit(0), lit(0)))
      ))
    e = types.IConsBranch('M.E', 0, types.IBlock([], [], types.IExempt()))
    return k, n, e

  def test_case_body(self):
    k, n, e = self.branches()
    sel = function('sel', 1, [(1, [0])], types.ICaseCons(1, [k, n, e]))
    shape = analysis.body_shape(sel.body, 1)
    self.assertIsInstance(shape, analysis.CaseBody)
    self.assertEqual(shape.scrutinee, 1)
    self.assertEqual(shape.index, 0)
    # The branch with an exempt is left out.
    self.assertEqual(set(shape.branches), {'M.K', 'M.N'})
    branch = shape.branches['M.K']
    self.assertEqual(branch.arity, 2)
    self.assertEqual(branch.fields, {2: 0})
    self.assertEqual(branch.fields_at(0), [2])
    self.assertEqual(branch.fields_at(1), [])
    self.assertEqual(branch.size, 1)
    self.assertEqual(branch.uses, {2: 2})
    self.assertEqual(shape.branches['M.N'].size, 3)
    self.assertEqual(shape.branches['M.N'].uses, {})
    self.assertEqual(shape.size, 3)
    # The case on the second parameter.
    sel2 = function(
        'sel2', 2, [(1, [1]), (2, [0])], types.ICaseCons(1, [k, n])
      )
    shape = analysis.body_shape(sel2.body, 2)
    self.assertEqual((shape.scrutinee, shape.index), (1, 1))
    # Every branch exempt: no shape.
    fail = function('fail', 1, [(1, [0])], types.ICaseCons(1, [e]))
    self.assertIsNone(analysis.body_shape(fail.body, 1))

  def test_not_a_shape(self):
    k, n, e = self.branches()
    nested = types.IConsBranch('M.N', 0, types.IBlock(
        [], [], types.ICaseCons(1, [k])
      ))
    cases = {
        'nested case': function(
            'f', 1, [(1, [0])], types.ICaseCons(1, [nested])
          )
      , 'case on a local': function(
            'f', 1, [], None, body=types.IFuncBody(types.IBlock(
                [types.IVarDecl(1)]
              , [types.IVarAssign(1, types.IFCall('M.g', []))]
              , types.ICaseCons(1, [k, n])
              ))
          )
      , 'recursive let': function(
            'f', 1, [], None, body=types.IFuncBody(types.IBlock(
                [types.IVarDecl(1)]
              , [ types.IVarAssign(1, types.ICCall('M.K', [lit(1), lit(2)]))
                , types.INodeAssign(1, [1], types.IVar(1))
                ]
              , types.IReturn(types.IVar(1))
              ))
          )
      , 'a path of two entries': function(
            'f', 1, [(1, [0, 1])], types.IReturn(types.IVar(1))
          )
      , 'a variable the body does not bind': function(
            'f', 1, [(1, [0])], types.IReturn(types.IVar(2))
          )
      , 'an access inside an expression': function(
            'f', 1, [(1, [0])]
          , types.IReturn(types.IFCall('M.g', [types.IVarAccess(1, [0])]))
          )
      , 'the redex': function(
            'f', 1, [(1, [0])], types.IReturn(types.IVar(0))
          )
      , 'a variable never assigned': function(
            'f', 1, [], None, body=types.IFuncBody(types.IBlock(
                [types.IVarDecl(1)], [], types.IReturn(lit(1))
              ))
          )
      , 'exempt': function(
            'f', 1, [], None, body=types.IFuncBody(types.IExempt())
          )
      , 'external': external('f', 1)
      , 'builtin': function('f', 1, [], None, body=types.IBuiltin())
      }
    for name, ifun in cases.items():
      self.assertIsNone(analysis.body_shape(ifun.body, 1), name)
      self.assertIsNone(analysis.inline_shape(ifun), name)
    # A branch that binds a field the inliner does not follow is left out;
    # the other branches stay.
    deep = types.IConsBranch('M.K', 2, types.IBlock(
        [types.IVarDecl(2)]
      , [types.IVarAssign(2, types.IVarAccess(1, [0, 0]))]
      , types.IReturn(types.IVar(2))
      ))
    sel = function('sel', 1, [(1, [0])], types.ICaseCons(1, [deep, n]))
    shape = analysis.body_shape(sel.body, 1)
    self.assertEqual(set(shape.branches), {'M.N'})

  def test_recursion(self):
    '''
    A function on a cycle of saturated calls is recursive.  A partial
    application of itself, a call into another module, and a call of a
    recursive function are not edges of a cycle.
    '''
    f = function('f', 1, [(1, [0])], call('f', 1))
    g = function('g', 1, [(1, [0])], call('h', 1))
    h = function('h', 1, [(1, [0])], call('g', 1))
    p = function(
        'p', 1, [(1, [0])]
      , types.IReturn(types.IFPCall('M.p', 2, [types.IVar(1)]))
      )
    q = function(
        'q', 1, [(1, [0])]
      , types.IReturn(types.IFCall('N.q', [types.IVar(1)]))
      )
    k = function('k', 1, [(1, [0])], call('f', 1))
    imodule = types.IModule('M', [], [], [f, g, h, p, q, k])
    modules = {'M': imodule}
    self.assertEqual(
        analysis.recursive_functions(imodule), frozenset({'M.f', 'M.g', 'M.h'})
      )
    self.assertIs(
        analysis.recursive_functions(imodule)
      , analysis.recursive_functions(imodule)
      )
    for ifun in f, g, h:
      self.assertTrue(analysis.is_recursive(ifun, modules), ifun.name)
    for ifun in p, q, k:
      self.assertFalse(analysis.is_recursive(ifun, modules), ifun.name)
    # A function whose module is not loaded counts as recursive.
    self.assertTrue(analysis.is_recursive(k, {}))

  def test_shape_from_metadata(self):
    '''A module loaded from its compiled form has no bodies: metadata speaks.
    '''
    dup = function(
        'dup', 1, [(1, [0])]
      , types.IReturn(pair(types.IVar(1), types.IVar(1)))
      )
    text = analysis.inline_body_text(dup.body)
    self.assertEqual(icurry.json.loads(text), dup.body)
    stub = function('s', 1, [], None, body=types.IFuncBody(types.IExempt()))
    stub.update_metadata({analysis.INLINE_KEY: text})
    shape = analysis.inline_shape(stub)
    self.assertIsInstance(shape, analysis.ExpressionBody)
    self.assertEqual(shape.size, 1)
    self.assertIs(analysis.inline_shape(stub), shape)
    # A text that is not a body, or not JSON, makes the function unknown.
    for bad in [icurry.json.dumps(types.IVar(1)), '[not json']:
      stub = function('b', 1, [], None, body=types.IFuncBody(types.IExempt()))
      stub.update_metadata({analysis.INLINE_KEY: bad})
      self.assertIsNone(analysis.inline_shape(stub))
    # The shape of a live function is a copy of the body as it was.
    shape = analysis.inline_shape(dup)
    dup.body.block.stmt.expr.exprs.append(lit(3))
    self.assertEqual(len(shape.result.exprs), 2)
    self.assertEqual(shape.body, icurry.json.loads(text))

  def test_inliner(self):
    '''
    The inliner on a hand-built module: an argument used twice is bound to a
    fresh variable; one used once is written at its use; a variable is
    written as it is.  The budget bounds the bodies inlined; 0 turns the
    inliner off.
    '''
    dup = function(
        'dup', 1, [(1, [0])]
      , types.IReturn(pair(types.IVar(1), types.IVar(1)))
      )
    once = function(
        'once', 1, [(1, [0])]
      , types.IReturn(types.ICCall('M.K', [types.IVar(1)]))
      )
    two = function(
        'two', 1, [(1, [0])]
      , types.IReturn(
            types.ICCall('M.K', [types.ICCall('M.K', [types.IVar(1)])])
          )
      )
    f = external('f', 1)
    def caller():
      return function(
          'main', 1, [(1, [0])]
        , types.IReturn(types.ICCall('Prelude.(,,,)', [
              types.IFCall('M.dup', [types.IFCall('M.f', [lit(1)])])
            , types.IFCall('M.once', [types.IFCall('M.f', [lit(2)])])
            , types.IFCall('M.dup', [types.IVar(1)])
            , types.IFCall('M.two', [lit(3)])
            ]))
        )
    main = caller()
    imodule = types.IModule('M', [], [], [dup, once, two, f, main])
    modules = {'M': imodule}
    inliner = analysis.Inliner(modules, 4)
    self.assertEqual(inliner.rewrite(main), 4)
    fresh = fresh_assigns(main)
    self.assertEqual(len(fresh), 1)
    self.assertEqual(fresh[0].expr, types.IFCall('M.f', [lit(1)]))
    v = fresh[0].vid
    self.assertIn(types.IVarDecl(v), main.body.block.vardecls)
    self.assertEqual(
        result_of(main)
      , types.ICCall('Prelude.(,,,)', [
            pair(types.IVar(v), types.IVar(v))
          , types.ICCall('M.K', [types.IFCall('M.f', [lit(2)])])
          , pair(types.IVar(1), types.IVar(1))
          , types.ICCall('M.K', [types.ICCall('M.K', [lit(3)])])
          ])
      )
    self.assertTrue(
        {'Prelude.(,)', 'M.K', 'M.f'} <= inliner.symbols, inliner.symbols
      )
    # The budget: two builds two nodes.
    main = caller()
    self.assertEqual(analysis.Inliner(modules, 1).rewrite(main), 3)
    self.assertEqual(result_of(main).exprs[3], types.IFCall('M.two', [lit(3)]))
    main = caller()
    self.assertEqual(analysis.Inliner(modules, 0).rewrite(main), 0)
    self.assertEqual(result_of(main), result_of(caller()))

  def test_two_variables_one_parameter(self):
    '''
    Two variables bound to one parameter name one argument: their uses
    count together, so an argument that each uses once is built once.  The
    same holds for the whole of a single-case body named through a second
    variable.  Each variable was bound alone, and the argument expression
    was written at both uses: a choice there would have been built twice.
    '''
    # both x = (x, x'), where x' is the parameter bound again.
    both = function(
        'both', 1, [(1, [0]), (2, [0])]
      , types.IReturn(pair(types.IVar(1), types.IVar(2)))
      )
    f = external('f', 1)
    def caller(callee, arg):
      return function(
          'main', 1, [(1, [0])]
        , types.IReturn(types.IFCall('M.' + callee, [arg]))
        )
    main = caller('both', types.IFCall('M.f', [lit(1)]))
    imodule = types.IModule('M', [], [], [both, f, main])
    self.assertEqual(analysis.Inliner({'M': imodule}, 4).rewrite(main), 1)
    fresh = fresh_assigns(main)
    self.assertEqual(len(fresh), 1)
    self.assertEqual(fresh[0].expr, types.IFCall('M.f', [lit(1)]))
    v = fresh[0].vid
    self.assertEqual(result_of(main), pair(types.IVar(v), types.IVar(v)))
    # A variable argument is written at every use, as before.
    main = caller('both', types.IVar(1))
    imodule = types.IModule('M', [], [], [both, f, main])
    self.assertEqual(analysis.Inliner({'M': imodule}, 4).rewrite(main), 1)
    self.assertEqual(fresh_assigns(main), [])
    self.assertEqual(result_of(main), pair(types.IVar(1), types.IVar(1)))
    # sel (K a _) = (a, k), where k is the parameter bound again: the field
    # is used by itself and inside the whole, so it is built once, and the
    # whole is written at its one use.
    k = types.IConsBranch('M.K', 2, types.IBlock(
        [types.IVarDecl(3)]
      , [types.IVarAssign(3, types.IVarAccess(1, [0]))]
      , types.IReturn(pair(types.IVar(3), types.IVar(2)))
      ))
    sel = function('sel', 1, [(1, [0]), (2, [0])], types.ICaseCons(1, [k]))
    main = caller(
        'sel', types.ICCall('M.K', [types.IFCall('M.f', [lit(1)]), lit(2)])
      )
    imodule = types.IModule('M', [], [], [sel, f, main])
    self.assertEqual(analysis.Inliner({'M': imodule}, 4).rewrite(main), 1)
    fresh = fresh_assigns(main)
    self.assertEqual(len(fresh), 1)
    self.assertEqual(fresh[0].expr, types.IFCall('M.f', [lit(1)]))
    a = fresh[0].vid
    self.assertEqual(
        result_of(main)
      , pair(types.IVar(a), types.ICCall('M.K', [types.IVar(a), lit(2)]))
      )

  def test_inliner_case(self):
    '''
    The known-constructor rule on a hand-built module: a field used twice is
    bound to a fresh variable, the whole constructor is built once when the
    branch uses it, an unused field is dropped, and a constructor without a
    branch stays.
    '''
    k, n, e = self.branches()
    sel = function('sel', 1, [(1, [0])], types.ICaseCons(1, [k, n, e]))
    whole = function('whole', 1, [(1, [0])], types.ICaseCons(1, [
        types.IConsBranch('M.K', 2, types.IBlock(
            [types.IVarDecl(2)]
          , [types.IVarAssign(2, types.IVarAccess(1, [0]))]
          , types.IReturn(
                pair(types.IFCall('M.g', [types.IVar(1)]), types.IVar(2))
              )
          ))
      ]))
    second = function('second', 1, [(1, [0])], types.ICaseCons(1, [
        types.IConsBranch('M.K', 2, types.IBlock(
            [types.IVarDecl(3)]
          , [types.IVarAssign(3, types.IVarAccess(1, [1]))]
          , types.IReturn(types.IVar(3))
          ))
      ]))
    f = external('f', 1)
    g = external('g', 1)
    def caller():
      return function(
          'main', 0, []
        , types.IReturn(types.ICCall('Prelude.(,,,,)', [
              types.IFCall('M.sel', [
                  types.ICCall('M.K', [types.IFCall('M.f', [lit(1)]), lit(2)])
                ])
            , types.IFCall('M.whole', [
                  types.ICCall('M.K', [types.IFCall('M.f', [lit(3)]), lit(4)])
                ])
            , types.IFCall('M.second', [
                  types.ICCall('M.K', [types.IFCall('M.f', [lit(5)]), lit(6)])
                ])
            , types.IFCall('M.sel', [types.ICCall('M.N', [])])
            , types.IFCall('M.sel', [types.ICCall('M.E', [])])
            ]))
        )
    main = caller()
    imodule = types.IModule('M', [], [], [sel, whole, second, f, g, main])
    inliner = analysis.Inliner({'M': imodule}, 4)
    self.assertEqual(inliner.rewrite(main), 4)
    fresh = fresh_assigns(main)
    self.assertEqual(len(fresh), 2)
    self.assertEqual(fresh[0].expr, types.IFCall('M.f', [lit(1)]))
    self.assertEqual(fresh[1].expr, types.IFCall('M.f', [lit(3)]))
    a, b = (assign.vid for assign in fresh)
    # The whole constructor is used once, so it is written at its use, with
    # the shared field inside.
    self.assertEqual(
        result_of(main)
      , types.ICCall('Prelude.(,,,,)', [
            pair(types.IVar(a), types.IVar(a))
          , pair(
                types.IFCall('M.g', [
                    types.ICCall('M.K', [types.IVar(b), lit(4)])
                  ])
              , types.IVar(b)
              )
          , lit(6)
          , pair(lit(0), lit(0))
          , types.IFCall('M.sel', [types.ICCall('M.E', [])])
          ])
      )
    # A whole used twice is built once.
    twice = function('twice', 1, [(1, [0])], types.ICaseCons(1, [
        types.IConsBranch('M.K', 2, types.IBlock(
            [types.IVarDecl(2)]
          , [types.IVarAssign(2, types.IVarAccess(1, [0]))]
          , types.IReturn(types.ICCall('Prelude.(,,)', [
                types.IVar(1), types.IVar(1), types.IVar(2)
              ]))
          ))
      ]))
    main = function('main', 0, [], types.IReturn(types.IFCall('M.twice', [
        types.ICCall('M.K', [types.IFCall('M.f', [lit(7)]), lit(8)])
      ])))
    imodule = types.IModule('M', [], [], [twice, f, main])
    self.assertEqual(analysis.Inliner({'M': imodule}, 4).rewrite(main), 1)
    fresh = fresh_assigns(main)
    self.assertEqual(len(fresh), 2)
    self.assertEqual(fresh[0].expr, types.IFCall('M.f', [lit(7)]))
    b, c = (assign.vid for assign in fresh)
    self.assertEqual(
        fresh[1].expr, types.ICCall('M.K', [types.IVar(b), lit(8)])
      )
    self.assertEqual(
        result_of(main)
      , types.ICCall(
            'Prelude.(,,)', [types.IVar(c), types.IVar(c), types.IVar(b)]
          )
      )


class InlineTestCase(ModuleTestCase):
  '''ModuleTestCase with the optimized and the unoptimized form of a module.'''

  def optimized(self, name):
    return self.icurry_of(name, inline=True)

  def unoptimized(self, name):
    '''
    Imports the module ``name`` from its ICurry object with the key of the
    pass set, so the pass does not run on it.  Returns the module object.
    '''
    imodule = self.load_icurry(name)
    imodule.update_metadata({passkey(): True})
    return curry.import_(imodule, currypath=self.currypath)

  def values(self, module, goal):
    return list(curry.eval(getattr(module, goal), converter='topython'))

  def check_values(self, stem, text, values):
    optimized = self.import_(self.write(stem, text))
    unoptimized = self.unoptimized(self.write(stem, text))
    for goal, expected in values.items():
      self.assertCountEqual(self.values(optimized, goal), expected, goal)
      self.assertCountEqual(self.values(unoptimized, goal), expected, goal)


class TestInlineShapes(InlineTestCase):
  '''The structure of the ICurry after the pass: the expression bodies.'''

  def test_budget(self):
    '''A body of four nodes is inlined; one of five is not.'''
    name = self.write('Inline', INLINE)
    imodule = self.optimized(name)
    fn = imodule.functions
    self.assertTrue(imodule.metadata[passkey()])
    self.assertEqual(analysis.inline_shape(fn['four']).size, 4)
    self.assertEqual(analysis.inline_shape(fn['five']).size, 5)
    self.assertEqual(
        result_of(fn['useFour'])
      , pair(types.IFCall('Prelude.plusInt', [lit(10), lit(1)]), lit(2))
      )
    self.assertEqual(
        result_of(fn['useFive']), types.IFCall('%s.five' % name, [lit(10)])
      )

  def test_recursive_left_alone(self):
    '''A recursive function and a mutually recursive pair stay calls.'''
    name = self.write('Inline', INLINE)
    imodule = self.optimized(name)
    fn = imodule.functions
    self.assertEqual(
        result_of(fn['useRec']), types.IFCall('%s.rec' % name, [lit(3)])
      )
    self.assertEqual(
        result_of(fn['useEv']), types.IFCall('%s.ev' % name, [lit(4)])
      )
    recursive = analysis.recursive_functions(imodule)
    for fname in 'rec', 'ev', 'od':
      self.assertIn('%s.%s' % (name, fname), recursive)
      self.assertNotIn(analysis.INLINE_KEY, fn[fname].metadata, fname)
    for fname in 'four', 'dup':
      self.assertNotIn('%s.%s' % (name, fname), recursive)

  def test_sharing_shapes(self):
    '''
    An argument used twice is built once, in a fresh variable of the
    caller's block; a variable is written at every use; an argument used
    once is written there; one not used is dropped; a choice in the body is
    one choice per call site; a local of the body gets a fresh variable when
    it is used more than once.
    '''
    name = self.write('Inline', INLINE)
    fn = self.optimized(name).functions
    for goal, arg in ('choiceArg', types.IOr(lit(0), lit(1))), \
        ('callArg', types.IFCall('Prelude.plusInt', [lit(3), lit(4)])), \
        ('useLet', types.IFCall('Prelude.plusInt', [lit(1), lit(1)])):
      fresh = fresh_assigns(fn[goal])
      self.assertEqual(len(fresh), 1, goal)
      self.assertEqual(fresh[0].expr, arg, goal)
      v = fresh[0].vid
      self.assertIn(types.IVarDecl(v), fn[goal].body.block.vardecls)
      self.assertEqual(
          result_of(fn[goal]), pair(types.IVar(v), types.IVar(v))
        )
    self.assertEqual(fresh_assigns(fn['varArg']), [])
    self.assertEqual(
        result_of(fn['varArg'])
      , pair(pair(types.IVar(1), types.IVar(1)), lit(0))
      )
    self.assertEqual(fresh_assigns(fn['twoCoins']), [])
    self.assertEqual(
        result_of(fn['twoCoins'])
      , pair(types.IOr(lit(0), lit(1)), types.IOr(lit(0), lit(1)))
      )
    self.assertEqual(result_of(fn['useDrop']), lit(5))
    self.assertEqual(ifcalls(fn['useDrop']), [])
    self.assertEqual(fresh_assigns(fn['useLetOnce']), [])
    self.assertEqual(
        result_of(fn['useLetOnce'])
      , types.IFCall('Prelude.plusInt', [
            types.IFCall('Prelude.timesInt', [lit(4), lit(2)]), lit(1)
          ])
      )
    for goal in 'choiceArg', 'callArg', 'varArg', 'twoCoins', 'useDrop' \
        , 'useLet', 'useLetOnce':
      self.assertFalse(
          [c for c in ifcalls(fn[goal]) if c.startswith(name + '.')], goal
        )

  def test_alias_of_apply(self):
    '''
    A call of a user alias of apply stays, as for the saturation pass:
    inline_aliases then makes an apply of it, on a known head, which the
    runtime applies (unit_cxx_partial.py tests that path).
    '''
    name = self.write('App', '''
      app :: (a -> b) -> a -> b
      app f x = f x
      inc :: Int -> Int
      inc x = x + 1
      useApp :: Int
      useApp = app inc 5
      ''')
    imodule = self.optimized(name)
    use = imodule.functions['useApp']
    self.assertEqual(ifcalls(use), [analysis.APPLY])
    self.assertEqual(
        result_of(use)
      , types.IFCall(analysis.APPLY, [
            types.IFPCall('%s.inc' % name, 1, []), lit(5)
          ])
      )
    modules = curry.getInterpreter().modules
    self.assertEqual(len(known_applies(use, modules)), 1)
    module = self.import_(self.write('App', '''
      app :: (a -> b) -> a -> b
      app f x = f x
      inc :: Int -> Int
      inc x = x + 1
      useApp :: Int
      useApp = app inc 5
      '''))
    self.assertEqual(self.values(module, 'useApp'), [6])

  def test_free_variable(self):
    '''A free variable of the body is a fresh free variable of the caller.'''
    name = self.write('Inline', INLINE)
    fn = self.optimized(name).functions
    use = fn['useFree']
    decls = freedecls(use)
    self.assertEqual(len(decls), 1)
    self.assertNotIn('%s.freeVal' % name, ifcalls(use))
    # The let variable of the caller is bound to the free variable.
    self.assertEqual(
        fresh_assigns(use), [types.IVarAssign(1, types.IVar(decls[0].vid))]
      )
    self.assertEqual(analysis.inline_shape(fn['freeVal']).frees, [1])

  def test_metadata(self):
    '''
    A small non-recursive body is recorded, as it was before the pass; a
    recursive one is not; a private function is recorded when a recorded
    body names it.
    '''
    name = self.write('Inline', INLINE)
    fn = self.optimized(name).functions
    for fname in [
        'four', 'five', 'dup', 'coin', 'freeVal', 'dropArg', 'withLet'
      ]:
      self.assertIn(analysis.INLINE_KEY, fn[fname].metadata, fname)
    for fname in 'rec', 'ev', 'od':
      self.assertNotIn(analysis.INLINE_KEY, fn[fname].metadata, fname)
    body = icurry.json.loads(fn['four'].metadata[analysis.INLINE_KEY])
    self.assertIsInstance(body, types.IFuncBody)
    self.assertEqual(analysis.body_shape(body, 1).size, 4)
    self.assertEqual(
        body, analysis.inline_shape(fn['four']).body
      )
    # The recorded body is the body before the pass: useFour names four.
    body = icurry.json.loads(fn['useFour'].metadata[analysis.INLINE_KEY])
    self.assertEqual(ifcalls(body), ['%s.four' % name])
    name = self.write('Priv', '''
      module %(name)s (useFour) where
      four :: Int -> (Int, Int)
      four x = (x + 1, 2)
      useFour :: (Int, Int)
      useFour = four 10
      hidden :: Int -> Int
      hidden x = x + 1
      ''')
    imodule = self.optimized(name)
    fn = imodule.functions
    self.assertTrue(fn['four'].is_private)
    self.assertIn(analysis.INLINE_KEY, fn['four'].metadata)
    self.assertIn(analysis.INLINE_KEY, fn['useFour'].metadata)
    self.assertNotIn(analysis.INLINE_KEY, fn['hidden'].metadata)
    self.assertEqual(
        analysis.recorded_functions(imodule, curry.getInterpreter().modules)
      , frozenset(['%s.four' % name, '%s.useFour' % name])
      )


class TestCaseShapes(InlineTestCase):
  '''The structure of the ICurry after the pass: the single-case bodies.'''

  def test_known_constructor(self):
    name = self.write('Cases', CASES)
    fn = self.optimized(name).functions
    # A choice in a field is built once.
    fresh = fresh_assigns(fn['choiceField'])
    self.assertEqual(len(fresh), 1)
    self.assertEqual(fresh[0].expr, types.IOr(lit(0), lit(1)))
    v = fresh[0].vid
    self.assertEqual(
        result_of(fn['choiceField']), pair(types.IVar(v), types.IVar(v))
      )
    # Literal fields are written at every use.
    self.assertEqual(fresh_assigns(fn['useSel']), [])
    self.assertEqual(result_of(fn['useSel']), pair(lit(1), lit(1)))
    self.assertEqual(result_of(fn['selN']), pair(lit(0), lit(0)))
    # A field used once is written at its use: the result is the choice.
    self.assertEqual(result_of(fn['useJ']), types.IOr(lit(0), lit(1)))
    # An unused field is dropped.
    self.assertEqual(result_of(fn['useUnused']), lit(9))
    self.assertEqual(ifcalls(fn['useUnused']), [])
    for goal in 'choiceField', 'useSel', 'selN', 'useJ', 'useUnused':
      self.assertFalse(
          [c for c in ifcalls(fn[goal]) if c.startswith(name + '.')], goal
        )

  def test_whole_parameter(self):
    '''
    A branch that uses the parameter as a whole and a field: the field is
    built once, the constructor is built once around it.
    '''
    name = self.write('Cases', CASES)
    fn = self.optimized(name).functions
    fresh = fresh_assigns(fn['useWhole'])
    self.assertEqual(len(fresh), 1)
    self.assertEqual(fresh[0].expr, types.IOr(lit(0), lit(1)))
    a = fresh[0].vid
    # The whole is used once, so the constructor is written at its use,
    # where sumT, a single-case function, resolves on it in turn.
    self.assertEqual(
        result_of(fn['useWhole'])
      , pair(
            types.IFCall('Prelude.plusInt', [types.IVar(a), lit(5)])
          , types.IVar(a)
          )
      )
    # A whole used twice is built once, around the shared field.
    fresh = fresh_assigns(fn['useTwice'])
    self.assertEqual(len(fresh), 2)
    self.assertEqual(fresh[0].expr, types.IOr(lit(0), lit(1)))
    a, c = fresh[0].vid, fresh[1].vid
    self.assertEqual(
        fresh[1].expr, types.ICCall('%s.K' % name, [types.IVar(a), lit(5)])
      )
    self.assertEqual(
        result_of(fn['useTwice'])
      , types.ICCall('Prelude.(,,)', [
            types.IFCall('%s.sumT' % name, [types.IVar(c)])
          , types.IFCall('%s.sumT' % name, [types.IVar(c)])
          , types.IVar(a)
          ])
      )

  def test_two_cases(self):
    '''
    A function of two patterns: the front end lifts the inner case into a
    function of its own.  A call with two constructors resolves whole; a
    call with a variable in the second position keeps the inner case
    function, whose scrutinee is not a constructor.  A body with a nested
    case is never inlined (TestInlineAnalysis.test_not_a_shape).
    '''
    name = self.write('Cases', CASES)
    fn = self.optimized(name).functions
    self.assertEqual(
        result_of(fn['useTwo'])
      , types.IFCall('Prelude.plusInt', [lit(1), lit(3)])
      )
    calls = [c for c in ifcalls(fn['useTwoVar']) if c.startswith(name + '.')]
    self.assertEqual(len(calls), 1, calls)
    self.assertTrue(calls[0].startswith('%s.twoCases_' % name), calls)
    self.assertNotEqual(calls[0], '%s.twoCases' % name)

  def test_metadata(self):
    name = self.write('Cases', CASES)
    fn = self.optimized(name).functions
    for fname in 'sel', 'whole', 'twice', 'fromJ', 'unused', 'sumT':
      self.assertIsInstance(
          analysis.inline_shape(fn[fname]), analysis.CaseBody, fname
        )
      self.assertIn(analysis.INLINE_KEY, fn[fname].metadata, fname)
    body = icurry.json.loads(fn['sel'].metadata[analysis.INLINE_KEY])
    shape = analysis.body_shape(body, 1)
    self.assertEqual(set(shape.branches), {'%s.K' % name, '%s.N' % name})


class TestEvaluation(InlineTestCase):
  '''Values and steps of the optimized program against the unoptimized one.'''

  def test_values(self):
    self.check_values('Inline', INLINE, INLINE_VALUES)

  def test_case_values(self):
    self.check_values('Cases', CASES, CASE_VALUES)

  @cytest.hardreset
  def test_flag(self):
    '''
    The flag inline_budget at 0 turns both rules off: the calls stay, and
    the values are those of the optimized program.  The bodies are recorded
    all the same.
    '''
    self.reload(inline_budget=0)
    self.assertEqual(curry.flags['inline_budget'], 0)
    name = self.write('Inline', INLINE)
    imodule = self.optimized(name)
    fn = imodule.functions
    self.assertTrue(imodule.metadata[passkey()])
    self.assertEqual(
        result_of(fn['useFour']), types.IFCall('%s.four' % name, [lit(10)])
      )
    self.assertEqual(
        result_of(fn['choiceArg'])
      , types.IFCall('%s.dup' % name, [types.IOr(lit(0), lit(1))])
      )
    self.assertIn(analysis.INLINE_KEY, fn['four'].metadata)
    name = self.write('Cases', CASES)
    fn = self.optimized(name).functions
    self.assertEqual(
        result_of(fn['choiceField'])
      , types.IFCall('%s.sel' % name, [
            types.ICCall('%s.K' % name, [types.IOr(lit(0), lit(1)), lit(2)])
          ])
      )
    for stem, text, values in [
        ('Inline', INLINE, INLINE_VALUES), ('Cases', CASES, CASE_VALUES)
      ]:
      module = self.import_(self.write(stem, text))
      for goal, expected in values.items():
        self.assertCountEqual(self.values(module, goal), expected, goal)

  @cytest.hardreset
  def test_steps(self):
    '''
    An inlined call saves its rewrite step.  Under the C++ backend the
    modules stay interpreted, so no background compile swaps the code of
    the unoptimized module.
    '''
    self.reload(interpret='new')
    def steps(module, goal, expected):
      values, count = self.steps(getattr(module, goal))
      self.assertEqual(values, expected)
      return count
    optimized = self.import_(self.write('Inline', INLINE))
    unoptimized = self.unoptimized(self.write('Inline', INLINE))
    self.assertEqual(
        steps(unoptimized, 'useFour', [(11, 2)])
          - steps(optimized, 'useFour', [(11, 2)])
      , 1
      )
    self.assertEqual(
        steps(unoptimized, 'useFive', [(11, 12)])
      , steps(optimized, 'useFive', [(11, 12)])
      )
    optimized = self.import_(self.write('Cases', CASES))
    unoptimized = self.unoptimized(self.write('Cases', CASES))
    self.assertEqual(
        steps(unoptimized, 'useSel', [(1, 1)])
          - steps(optimized, 'useSel', [(1, 1)])
      , 1
      )

  @cytest.hardreset
  def test_generated_code(self):
    '''
    The generated code of the backend handles the block shapes the pass
    produces: fresh variables bound to calls, choices, and constructors, a
    free variable, a literal result.  The modules are compiled, not
    interpreted.
    '''
    self.compiled()
    for stem, text, values in [
        ('Inline', INLINE, INLINE_VALUES), ('Cases', CASES, CASE_VALUES)
      ]:
      name = self.write(stem, text)
      module = self.import_(name)
      for goal, expected in values.items():
        self.assertCountEqual(self.values(module, goal), expected, goal)
      text = self.generated_text(name)
      self.assertTrue(text)


class TestAcrossModules(InlineTestCase):
  '''The bodies of a module loaded from its compiled form.'''

  @cytest.hardreset
  def test_bodies_across_modules(self):
    '''
    A function of a module loaded from its compiled form is known through
    its metadata: an expression body and a single-case body alike.  When
    the copied body names a symbol of a module the caller does not import,
    the module joins the imports.
    '''
    self.compiled()
    base = self.write('Base', '''
      data U = C Int Int
      four :: Int -> (Int, Int)
      four x = (x + 1, 2)
      unC :: U -> Int
      unC (C a _) = a
      mk :: Int -> U
      mk x = C x 1
      ''')
    middle = self.write('Middle', '''
      import %s
      wrap :: Int -> U
      wrap x = mk (x + 1)
      unwrap :: U -> Int
      unwrap (C a _) = a
      ''' % base)
    top = self.write('Top', '''
      import %s
      useFour :: (Int, Int)
      useFour = four 10
      useC :: Int
      useC = unC (C (0 ? 1) 2)
      ''' % base)
    base_module = self.import_(base)
    fn = getattr(base_module, '.icurry').functions
    for fname in 'four', 'unC', 'mk':
      self.assertNotIsInstance(fn[fname].body.block, types.IBlock)
      self.assertIn(analysis.INLINE_KEY, fn[fname].metadata, fname)
    self.assertEqual(analysis.inline_shape(fn['four']).size, 4)
    self.assertIsInstance(analysis.inline_shape(fn['unC']), analysis.CaseBody)
    self.assertTrue(getattr(base_module, '.icurry').metadata[passkey()])
    imodule = self.load_icurry(top)
    curry.import_(imodule, currypath=self.currypath)
    self.assertEqual(
        result_of(imodule.functions['useFour'])
      , pair(types.IFCall('Prelude.plusInt', [lit(10), lit(1)]), lit(2))
      )
    self.assertEqual(
        result_of(imodule.functions['useC']), types.IOr(lit(0), lit(1))
      )
    # Through Middle: wrap and unwrap are inlined, mk and C of Base with
    # them, so Base joins the imports.
    self.import_(middle)
    imodule = self.load_icurry(self.write('Top2', '''
      import %s
      main :: Int
      main = unwrap (wrap 1)
      ''' % middle))
    self.assertNotIn(base, imodule.imports)
    imports = imodule.imports
    curry.import_(imodule, currypath=self.currypath)
    self.assertEqual(
        result_of(imodule.functions['main'])
      , types.IFCall('Prelude.plusInt', [lit(1), lit(1)])
      )
    self.assertEqual(imodule.imports, imports + (base,))
    # The values, from a module of the same text imported by name: on the
    # C++ backend a module imported from its ICurry object has no object
    # to run under interpret 'off'.
    module = self.import_(self.write('Use', '''
      import %s
      import %s
      useFour :: (Int, Int)
      useFour = four 10
      useC :: Int
      useC = unC (C (0 ? 1) 2)
      main :: Int
      main = unwrap (wrap 1)
      ''' % (base, middle)))
    self.assertEqual(self.values(module, 'useFour'), [(11, 2)])
    self.assertCountEqual(self.values(module, 'useC'), [0, 1])
    self.assertEqual(self.values(module, 'main'), [2])


class TestChain(InlineTestCase):
  '''The dictionary chain of a class method on a constant dictionary.'''

  def test_chain(self):
    '''
    After saturation, inlining, the known-constructor rule and the alias
    pass, x /= y on Int is not (eqInt x y), and mod x n /= 0 is
    not (eqInt (modInt x n) 0): no apply, no class default, no instance
    dictionary remains.  The Prelude's not on a literal constructor
    resolves as well.
    '''
    name = self.write('Chain', CHAIN)
    imodule = self.optimized(name)
    fn = imodule.functions
    self.assertEqual(
        result_of(fn['neq'])
      , types.IFCall('Prelude.not', [
            types.IFCall('Prelude.eqInt', [types.IVar(1), types.IVar(2)])
          ])
      )
    self.assertEqual(
        result_of(fn['divides'])
      , types.IFCall('Prelude.not', [
            types.IFCall('Prelude.eqInt', [
                types.IFCall('Prelude.modInt', [types.IVar(2), types.IVar(1)])
              , lit(0)
              ])
          ])
      )
    self.assertEqual(result_of(fn['notTrue']), types.ICCall('Prelude.False'))
    calls = ifcalls(imodule)
    self.assertFalse(applies(imodule))
    for part in '_def#', '_inst#', '_impl#', 'Prelude.$':
      self.assertFalse([c for c in calls if part in c], part)

  def test_values(self):
    self.check_values('Chain', CHAIN, CHAIN_VALUES)

  @cytest.hardreset
  def test_steps(self):
    '''
    not (eqInt 1 2) costs three steps: the goal, not, and eqInt.  The chain
    of the unoptimized program costs the class default, the selector and
    its lambda, the applies, the dictionary, and the instance method
    besides.
    '''
    self.reload(interpret='new')
    optimized = self.import_(self.write('Chain', CHAIN))
    unoptimized = self.unoptimized(self.write('Chain', CHAIN))
    values, after = self.steps(optimized.neqGoal)
    self.assertEqual(values, [True])
    values, before = self.steps(unoptimized.neqGoal)
    self.assertEqual(values, [True])
    self.assertEqual(after, 3)
    self.assertGreaterEqual(before - after, 8)


class TestPrelude(cytest.TestCase):
  '''The Prelude: the installed one, and its ICurry as the toolchain reads it.
  '''

  RECORDED = [
      '_def#/=#Prelude.Eq', '_inst#Prelude.Eq#Prelude.Int', 'not', '=='
    , '==._#lambda', '_impl#==#Prelude.Eq#Prelude.Int', 'divMod._#lambda'
    , '_def#mod#Prelude.Integral', '_def#mod#Prelude.Integral._#selFP4#r'
    , '_inst#Prelude.Integral#Prelude.Int'
    , '_impl#divMod#Prelude.Integral#Prelude.Int', 'fst', 'maybe', '&&'
    ]
  RECURSIVE = ['length', 'foldr', 'map', 'filter', '++']

  def prelude_json(self):
    jsonfile = os.path.join(
        config.system_curry_path(), '.curry', config.intermediate_subdir()
      , 'Prelude.json.z'
      )
    return loadjson(jsonfile)

  def test_installed_prelude(self):
    '''
    The staged Prelude was compiled with the pass: its metadata records the
    bodies of the chain, and a module that imports it resolves x /= y.
    '''
    interp = curry.getInterpreter()
    imodule = getattr(interp.prelude, '.icurry')
    self.assertTrue(imodule.metadata[passkey()])
    for name in self.RECORDED:
      self.assertIn(
          analysis.INLINE_KEY, imodule.functions[name].metadata, name
        )
    for name in self.RECURSIVE:
      self.assertNotIn(
          analysis.INLINE_KEY, imodule.functions[name].metadata, name
        )
    shape = analysis.inline_shape(imodule.functions['_def#/=#Prelude.Eq'])
    self.assertIsInstance(shape, analysis.ExpressionBody)
    self.assertEqual(shape.size, 4)
    shape = analysis.inline_shape(
        imodule.functions['_inst#Prelude.Eq#Prelude.Int']
      )
    self.assertIsInstance(shape, analysis.CaseBody)
    self.assertEqual(set(shape.branches), {'Prelude.()'})
    goal = curry.compile('(3 /= 4, 3 /= 3, mod 7 3 /= 0)', 'expr')
    self.assertEqual(
        list(curry.eval(goal, converter='topython')), [(True, False, True)]
      )

  def test_prelude_source(self):
    '''
    The passes over the ICurry of the Prelude: no apply with a known head
    remains, so no call of a nullary instance method that unfolds to a
    partial application sits in a saturable position; the class defaults
    inline the selectors; every instance dictionary records its body; a
    recursive function records none.
    '''
    imodule = self.prelude_json()
    modules = {'Prelude': imodule}
    interp = curry.getInterpreter()
    for ifun in imodule.functions.values():
      optimize.saturate_applies(interp, ifun, imodule, modules=modules)
    for ifun in imodule.functions.values():
      optimize.inline_calls(interp, ifun, imodule, modules=modules)
    for ifun in imodule.functions.values():
      optimize.inline_aliases(interp, ifun, imodule)
    self.assertFalse(known_applies(imodule, modules))
    self.assertEqual(imodule.imports, ())
    nullary = [
        iapply for iapply in applies(imodule, modules)
               if type(iapply.exprs[0]) is types.IFCall
                  and not iapply.exprs[0].exprs
      ]
    for iapply in nullary:
      ifun = imodule.functions[iapply.exprs[0].symbolname.partition('.')[2]]
      self.assertIsNone(analysis.unfolding(ifun, modules), str(iapply))
    ne = imodule.functions['_def#/=#Prelude.Eq']
    self.assertIn('Prelude.==._#lambda', ifcalls(ne))
    self.assertNotIn('Prelude.==', ifcalls(ne))
    recorded = analysis.recorded_functions(imodule, modules)
    for name in imodule.functions:
      if name.startswith('_inst#'):
        self.assertIn('Prelude.' + name, recorded, name)
        self.assertIn(
            analysis.INLINE_KEY, imodule.functions[name].metadata, name
          )
    for name in self.RECORDED:
      self.assertIn('Prelude.' + name, recorded, name)
    for name in self.RECURSIVE:
      self.assertNotIn('Prelude.' + name, recorded, name)
      self.assertIn('Prelude.' + name, analysis.recursive_functions(imodule))
    # A private function that no recorded body names records nothing.
    private = [
        name for name, ifun in imodule.functions.items()
             if ifun.is_private and analysis.INLINE_KEY not in ifun.metadata
      ]
    self.assertTrue(private)


class TestBenchmarkShapes(cytest.TestCase):
  '''The chains of Queens10 and Primes, the programs of the gate.'''

  def test_safe_and_isdivs(self):
    currypath = [
        os.path.join(os.path.dirname(__file__), 'data', 'curry', 'benchmarks')
      ]
    plan = plans.makeplan(
        None, plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON
      )
    interp = curry.getInterpreter()
    interp.prelude
    def passes(ifun, imodule):
      optimize.saturate_applies(interp, ifun, imodule)
      optimize.inline_calls(interp, ifun, imodule)
      optimize.inline_aliases(interp, ifun, imodule)
    imodule = toolchain.loadcurry(plan, 'Queens10', currypath)
    safe = imodule.functions['safe']
    passes(safe, imodule)
    calls = ifcalls(safe)
    self.assertEqual(calls.count('Prelude.not'), 3)
    self.assertEqual(calls.count('Prelude.eqInt'), 3)
    self.assertFalse([c for c in calls if '_def#' in c or '_inst#' in c])
    self.assertFalse(applies(safe))
    imodule = toolchain.loadcurry(plan, 'Primes', currypath)
    isdivs = imodule.functions['isdivs']
    passes(isdivs, imodule)
    self.assertEqual(
        result_of(isdivs)
      , types.IFCall('Prelude.not', [
            types.IFCall('Prelude.eqInt', [
                types.IFCall('Prelude.modInt', [types.IVar(2), types.IVar(1)])
              , lit(0)
              ])
          ])
      )


# The module of the expression-body tests.  four builds four nodes (the
# pair, the addition, and two literals) and five builds five.
INLINE = '''
  four :: Int -> (Int, Int)
  four x = (x + 1, 2)
  five :: Int -> (Int, Int)
  five x = (x + 1, x + 2)
  useFour :: (Int, Int)
  useFour = four 10
  useFive :: (Int, Int)
  useFive = five 10
  rec :: Int -> Int
  rec n = if n == 0 then 0 else rec (n - 1)
  useRec :: Int
  useRec = rec 3
  ev :: Int -> Bool
  ev n = if n == 0 then True else od (n - 1)
  od :: Int -> Bool
  od n = if n == 0 then False else ev (n - 1)
  useEv :: Bool
  useEv = ev 4
  dup :: Int -> (Int, Int)
  dup x = (x, x)
  choiceArg :: (Int, Int)
  choiceArg = dup (0 ? 1)
  callArg :: (Int, Int)
  callArg = dup (3 + 4)
  varArg :: Int -> ((Int, Int), Int)
  varArg y = (dup y, 0)
  coin :: Int
  coin = 0 ? 1
  twoCoins :: (Int, Int)
  twoCoins = (coin, coin)
  freeVal :: Int
  freeVal = x where x free
  useFree :: Int
  useFree = let v = freeVal in (v =:= 3) &> v
  dropArg :: Int -> Int -> Int
  dropArg x _ = x
  useDrop :: Int
  useDrop = dropArg 5 (3 + 4)
  withLet :: Int -> (Int, Int)
  withLet x = let y = x + 1 in (y, y)
  useLet :: (Int, Int)
  useLet = withLet 1
  letOnce :: Int -> Int
  letOnce x = let y = x * 2 in y + 1
  useLetOnce :: Int
  useLetOnce = letOnce 4
  '''

INLINE_VALUES = {
    'useFour': [(11, 2)], 'useFive': [(11, 12)], 'useRec': [0]
  , 'useEv': [True], 'choiceArg': [(0, 0), (1, 1)], 'callArg': [(7, 7)]
  , 'twoCoins': [(0, 0), (0, 1), (1, 0), (1, 1)], 'useFree': [3]
  , 'useDrop': [5], 'useLet': [(2, 2)], 'useLetOnce': [9]
  }

# The module of the single-case tests (section 4.3 of the plan: a choice in
# a constructor field is built once).
CASES = '''
  data T = K Int Int | N
  sel :: T -> (Int, Int)
  sel (K a _) = (a, a)
  sel N = (0, 0)
  choiceField :: (Int, Int)
  choiceField = sel (K (0 ? 1) 2)
  useSel :: (Int, Int)
  useSel = sel (K 1 2)
  selN :: (Int, Int)
  selN = sel N
  sumT :: T -> Int
  sumT (K a b) = a + b
  sumT N = 0
  whole :: T -> (Int, Int)
  whole t@(K a _) = (sumT t, a)
  whole N = (0, 0)
  useWhole :: (Int, Int)
  useWhole = whole (K (0 ? 1) 5)
  twice :: T -> (Int, Int, Int)
  twice t@(K a _) = (sumT t, sumT t, a)
  twice N = (0, 0, 0)
  useTwice :: (Int, Int, Int)
  useTwice = twice (K (0 ? 1) 5)
  twoCases :: T -> T -> Int
  twoCases (K a _) (K b _) = a + b
  twoCases (K a _) N = a
  twoCases N _ = 0
  useTwo :: Int
  useTwo = twoCases (K 1 2) (K 3 4)
  useTwoVar :: T -> Int
  useTwoVar t = twoCases (K 1 2) t
  fromJ :: Maybe Int -> Int
  fromJ (Just x) = x
  fromJ Nothing = 0
  useJ :: Int
  useJ = fromJ (Just (0 ? 1))
  unused :: T -> Int
  unused (K _ b) = b
  unused N = 0
  useUnused :: Int
  useUnused = unused (K (3 + 4) 9)
  '''

CASE_VALUES = {
    'choiceField': [(0, 0), (1, 1)], 'useSel': [(1, 1)], 'selN': [(0, 0)]
  , 'useWhole': [(5, 0), (6, 1)], 'useTwice': [(5, 5, 0), (6, 6, 1)]
  , 'useTwo': [4], 'useJ': [0, 1], 'useUnused': [9]
  }

# The module of the chain tests.
CHAIN = '''
  neq :: Int -> Int -> Bool
  neq x y = x /= y
  divides :: Int -> Int -> Bool
  divides n x = mod x n /= 0
  notTrue :: Bool
  notTrue = not True
  neqGoal :: Bool
  neqGoal = neq 1 2
  main :: [Bool]
  main = [neq 1 2, neq 3 3, divides 3 7, divides 3 9, notTrue]
  '''

CHAIN_VALUES = {
    'main': [[True, False, True, False, False]], 'neqGoal': [True]
  }
