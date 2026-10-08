'''
Tests for the ICurry optimizer: the saturation of apply chains.

A chain ``apply (apply h x) y`` whose head is known becomes the call it
builds: one saturated call when the argument count fits the arity, a shorter
partial application when arguments are still missing, and a saturated call
followed by the remaining applies when there are too many.  A head is known
when it is a partial application, or a call without arguments of a nullary
function whose body is one (followed to a bounded depth), or an apply whose
head is known, so the order of the functions does not matter.  A variable
head, a call with arguments, and a head held in a variable stay.  A call of
$, an alias of apply, is an apply to the pass.  The pass saturate_applies
runs before inline_aliases when a module is loaded, so it reaches the
generated code of both backends; each nullary function records the partial
application it unfolds to under analysis.UNFOLDING_KEY, so a module loaded
from its compiled form still tells it to its importers.

The helpers come from unit_optimize.py: ModuleTestCase writes modules into a
temporary directory; a module imported from its ICurry object shows the
optimized structure, and a module imported by name gives values.  The
unoptimized form of a program is the same text under another name, imported
from its ICurry object with the key of the pass already set, which the
framework reads as "this pass ran".
'''
import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.icurry import analysis, types
from curry.interpreter import optimize
from curry.toolchain import plans
from curry.toolchain._loadcurry import loadjson
from unit_optimize import ModuleTestCase, function, ifcalls, infotable_handle
import collections, curry, os

def applies(iobj, modules=None):
  '''
  The apply calls under ``iobj``: the calls of Prelude.apply and of its
  aliases (Prelude.$) with two arguments (analysis.is_apply).  ``modules``
  resolves the aliases; by default, the modules of the interpreter.
  '''
  if modules is None:
    modules = curry.getInterpreter().modules
  found = []
  def visitor(node, **kwds):
    if analysis.is_apply(node, modules):
      found.append(node)
  icurry.visit.visit(visitor, iobj)
  return found

def known_applies(iobj, modules):
  '''The apply calls under ``iobj`` whose head is known.'''
  return [
      iapply for iapply in applies(iobj, modules)
             if analysis.partial_head(iapply.exprs[0], modules) is not None
    ]

def alias_of_apply(name, modulename='Prelude'):
  '''An IFunction of the fixture, ``name x y = apply x y``.'''
  block = types.IBlock(
      [types.IVarDecl(1), types.IVarDecl(2)]
    , [ types.IVarAssign(1, types.IVarAccess(0, [0]))
      , types.IVarAssign(2, types.IVarAccess(0, [1]))
      ]
    , types.IReturn(
          types.IFCall(analysis.APPLY, [types.IVar(1), types.IVar(2)])
        )
    )
  return types.IFunction(
      '%s.%s' % (modulename, name), 2, body=types.IFuncBody(block)
    , modulename=modulename
    )

def partials(iobj):
  '''The partial function calls under ``iobj``, as (name, missing, nargs).'''
  found = []
  def visitor(node, **kwds):
    if type(node) is types.IFPCall:
      found.append((node.symbolname, node.missing, len(node.exprs)))
  icurry.visit.visit(visitor, iobj)
  return found

def passkey():
  return '%s.opt.saturate_applies' % curry.flags['backend']

def nullary(name, expr):
  '''A nullary function of module M that returns ``expr``.'''
  return function(name, 0, [], types.IReturn(expr))


class TestPartialHeadAnalysis(cytest.TestCase):
  '''The analysis on hand-built ICurry.'''

  def setUp(self):
    # f x y = x + y; g = f; g1 = f 1; k = g; a = b; b = a; w x = f x
    self.f = function('f', 2, [(1, [0]), (2, [1])], types.IReturn(
        types.IFCall('Prelude.plusInt', [types.IVar(1), types.IVar(2)])
      ))
    self.g = nullary('g', types.IFPCall('M.f', 2, []))
    self.g1 = nullary(
        'g1', types.IFPCall('M.f', 1, [types.ILit(types.IInt(1))])
      )
    self.k = nullary('k', types.IFCall('M.g', []))
    self.a = nullary('a', types.IFCall('M.b', []))
    self.b = nullary('b', types.IFCall('M.a', []))
    self.w = function('w', 1, [(1, [0])], types.IReturn(
        types.IFPCall('M.f', 1, [types.IVar(1)])
      ))
    # data T = C Int Int | N; mk = C
    self.mk = nullary('mk', types.ICPCall('M.C', 2, []))
    itype = types.IDataType(
        'M.T', [types.IConstructor('M.C', 2), types.IConstructor('M.N', 0)]
      )
    # h = g 1 (an apply in the body); ap = apply; app f x = f x;
    # big x1 .. x10 = x1
    self.h = nullary('h', types.IFCall(
        analysis.APPLY, [types.IFCall('M.g', []), types.ILit(types.IInt(1))]
      ))
    self.ap = nullary('ap', types.IFPCall(analysis.APPLY, 2, []))
    self.app = alias_of_apply('app', 'M')
    self.big = function('big', 10, [(1, [0])], types.IReturn(types.IVar(1)))
    # The Prelude of the fixture: apply, and $ as an alias of it.
    prelude = types.IModule('Prelude', [], [], [
        types.IFunction(
            analysis.APPLY, 2, body=types.IExternal(analysis.APPLY)
          , modulename='Prelude'
          )
      , alias_of_apply('$')
      ])
    self.modules = {
        'M': types.IModule(
            'M', [], [itype]
          , [ self.f, self.g, self.g1, self.k, self.a, self.b, self.w, self.mk
            , self.h, self.ap, self.app, self.big
            ]
          )
      , 'Prelude': prelude
      }

  def head(self, expr):
    return analysis.partial_head(expr, self.modules)

  def test_partial_application(self):
    '''A partial application of known arity is a fresh copy of itself.'''
    expr = types.IFPCall('M.f', 1, [types.ILit(types.IInt(1))])
    found = self.head(expr)
    self.assertEqual(found, expr)
    self.assertIsNot(found, expr)
    self.assertIsNot(found.exprs[0], expr.exprs[0])

  def test_arity_disagrees(self):
    '''The missing count must agree with the function table.'''
    self.assertIsNone(self.head(types.IFPCall('M.f', 1, [])))
    self.assertIsNone(self.head(types.IFPCall('M.f', 3, [])))
    self.assertIsNone(self.head(
        types.IFPCall('M.f', 0, [types.IVar(1), types.IVar(2)])
      ))
    # The function must be loaded.
    self.assertIsNone(self.head(types.IFPCall('M.x', 1, [])))
    self.assertIsNone(self.head(types.IFPCall('N.f', 2, [])))

  def test_nullary_function(self):
    '''A call without arguments of a nullary function unfolds to its body.'''
    self.assertEqual(
        self.head(types.IFCall('M.g', [])), types.IFPCall('M.f', 2, [])
      )
    self.assertEqual(
        self.head(types.IFCall('M.g1', []))
      , types.IFPCall('M.f', 1, [types.ILit(types.IInt(1))])
      )
    # Through another nullary function.
    self.assertEqual(
        self.head(types.IFCall('M.k', [])), types.IFPCall('M.f', 2, [])
      )
    # A function with parameters is not unfolded.
    self.assertIsNone(self.head(types.IFCall('M.w', [])))

  def test_constructor(self):
    '''A partial application of a constructor takes the constructor's arity.'''
    self.assertEqual(
        self.head(types.ICPCall('M.C', 1, [types.IVar(1)]))
      , types.ICPCall('M.C', 1, [types.IVar(1)])
      )
    self.assertEqual(
        self.head(types.IFCall('M.mk', [])), types.ICPCall('M.C', 2, [])
      )
    self.assertIsNone(self.head(types.ICPCall('M.C', 2, [types.IVar(1)])))
    self.assertIsNone(self.head(types.ICPCall('M.N', 1, [])))
    self.assertIsNone(self.head(types.ICPCall('M.X', 1, [])))
    self.assertIs(
        analysis.lookup_constructor('M.C', self.modules)
      , self.modules['M'].types['T'].constructors[0]
      )
    self.assertIsNone(analysis.lookup_constructor('M.f', self.modules))
    self.assertIsNone(analysis.lookup_constructor('N.C', self.modules))
    self.assertIs(analysis.lookup_symbol('M.f', self.modules), self.f)
    self.assertEqual(analysis.lookup_symbol('M.C', self.modules).arity, 2)

  def test_not_known(self):
    cases = {
        'variable'   : types.IVar(1)
      , 'path'       : types.IVarAccess(1, [0])
      , 'literal'    : types.ILit(types.IInt(1))
      , 'with args'  : types.IFCall('M.w', [types.IVar(1)])
      , 'saturated'  : types.IFCall('M.f', [types.IVar(1), types.IVar(2)])
      , 'constructor': types.ICCall('M.N', [])
      , 'choice'     : types.IOr(
            types.IFPCall('M.f', 2, []), types.IFPCall('M.f', 2, [])
          )
      , 'unknown'    : types.IFCall('M.x', [])
      , 'cycle'      : types.IFCall('M.a', [])
      }
    for name, expr in cases.items():
      self.assertIsNone(self.head(expr), name)

  def test_apply_in_head_position(self):
    '''
    An apply whose head is known is known as well: the body of a nullary
    function the pass has not rewritten yet, a partial application of apply
    (ap = apply), and a call of $, the Prelude's alias of apply.  A user
    alias of apply is not an apply.
    '''
    one, two = types.ILit(types.IInt(1)), types.ILit(types.IInt(2))
    f1 = types.IFPCall('M.f', 1, [one])
    g = types.IFCall('M.g', [])
    self.assertEqual(self.head(types.IFCall(analysis.APPLY, [g, one])), f1)
    self.assertEqual(self.head(types.IFCall('M.h', [])), f1)
    # Two arguments saturate f: the chain is a call, not a partial.
    chain = types.IFCall(
        analysis.APPLY, [types.IFCall(analysis.APPLY, [g, one]), two]
      )
    self.assertIsNone(self.head(chain))
    call = analysis.saturate(chain, self.modules)
    self.assertEqual(call, types.IFCall('M.f', [one, two]))
    # The argument of the apply is shared; the head is a copy.
    self.assertIs(call.exprs[-1], two)
    self.assertIsNot(call.exprs[0], one)
    # ap = apply: a partial application of apply, saturated again.
    ap = types.IFCall('M.ap', [])
    self.assertEqual(self.head(ap), types.IFPCall(analysis.APPLY, 2, []))
    via_ap = types.IFCall(analysis.APPLY, [ap, g])
    self.assertEqual(self.head(via_ap), types.IFPCall(analysis.APPLY, 1, [g]))
    self.assertEqual(
        analysis.saturate(
            types.IFCall(analysis.APPLY, [via_ap, one]), self.modules
          )
      , f1
      )
    # $ is the Prelude's alias of apply; app is the user's, and stays.
    dollar = types.IFCall('Prelude.$', [g, one])
    self.assertTrue(analysis.is_apply(dollar, self.modules))
    self.assertEqual(self.head(dollar), f1)
    app = types.IFCall('M.app', [g, one])
    self.assertEqual(
        analysis.resolve_alias('M.app', self.modules, 2), analysis.APPLY
      )
    self.assertFalse(analysis.is_apply(app, self.modules))
    self.assertIsNone(self.head(app))
    for expr in [
        types.IFCall('M.f', [one, two])         # not apply
      , types.IFCall(analysis.APPLY, [g])       # one argument
      , types.IFPCall(analysis.APPLY, 1, [g])   # a partial application
      , types.IFCall('M.w', [g, one])           # w has arity one
      , types.IFCall('Prelude.x', [g, one])     # not loaded
      ]:
      self.assertFalse(analysis.is_apply(expr, self.modules), str(expr))
    # $ counts while the Prelude defines it as an alias of apply.
    del self.modules['Prelude'].functions['$']
    self.assertFalse(analysis.is_apply(dollar, self.modules))
    # An unknown head stays unknown through the apply.
    unknown = types.IFCall(analysis.APPLY, [types.IVar(1), one])
    self.assertIsNone(self.head(unknown))
    self.assertIsNone(analysis.saturate(unknown, self.modules))

  def test_apply_depth(self):
    '''Applies in head position count against the depth as well.'''
    depth = analysis.MAX_UNFOLDING_DEPTH
    def chain(n):
      expr = types.IFPCall('M.big', 10, [])
      for i in range(n):
        expr = types.IFCall(
            analysis.APPLY, [expr, types.ILit(types.IInt(i))]
          )
      return expr
    args = [types.ILit(types.IInt(i)) for i in range(depth + 1)]
    self.assertEqual(
        self.head(chain(depth)), types.IFPCall('M.big', 10 - depth, args[:-1])
      )
    self.assertIsNone(self.head(chain(depth + 1)))
    self.assertEqual(
        analysis.partial_head(chain(depth + 1), self.modules, depth=depth + 1)
      , types.IFPCall('M.big', 9 - depth, args)
      )

  def test_unfolding_text(self):
    '''
    The text reads back every literal, a string included (the pass runs
    after replace_static_strings).  A text that does not read back as a
    partial application makes the function unknown, and nothing more.
    '''
    for partial in [
        types.IFPCall('M.f', 1, [types.ILit(types.IInt(1))])
      , types.IFPCall('M.f', 1, [types.IString('abc')])
      , types.IFPCall('M.f', 1, [types.ILit(types.IChar('x'))])
      , types.IFPCall('M.f', 1, [types.ILit(types.IFloat(1.5))])
      , types.ICPCall('M.C', 1, [types.IString('')])
      ]:
      text = analysis.unfolding_text(partial)
      self.assertEqual(icurry.json.loads(text), partial)
      self.assertEqual(analysis.unfolding_text(icurry.json.loads(text)), text)
    stub = function('s', 0, [], None, body=types.IFuncBody(types.IExempt()))
    self.modules['M'].functions['s'] = stub
    for text in [
        'not json', '[]', '{"__class__":"INoSuchClass"}'
      , '{"__class__":"IFPCall"}', '{"__class__":"IString"}'
      ]:
      stub.update_metadata({analysis.UNFOLDING_KEY: text})
      self.assertIsNone(analysis.unfolding(stub, self.modules), text)
      self.assertIsNone(self.head(types.IFCall('M.s', [])), text)

  def test_depth(self):
    '''A head is followed through a bounded number of nullary functions.'''
    depth = analysis.MAX_UNFOLDING_DEPTH
    chain = [nullary('c0', types.IFPCall('M.f', 2, []))]
    for i in range(1, depth + 2):
      chain.append(nullary('c%d' % i, types.IFCall('M.c%d' % (i - 1), [])))
    modules = {'M': types.IModule('M', [], [], [self.f] + chain)}
    partial = types.IFPCall('M.f', 2, [])
    # A call of c<i> unfolds i+1 nullary functions, c<i> to c0.
    self.assertEqual(
        analysis.partial_head(types.IFCall('M.c%d' % (depth - 1), []), modules)
      , partial
      )
    self.assertIsNone(
        analysis.partial_head(types.IFCall('M.c%d' % depth, []), modules)
      )
    self.assertEqual(
        analysis.partial_head(
            types.IFCall('M.c%d' % depth, []), modules, depth=depth + 1
          )
      , partial
      )

  def test_nullary_body(self):
    '''Only one return statement without declarations is unfolded.'''
    expr = types.IFPCall('M.f', 2, [])
    self.assertEqual(analysis.nullary_body(self.g), expr)
    self.assertIsNone(analysis.nullary_body(self.f))
    cases = {
        'variable' : function('v', 0, [(1, [0])], types.IReturn(expr))
      , 'case'     : function('c', 0, [], types.ICaseLit(
            1, [types.ILitBranch(types.IInt(0), types.IReturn(expr))]
          ))
      , 'external' : function('e', 0, [], None, body=types.IExternal('M.e'))
      , 'builtin'  : function('b', 0, [], None, body=types.IBuiltin())
      , 'exempt'   : function(
            'x', 0, [], None, body=types.IFuncBody(types.IExempt())
          )
      }
    for name, ifun in cases.items():
      self.assertIsNone(analysis.nullary_body(ifun), name)
    free = nullary('fr', expr)
    block = free.body.block
    free.body.block = types.IBlock([types.IFreeDecl(1)], [], block.stmt)
    self.assertIsNone(analysis.nullary_body(free))

  def test_metadata_speaks_first(self):
    '''A module loaded from its compiled form has no bodies: metadata speaks.
    '''
    expr = types.IFPCall('M.f', 1, [types.ILit(types.IInt(7))])
    text = analysis.unfolding_text(expr)
    self.assertEqual(icurry.json.loads(text), expr)
    stub = function('s', 0, [], None, body=types.IFuncBody(types.IExempt()))
    stub.update_metadata({analysis.UNFOLDING_KEY: text})
    self.modules['M'].functions['s'] = stub
    self.assertEqual(analysis.unfolding(stub, self.modules), expr)
    self.assertEqual(self.head(types.IFCall('M.s', [])), expr)
    # The metadata takes precedence over the body, and must hold a partial.
    g = nullary('g', types.IFPCall('M.f', 2, []))
    g.update_metadata({analysis.UNFOLDING_KEY: text})
    self.assertEqual(analysis.unfolding(g, self.modules), expr)
    other = nullary('o', types.IFPCall('M.f', 2, []))
    other.update_metadata({
        analysis.UNFOLDING_KEY: analysis.unfolding_text(
            types.IFCall('M.f', [types.IVar(1), types.IVar(2)])
          )
      })
    self.assertIsNone(analysis.unfolding(other, self.modules))


# The module of the structure and value tests.  f is not an alias, so a call
# of it stays a call of it.
CHAINS = '''
  f :: Int -> Int -> Int
  f x y = x * 10 + y
  g :: Int -> Int -> Int
  g = f
  g1 :: Int -> Int
  g1 = f 1
  exact :: Int
  exact = g 1 2
  under :: [Int]
  under = map (g 1) [1, 2]
  viaG1 :: Int
  viaG1 = g1 2
  addc :: Int -> Int -> Int
  addc x = \\y -> f x y
  h :: Int -> Int -> Int
  h = addc
  over :: Int
  over = h 1 2
  nested :: Int
  nested = g (g 1 2) 3
  twice :: (Int -> Int) -> Int -> Int
  twice k x = k (k x)
  viaTwice :: Int
  viaTwice = twice (g 1) 5
  withArgs :: Int -> Int -> Int
  withArgs x = f x
  viaWithArgs :: Int
  viaWithArgs = withArgs 1 2
  shared :: (Int, Int)
  shared = let p = g 1 in (p 2, p 3)
  mk :: Int -> Maybe Int
  mk = Just
  viaMk :: Maybe Int
  viaMk = mk 4
  mkVal :: Int
  mkVal = maybe 0 id (mk 5)
  pair :: Int -> Int -> (Int, Int)
  pair = (,)
  viaPair :: [(Int, Int)]
  viaPair = map (pair 1) [2, 3]
  '''

CHAIN_VALUES = {
    'exact': [12], 'under': [[11, 12]], 'viaG1': [12], 'over': [12]
  , 'nested': [123], 'viaTwice': [25], 'viaWithArgs': [12]
  , 'shared': [(12, 13)]
  , 'mkVal': [5], 'viaPair': [[(1, 2), (1, 3)]]
  }

# The module of the sharing tests (section 4.3 of the plan): a choice in an
# argument of a collapsed chain is built once, as before.
CHOICES = '''
  dup :: Int -> Int -> (Int, Int, Int)
  dup x y = (x, x, y)
  d :: Int -> Int -> (Int, Int, Int)
  d = dup
  choiceArg :: (Int, Int, Int)
  choiceArg = d (0 ? 1) 2
  dc :: Int -> (Int, Int, Int)
  dc = dup (0 ? 1)
  choiceHead :: ((Int, Int, Int), (Int, Int, Int))
  choiceHead = (dc 2, dc 3)
  sharedChoice :: ((Int, Int, Int), (Int, Int, Int))
  sharedChoice = let p = d (0 ? 1) in (p 2, p 3)
  '''

CHOICE_VALUES = {
    'choiceArg': [(0, 0, 2), (1, 1, 2)]
  , 'choiceHead': [
        ((0, 0, 2), (0, 0, 3)), ((0, 0, 2), (1, 1, 3))
      , ((1, 1, 2), (0, 0, 3)), ((1, 1, 2), (1, 1, 3))
      ]
  , 'sharedChoice': [((0, 0, 2), (0, 0, 3)), ((1, 1, 2), (1, 1, 3))]
  }

# The module of the order and alias tests: a use before the definitions, a
# nullary alias of apply, chains through $ and through a user alias of $,
# and string literals in the partial applications (replace_static_strings
# runs before the pass, so the unfolding of prefix holds an IString).
ORDER = '''
  main :: Int
  main = g 2 3
  g :: Int -> Int -> Int
  g = k 1
  k :: Int -> Int -> Int -> Int
  k = f
  f :: Int -> Int -> Int -> Int
  f x y z = x * 100 + y * 10 + z
  ap :: (a -> b) -> a -> b
  ap = apply
  viaAp :: Int
  viaAp = ap g 2 3
  dollar :: Int
  dollar = g 2 $ 3
  dollarVar :: (Int -> Int) -> Int -> Int
  dollarVar h x = h $ x
  viaDollarVar :: Int
  viaDollarVar = dollarVar (g 2) 3
  prefix :: String -> String
  prefix = (++) "abc"
  viaPrefix :: String
  viaPrefix = prefix "def"
  isVowel :: Char -> Bool
  isVowel = flip elem "aeiou"
  vowelA :: Bool
  vowelA = isVowel (chr 97)
  '''

ORDER_VALUES = {
    'main': [123], 'viaAp': [123], 'dollar': [123], 'viaDollarVar': [123]
  , 'viaPrefix': ['abcdef'], 'vowelA': [True]
  }


class ApplyTestCase(ModuleTestCase):
  '''ModuleTestCase with the unoptimized form of a module.'''

  def unoptimized(self, name):
    '''
    Imports the module ``name`` from its ICurry object with the key of the
    pass set, so the pass does not run on it, and the key of the inliner,
    which saturates a known head as well.  Returns the module object.
    '''
    imodule = self.load_icurry(name)
    imodule.update_metadata({
        passkey(): True, '%s.opt.inline_calls' % curry.flags['backend']: True
      })
    module = curry.import_(imodule, currypath=self.currypath)
    self.assertTrue(applies(imodule), 'the unoptimized form keeps its applies')
    return module

  def values(self, module, goal):
    return list(curry.eval(getattr(module, goal), converter='topython'))


class TestSaturateApplies(ApplyTestCase):
  '''The structure of the ICurry after the pass.'''

  def test_shapes(self):
    name = self.write('Chains', CHAINS)
    imodule = self.icurry_of(name)
    fn = imodule.functions
    f, g, g1, addc, withargs = (
        '%s.%s' % (name, s) for s in ('f', 'g', 'g1', 'addc', 'withArgs')
      )
    self.assertTrue(imodule.metadata[passkey()])
    # A chain that fits exactly is the saturated call.
    self.assertEqual(ifcalls(fn['exact']), [f])
    self.assertEqual(
        fn['exact'].body.block.stmt.expr
      , types.IFCall(f, [types.ILit(types.IInt(1)), types.ILit(types.IInt(2))])
      )
    # An under-saturated chain is a shorter partial application.
    self.assertEqual(partials(fn['under']), [(f, 1, 1)])
    self.assertNotIn(optimize.APPLY, ifcalls(fn['under']))
    # A nullary function that unfolds to a partial application with
    # arguments: the arguments come first.
    self.assertEqual(
        fn['viaG1'].body.block.stmt.expr
      , types.IFCall(f, [types.ILit(types.IInt(1)), types.ILit(types.IInt(2))])
      )
    # An over-saturated chain is the saturated call and the applies after it.
    self.assertEqual(ifcalls(fn['over']), [addc, optimize.APPLY])
    self.assertEqual(
        fn['over'].body.block.stmt.expr
      , types.IFCall(optimize.APPLY, [
            types.IFCall(addc, [types.ILit(types.IInt(1))])
          , types.ILit(types.IInt(2))
          ])
      )
    # A chain in an argument of a chain.
    self.assertEqual(ifcalls(fn['nested']), [f, f])
    self.assertFalse(applies(fn['nested']))
    # A variable head stays.
    self.assertEqual(len(applies(fn['twice'])), 2)
    # A head defined with arguments stays.
    self.assertEqual(ifcalls(fn['viaWithArgs']), [withargs, optimize.APPLY])
    # A head held in a variable stays, though the variable is bound to a
    # chain, which collapses on its own.
    self.assertEqual(len(applies(fn['shared'])), 2)
    for iapply in applies(fn['shared']):
      self.assertIsInstance(iapply.exprs[0], types.IVar)
    assigns = fn['shared'].body.block.assigns
    self.assertEqual(len(assigns), 1)
    self.assertEqual(
        assigns[0].expr, types.IFPCall(f, 1, [types.ILit(types.IInt(1))])
      )
    # A nullary function that unfolds to a partial application of a
    # constructor: the constructor node, or a shorter partial application.
    self.assertEqual(
        fn['viaMk'].body.block.stmt.expr
      , types.ICCall('Prelude.Just', [types.ILit(types.IInt(4))])
      )
    self.assertEqual(
        fn['viaPair'].body.block.stmt.expr.exprs[0]
      , types.ICPCall('Prelude.(,)', 1, [types.ILit(types.IInt(1))])
      )
    self.assertFalse(applies(fn['viaMk']) + applies(fn['viaPair']))
    self.assertEqual(
        fn['mk'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.ICPCall('Prelude.Just', 1, []))
      )
    # No apply with a known head remains in the module.
    self.assertFalse(known_applies(imodule, curry.getInterpreter().modules))
    # The nullary functions record what they unfold to; the others do not.
    self.assertEqual(
        fn['g'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.IFPCall(f, 2, []))
      )
    self.assertEqual(
        fn['g1'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(
            types.IFPCall(f, 1, [types.ILit(types.IInt(1))])
          )
      )
    self.assertEqual(
        fn['h'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.IFPCall(addc, 1, []))
      )
    for fname in 'f', 'addc', 'withArgs', 'exact', 'twice':
      self.assertNotIn(analysis.UNFOLDING_KEY, fn[fname].metadata, fname)

  def test_before_aliases(self):
    '''A collapsed chain that saturates an alias calls the target.'''
    name = self.write('AliasChain', '''
      plus :: Int -> Int -> Int
      plus x y = x + y
      p :: Int -> Int -> Int
      p = plus
      main :: Int
      main = p 1 2
      ''')
    imodule = self.icurry_of(name)
    self.assertEqual(ifcalls(imodule.functions['main']), ['Prelude.plusInt'])

  def test_order_and_aliases(self):
    '''
    A use before the definitions, a nullary alias of apply, and a chain
    through $ collapse alike.  A call of dollarVar, a user alias of $ and
    so of apply, stays for the pass; inline_aliases then makes an apply of
    it, on a known head.  The $ with a variable head inside dollarVar stays
    and becomes apply.  A string literal in an unfolding reads back.
    '''
    name = self.write('Order', ORDER)
    imodule = self.icurry_of(name)
    fn = imodule.functions
    f = '%s.f' % name
    args = [types.ILit(types.IInt(i)) for i in (1, 2, 3)]
    for goal in 'main', 'viaAp', 'dollar':
      self.assertEqual(
          fn[goal].body.block.stmt.expr, types.IFCall(f, args), goal
        )
    self.assertEqual(ifcalls(fn['dollarVar']), [optimize.APPLY])
    modules = curry.getInterpreter().modules
    self.assertEqual(
        analysis.resolve_alias('%s.dollarVar' % name, modules, 2)
      , optimize.APPLY
      )
    self.assertEqual(ifcalls(fn['viaDollarVar']), [optimize.APPLY])
    self.assertEqual(partials(fn['viaDollarVar']), [(f, 1, 2)])
    self.assertEqual(len(known_applies(fn['viaDollarVar'], modules)), 1)
    self.assertEqual(
        fn['g'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.IFPCall(f, 2, [args[0]]))
      )
    self.assertEqual(
        fn['ap'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.IFPCall(optimize.APPLY, 2, []))
      )
    self.assertEqual(
        fn['prefix'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(
            types.IFPCall('Prelude.++', 1, [types.IString('abc')])
          )
      )
    self.assertEqual(
        fn['viaPrefix'].body.block.stmt.expr
      , types.IFCall(
            'Prelude.++', [types.IString('abc'), types.IString('def')]
          )
      )
    is_vowel = analysis.partial_head(
        types.IFCall('%s.isVowel' % name, []), modules
      )
    self.assertEqual(is_vowel.exprs[-1], types.IString('aeiou'))
    self.assertFalse(applies(fn['vowelA']))
    # The apply that inline_aliases made of dollarVar is the one left.
    del fn['viaDollarVar']
    self.assertFalse(known_applies(imodule, modules))

  def test_choice_shapes(self):
    '''The choice of a collapsed chain is one node, written once.'''
    name = self.write('Choices', CHOICES)
    imodule = self.icurry_of(name)
    fn = imodule.functions
    dup = '%s.dup' % name
    self.assertEqual(ifcalls(fn['choiceArg']), [dup])
    self.assertFalse(applies(fn['choiceArg']))
    self.assertIsInstance(
        fn['choiceArg'].body.block.stmt.expr.exprs[0], types.IOr
      )
    # Each use of dc gets a copy of its body, as its step would build it.
    self.assertEqual(ifcalls(fn['choiceHead']), [dup, dup])
    self.assertFalse(applies(fn['choiceHead']))
    # The chain bound to p collapses; the applies of p stay.
    self.assertEqual(len(applies(fn['sharedChoice'])), 2)
    self.assertEqual(partials(fn['sharedChoice']), [(dup, 1, 1)])

  @cytest.hardreset
  def test_unfolding_across_modules(self):
    '''
    A nullary function of a module loaded from its compiled form is known
    through its metadata.  When the partial names a function of a module the
    caller does not import, the module joins the imports.  The inliner is
    off: it would inline f into main.
    '''
    self.compiled(inline_budget=0)
    base = self.write('Base', '''
      f :: Int -> Int -> Int
      f x y = x * 10 + y
      ''')
    middle = self.write('Middle', '''
      import %s
      g :: Int -> Int -> Int
      g = f
      prefix :: String -> String
      prefix = (++) "abc"
      ''' % base)
    top = self.write('Top', '''
      import %s
      main :: Int
      main = g 1 2
      viaPrefix :: String
      viaPrefix = prefix "def"
      ''' % middle)
    middle_module = self.import_(middle)
    g = getattr(middle_module, '.icurry').functions['g']
    self.assertNotIsInstance(g.body.block, types.IBlock)
    self.assertEqual(
        g.metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.IFPCall('%s.f' % base, 2, []))
      )
    # A string literal in the unfolding comes back through the record.
    prefix = getattr(middle_module, '.icurry').functions['prefix']
    self.assertEqual(
        icurry.json.loads(prefix.metadata[analysis.UNFOLDING_KEY])
      , types.IFPCall('Prelude.++', 1, [types.IString('abc')])
      )
    self.assertTrue(getattr(middle_module, '.icurry').metadata[passkey()])
    imodule = self.load_icurry(top)
    self.assertNotIn(base, imodule.imports)
    imports = imodule.imports
    curry.import_(imodule, currypath=self.currypath)
    self.assertEqual(ifcalls(imodule.functions['main']), ['%s.f' % base])
    self.assertEqual(ifcalls(imodule.functions['viaPrefix']), ['Prelude.++'])
    self.assertEqual(imodule.imports, imports + (base,))
    # The values, from a module of the same text imported by name.
    module = self.import_(self.write('Use', '''
      import %s
      main :: Int
      main = g 1 2
      viaPrefix :: String
      viaPrefix = prefix "def"
      ''' % middle))
    self.assertEqual(self.values(module, 'main'), [12])
    self.assertEqual(self.values(module, 'viaPrefix'), ['abcdef'])


class TestEvaluation(ApplyTestCase):
  '''Values and steps of the optimized program against the unoptimized one.'''

  @cytest.hardreset
  def test_values(self):
    programs = [
        ('Chains', CHAINS, CHAIN_VALUES), ('Order', ORDER, ORDER_VALUES)
      ]
    for stem, text, values in programs:
      optimized = self.import_(self.write(stem, text))
      for goal, expected in values.items():
        self.assertEqual(self.values(optimized, goal), expected, goal)
    # The unoptimized form is imported from its ICurry object: under
    # interpret 'off' it compiles on its first use (issue #102).
    for stem, text, values in programs:
      unoptimized = self.unoptimized(self.write(stem, text))
      for goal, expected in values.items():
        self.assertEqual(self.values(unoptimized, goal), expected, goal)

  @cytest.hardreset
  def test_choices(self):
    '''A choice in an argument of a collapsed chain: the same values, no more.
    '''
    optimized = self.import_(self.write('Choices', CHOICES))
    for goal, expected in CHOICE_VALUES.items():
      self.assertCountEqual(self.values(optimized, goal), expected, goal)
    unoptimized = self.unoptimized(self.write('Choices', CHOICES))
    for goal, expected in CHOICE_VALUES.items():
      self.assertCountEqual(self.values(unoptimized, goal), expected, goal)

  @cytest.hardreset
  def test_steps(self):
    '''
    A collapsed chain of two applies on a nullary function saves three
    rewrite steps: the function and the two applies.  Under the C++ backend
    the modules stay interpreted, so no background compile swaps the code
    of the unoptimized module.  The inliner is off: it would save the step
    of f as well.
    '''
    self.reload(interpret='new', inline_budget=0)
    optimized = self.import_(self.write('Chains', CHAINS))
    unoptimized = self.unoptimized(self.write('Chains', CHAINS))
    def steps(module, goal):
      values, count = self.steps(getattr(module, goal))
      self.assertEqual(values, CHAIN_VALUES[goal])
      return count
    self.assertEqual(
        steps(unoptimized, 'exact') - steps(optimized, 'exact'), 3
      )
    self.assertEqual(
        steps(unoptimized, 'viaG1') - steps(optimized, 'viaG1'), 2
      )
    # Nothing changes for a variable head.
    self.assertEqual(
        steps(unoptimized, 'viaWithArgs'), steps(optimized, 'viaWithArgs')
      )

  @cytest.hardreset
  def test_generated_code(self):
    '''The generated code builds the call and names neither apply nor g.'''
    self.compiled()
    name = self.write('Code', '''
      f :: Int -> Int -> Int
      f x y = x * 10 + y
      g :: Int -> Int -> Int
      g = f
      main :: Int
      main = g 1 2
      ''')
    module = self.import_(name)
    self.assertEqual(self.values(module, 'main'), [12])
    text = self.generated_text(name)
    self.assertIn(infotable_handle('%s.f' % name), text)
    self.assertNotIn(infotable_handle(optimize.APPLY), text)


class TestPrelude(cytest.TestCase):
  '''The Prelude: the installed one, and its ICurry as the toolchain reads it.
  '''

  IMPL_NE_INT = '_impl#/=#Prelude.Eq#Prelude.Int'
  UNFOLDING_NE_INT = types.IFPCall(
      'Prelude._def#/=#Prelude.Eq', 2
    , [types.IFPCall('Prelude._inst#Prelude.Eq#Prelude.Int', 1, [])]
    )

  def prelude_json(self):
    jsonfile = os.path.join(
        config.system_curry_path(), '.curry', config.intermediate_subdir()
      , 'Prelude.json.z'
      )
    return loadjson(jsonfile)

  def test_installed_prelude(self):
    '''
    The staged Prelude was compiled with the pass: its metadata names the
    unfoldings, and the modules that import it collapse their chains.
    '''
    interp = curry.getInterpreter()
    imodule = getattr(interp.prelude, '.icurry')
    self.assertTrue(imodule.metadata[passkey()])
    ne = imodule.functions[self.IMPL_NE_INT]
    self.assertEqual(
        ne.metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(self.UNFOLDING_NE_INT)
      )
    self.assertEqual(
        analysis.partial_head(
            types.IFCall('Prelude.' + self.IMPL_NE_INT, []), interp.modules
          )
      , self.UNFOLDING_NE_INT
      )
    for name in [
        'ltEqInt', 'plusInt', 'length', 'take', 'not', '_def#/=#Prelude.Eq'
      ]:
      self.assertNotIn(
          analysis.UNFOLDING_KEY, imodule.functions[name].metadata, name
        )
    goal = curry.compile('(3 /= 4, 3 /= 3, mod 7 3 /= 0)', 'expr')
    self.assertEqual(
        list(curry.eval(goal, converter='topython')), [(True, False, True)]
      )

  def test_prelude_source(self):
    '''
    The pass over the ICurry of the Prelude: no apply with a known head
    remains, and the chains on the instance methods become calls of the
    class defaults.
    '''
    imodule = self.prelude_json()
    modules = {'Prelude': imodule}
    before = applies(imodule, modules)
    known_before = known_applies(imodule, modules)
    self.assertGreaterEqual(len(known_before), 100)
    # chr $ ... and lex $ ...: chains through the alias of apply.
    self.assertIn('Prelude.$', [iapply.symbolname for iapply in known_before])
    interp = curry.getInterpreter()
    for ifun in imodule.functions.values():
      optimize.saturate_applies(interp, ifun, imodule, modules=modules)
    after = applies(imodule, modules)
    self.assertFalse(known_applies(imodule, modules))
    self.assertNotIn('Prelude.$', [iapply.symbolname for iapply in after])
    self.assertLess(len(after), len(before) - 200)
    # The heads that stay: a variable, a call with arguments, or a call of a
    # nullary function whose body is not a partial application.
    for iapply in after:
      head = iapply.exprs[0]
      if isinstance(head, (types.IVar, types.IVarAccess)):
        continue
      self.assertIsInstance(head, types.ICall, str(iapply))
      if not head.exprs:
        self.assertIs(type(head), types.IFCall, str(iapply))
        self.assertIsNone(
            analysis.unfolding(
                analysis.lookup_function(head.symbolname, modules), modules
              )
          , str(iapply)
          )
    self.assertEqual(imodule.imports, ())
    # userError = UserError: a chain on a constructor.
    self.assertEqual(
        imodule.functions['userError'].metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(types.ICPCall('Prelude.UserError', 1, []))
      )
    ne = imodule.functions[self.IMPL_NE_INT]
    self.assertEqual(
        ne.metadata[analysis.UNFOLDING_KEY]
      , analysis.unfolding_text(self.UNFOLDING_NE_INT)
      )
    # x === '(' in the Read instance of () was apply (apply (_impl#===) x) '('.
    reads = imodule.functions[
        '_impl#readsPrec#Prelude.Read#()._#lambda41._#lambda44_CASE0'
      ]
    self.assertIn('Prelude._impl#==#Prelude.Eq#Prelude.Char', ifcalls(reads))
    self.assertFalse(applies(reads))


class TestCompiledModules(cytest.TestCase):
  '''A module loaded from its compiled form.'''

  @cytest.hardreset
  def test_not_optimized_again(self):
    '''
    The compiled form of a module carries the keys of the passes that ran on
    it, so no pass runs again when it is loaded.  On the C++ backend the
    loader hands the metadata of the record on (backends.cxx.loader); before
    that, every pass ran over the bodiless functions of the Prelude at each
    import.  Under interpret 'all' the Prelude is loaded from its ICurry and
    the passes run: the test does not apply.
    '''
    if curry.flags['interpret'] == 'all':
      self.skipTest('the Prelude is interpreted from its ICurry')
    curry.reload()
    counts = collections.Counter()
    original = list(optimize.default_optimizers)
    def counting(stem, optimizer):
      def wrapper(interp, ifun, imodule):
        counts[stem % interp.backend.backend_name] += 1
        return optimizer(interp, ifun, imodule)
      return wrapper
    optimize.default_optimizers[:] = [
        (stem, counting(stem, optimizer)) for stem, optimizer in original
      ]
    try:
      interp = curry.getInterpreter()
      self.assertNotIn('Prelude', interp.modules)
      imodule = getattr(interp.prelude, '.icurry')
      self.assertEqual(dict(counts), {})
      backend = curry.flags['backend']
      for stem, _ in original:
        self.assertTrue(imodule.metadata[stem % backend], stem)
      self.assertTrue(imodule.metadata['%s.is_merged' % backend])
      # A module imported from its ICurry is optimized, once.
      goal = curry.compile('3 /= 4', 'expr')
      self.assertTrue(counts)
      self.assertEqual(list(curry.eval(goal, converter='topython')), [True])
    finally:
      optimize.default_optimizers[:] = original


class TestPrivateSymbols(ApplyTestCase):
  '''
  The copied body of a nullary function may name a private function of its
  module.  Both backends resolve it through the symbol table of that module.
  '''

  def test_interpreted_caller(self):
    '''
    showsPrec at Int and Float unfolds to showSigned on showIntLiteral and
    showFloatLiteral, private wrappers of primitives of the Prelude.  A
    module imported by name runs interpreted on the C++ backend (the flag
    interpret), so it names them through the symbol table.
    '''
    name = self.write('Private', '''
      negFloat :: String
      negFloat = showsPrec 11 (-2.5 :: Float) ""
      negInt :: String
      negInt = showsPrec 0 (-3 :: Int) ""
      viaShow :: String
      viaShow = show (Just (-3 :: Int))
      ''')
    imodule = self.icurry_of(self.write('Private', '''
      negInt :: String
      negInt = showsPrec 0 (-3 :: Int) ""
      '''))
    self.assertEqual(
        [c for c in ifcalls(imodule.functions['negInt']) if 'show' in c]
      , ['Prelude.showSigned']
      )
    self.assertIn(
        ('Prelude.showIntLiteral', 1, 0), partials(imodule.functions['negInt'])
      )
    module = self.import_(name)
    self.assertEqual(self.values(module, 'negFloat'), ['(-2.5)'])
    self.assertEqual(self.values(module, 'negInt'), ['-3'])
    self.assertEqual(self.values(module, 'viaShow'), ['Just (-3)'])


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
    # The heads are nullary functions of the Prelude, known through the
    # metadata of the installed Prelude once it is loaded.
    interp.prelude
    ne, mod = 'Prelude._def#/=#Prelude.Eq', 'Prelude._def#mod#Prelude.Integral'
    cases = [
        ('Queens10', 'safe', [ne, ne, ne])
      , ('Primes', 'isdivs', [mod, ne])
      ]
    for name, fname, defaults in cases:
      imodule = toolchain.loadcurry(plan, name, currypath)
      ifun = imodule.functions[fname]
      self.assertEqual(len(applies(ifun)), 2 * len(defaults))
      optimize.saturate_applies(interp, ifun, imodule)
      self.assertFalse(applies(ifun))
      calls = ifcalls(ifun)
      self.assertEqual([c for c in calls if c in (ne, mod)], defaults)
      self.assertNotIn('Prelude._impl#/=#Prelude.Eq#Prelude.Int', calls)
