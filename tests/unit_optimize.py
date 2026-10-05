'''
Tests for the ICurry optimizer: the alias pass.

An alias is a function whose body is one call of another function on exactly
its own parameters, in order.  The pass inline_aliases replaces each saturated
call of an alias by a call of its target, through a chain of aliases and
across modules, and records the direct target of every alias in its metadata
(analysis.ALIAS_KEY).  The alias function itself stays.  The pass runs when a
module is loaded, so it reaches the generated code of both backends and
leaves the FlatCurry-to-ICurry translation alone.

The structure of the optimized ICurry is read from a module imported from its
ICurry object, which the passes change in place.  Values come from a module
imported by name, whose generated code is cached beside its source.  No
module is imported both ways: on the C++ backend a module imported from its
ICurry object cannot be loaded from a shared object later.
'''
import cytest # from ./lib; must be first
from curry import common, config, icurry, toolchain
from curry.backends.generic import compiler as generic_compiler
from curry.icurry import analysis, types
from curry.interpreter import optimize
from curry.toolchain import plans
from curry.toolchain._loadcurry import loadjson
import curry, itertools, os, shutil, tempfile, unittest

def ifcalls(iobj):
  '''The symbol names of the saturated function calls under ``iobj``.'''
  found = []
  def visitor(node, **kwds):
    if type(node) is types.IFCall:
      found.append(node.symbolname)
  icurry.visit.visit(visitor, iobj)
  return found

def ifpcalls(iobj):
  '''The symbol names of the partial function calls under ``iobj``.'''
  found = []
  def visitor(node, **kwds):
    if type(node) is types.IFPCall:
      found.append(node.symbolname)
  icurry.visit.visit(visitor, iobj)
  return found

def infotable_handle(symbolname):
  '''The name of the info table of ``symbolname`` in generated code.'''
  modulename, _, name = symbolname.partition('.')
  return generic_compiler.mangle(
      modulename.split('.') + [name], generic_compiler.INFO_TABLE
    )

def function(name, arity, assigns, stmt, body=None):
  '''An IFunction of module M with the given block, or with ``body``.'''
  if body is None:
    vardecls = [types.IVarDecl(vid) for vid, _ in assigns]
    assigns = [
        types.IVarAssign(vid, types.IVarAccess(0, list(path)))
            for vid, path in assigns
      ]
    body = types.IFuncBody(types.IBlock(vardecls, assigns, stmt))
  return types.IFunction('M.' + name, arity, body=body, modulename='M')

def call(name, *vids):
  return types.IReturn(
      types.IFCall('M.' + name, [types.IVar(vid) for vid in vids])
    )

class TestAliasAnalysis(cytest.TestCase):
  '''The alias test on hand-built ICurry.'''

  def test_alias(self):
    # f x y = g x y
    f = function('f', 2, [(1, [0]), (2, [1])], call('g', 1, 2))
    self.assertEqual(analysis.alias_target_of_body(f), 'M.g')
    self.assertEqual(analysis.alias_target(f), 'M.g')
    # The order of the declarations does not matter.
    f = function('f', 2, [(2, [1]), (1, [0])], call('g', 1, 2))
    self.assertEqual(analysis.alias_target_of_body(f), 'M.g')
    # f = g
    f = function('f', 0, [], call('g'))
    self.assertEqual(analysis.alias_target_of_body(f), 'M.g')

  def test_not_an_alias(self):
    cases = {
        'swapped'  : function('f', 2, [(1, [0]), (2, [1])], call('g', 2, 1))
      , 'dropped'  : function('f', 2, [(1, [0]), (2, [1])], call('g', 1))
      , 'repeated' : function('f', 1, [(1, [0])], call('g', 1, 1))
      , 'nested'   : function('f', 1, [(1, [0, 1])], call('g', 1))
      , 'literal'  : function(
            'f', 1, [(1, [0])]
          , types.IReturn(types.IFCall(
                'M.g', [types.IVar(1), types.ILit(types.IInt(1))]
              ))
          )
      , 'constructor': function(
            'f', 1, [(1, [0])]
          , types.IReturn(types.ICCall('M.C', [types.IVar(1)]))
          )
      , 'partial'  : function(
            'f', 1, [(1, [0])]
          , types.IReturn(types.IFPCall('M.g', 1, [types.IVar(1)]))
          )
      , 'variable' : function(
            'f', 1, [(1, [0])], types.IReturn(types.IVar(1))
          )
      , 'case'     : function(
            'f', 1, [(1, [0])]
          , types.ICaseLit(1, [types.ILitBranch(types.IInt(0), call('g', 1))])
          )
      , 'external' : function(
            'f', 1, [], None, body=types.IExternal('M.f')
          )
      , 'builtin'  : function('f', 1, [], None, body=types.IBuiltin())
      , 'exempt'   : function(
            'f', 1, [], None, body=types.IFuncBody(types.IExempt())
          )
      }
    for name, ifun in cases.items():
      self.assertIsNone(analysis.alias_target_of_body(ifun), name)
      self.assertIsNone(analysis.alias_target(ifun), name)
    # A free variable is not a parameter.
    f = function('f', 1, [(1, [0])], call('g', 1))
    block = f.body.block
    f.body.block = types.IBlock(
        list(block.vardecls) + [types.IFreeDecl(2)], block.assigns, block.stmt
      )
    self.assertIsNone(analysis.alias_target_of_body(f))

  def test_metadata_names_the_target(self):
    '''A module loaded from its compiled form has no bodies; the metadata speaks.'''
    f = function('f', 1, [], None, body=types.IFuncBody(types.IExempt()))
    f.update_metadata({analysis.ALIAS_KEY: 'M.g'})
    self.assertIsNone(analysis.alias_target_of_body(f))
    self.assertEqual(analysis.alias_target(f), 'M.g')

  def test_resolve(self):
    '''A chain of aliases ends at the function that does the work.'''
    f = function('f', 1, [(1, [0])], call('g', 1))
    g = function('g', 1, [(1, [0])], call('h', 1))
    h = function('h', 1, [(1, [0])], types.IReturn(types.IVar(1)))
    k = function('k', 2, [(1, [0]), (2, [1])], call('f', 1))
    modules = {'M': types.IModule('M', [], [], [f, g, h, k])}
    self.assertIs(analysis.lookup_function('M.g', modules), g)
    self.assertIsNone(analysis.lookup_function('M.x', modules))
    self.assertIsNone(analysis.lookup_function('N.g', modules))
    self.assertIsNone(analysis.lookup_function('M', modules))
    self.assertEqual(analysis.resolve_alias('M.f', modules, 1), 'M.h')
    self.assertEqual(analysis.resolve_alias('M.g', modules, 1), 'M.h')
    self.assertEqual(analysis.resolve_alias('M.h', modules, 1), 'M.h')
    # k is not an alias: it drops a parameter.
    self.assertEqual(analysis.resolve_alias('M.k', modules, 2), 'M.k')
    # A call that is not saturated, or of an unknown function, is left alone.
    self.assertEqual(analysis.resolve_alias('M.f', modules, 2), 'M.f')
    self.assertEqual(analysis.resolve_alias('N.f', modules, 1), 'N.f')
    # A chain stops before a target that is not loaded or has another arity.
    # The metadata takes precedence over the body.
    f2 = function('f2', 1, [(1, [0])], call('x', 1))
    f3 = function('f3', 1, [(1, [0])], call('f2', 1))
    f3.update_metadata({analysis.ALIAS_KEY: 'M.k'})
    modules = {'M': types.IModule('M', [], [], [f2, f3, k])}
    self.assertEqual(analysis.resolve_alias('M.f2', modules, 1), 'M.f2')
    self.assertEqual(analysis.resolve_alias('M.f3', modules, 1), 'M.f3')

  def test_cycle(self):
    '''A chain that closes on itself leaves the call alone.'''
    f = function('f', 1, [(1, [0])], call('g', 1))
    g = function('g', 1, [(1, [0])], call('f', 1))
    h = function('h', 1, [(1, [0])], call('f', 1))
    s = function('s', 1, [(1, [0])], call('s', 1))
    modules = {'M': types.IModule('M', [], [], [f, g, h, s])}
    self.assertEqual(analysis.resolve_alias('M.f', modules, 1), 'M.f')
    self.assertEqual(analysis.resolve_alias('M.g', modules, 1), 'M.g')
    self.assertEqual(analysis.resolve_alias('M.h', modules, 1), 'M.h')
    self.assertEqual(analysis.resolve_alias('M.s', modules, 1), 'M.s')


class ModuleTestCase(cytest.TestCase):
  '''A temporary source directory of Curry modules.'''
  # The C++ runtime keeps one entry per module name, so every module of these
  # tests gets a name of its own.
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-optimize-')
    # The imports of a module are found through the Curry path of the
    # interpreter.  tearDown resets it.
    curry.path.insert(0, self.tmpdir)
    self.currypath = list(curry.path)

  def tearDown(self):
    super().tearDown()
    shutil.rmtree(self.tmpdir, ignore_errors=True)

  def compiled(self):
    '''
    Reloads the interpreter with the flag ``interpret`` off.  A test that
    reads the generated code of a module, or needs a module loaded from its
    compiled form, calls this first: under the default of the flag (tiered)
    a module is interpreted and no code is generated for it.  The caller is
    decorated with cytest.hardreset, which restores the default.
    '''
    curry.reload({'interpret': 'off'})
    curry.path.insert(0, self.tmpdir)
    self.currypath = list(curry.path)

  def write(self, stem, text):
    '''
    Writes a Curry module with a new name that starts with ``stem``.  The
    text may name the module as %(name)s.  Returns the name.
    '''
    name = '%s%d' % (stem, next(self.counter))
    with open(os.path.join(self.tmpdir, name + '.curry'), 'w') as stream:
      stream.write(text % {'name': name})
    return name

  def load_icurry(self, name):
    '''The ICurry of the module ``name``, as the front end wrote it.'''
    plan = plans.makeplan(
        None, plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON
      )
    return toolchain.loadcurry(plan, name, self.currypath)

  def icurry_of(self, name):
    '''
    The ICurry of the module ``name`` after the passes ran.  The module is
    imported from its ICurry object, so the passes change that object in
    place.  Its code is not written to a file.
    '''
    imodule = self.load_icurry(name)
    curry.import_(imodule, currypath=self.currypath)
    return imodule

  def import_(self, name):
    '''Imports the module ``name`` by name: it is compiled and loaded.'''
    return curry.import_(name, currypath=self.currypath)

  def generated_text(self, name):
    '''The generated code of a module imported by name.'''
    suffix = '.py' if curry.flags['backend'] == 'py' else '.cpp'
    path = os.path.join(
        self.tmpdir, '.curry', config.intermediate_subdir(), name + suffix
      )
    return cytest.readfile(path)

  def steps(self, goal):
    '''The values and the rewrite steps of one evaluation of ``goal``.'''
    before = curry.stats()['steps']
    values = list(curry.eval(goal, converter='topython'))
    return values, curry.stats()['steps'] - before


class TestInlineAliases(ModuleTestCase):
  '''The structure of the ICurry after the pass.'''

  def test_chain_in_one_module(self):
    '''
    Calls follow a chain of aliases to its end.  Each alias records its
    direct target, after its own body was rewritten.
    '''
    name = self.write('Chain', '''
      f :: Int -> Int -> Int
      f x y = g x y
      g :: Int -> Int -> Int
      g x y = h x y
      h :: Int -> Int -> Int
      h x y = x + y
      k :: Int -> Int
      k n = f n 1
      main :: Int
      main = k 41
      ''')
    imodule = self.icurry_of(name)
    functions = imodule.functions
    for alias in 'f', 'g', 'h':
      self.assertEqual(
          functions[alias].metadata[analysis.ALIAS_KEY], 'Prelude.plusInt'
        )
      self.assertEqual(ifcalls(functions[alias]), ['Prelude.plusInt'])
    self.assertNotIn(analysis.ALIAS_KEY, functions['k'].metadata)
    self.assertEqual(ifcalls(functions['k']), ['Prelude.plusInt'])
    self.assertEqual(ifcalls(functions['main']), ['%s.k' % name])
    key = '%s.opt.inline_aliases' % curry.flags['backend']
    self.assertEqual(imodule.metadata[key], True)

  def test_not_aliases(self):
    '''A call of a function that is not an alias does not change.'''
    name = self.write('NotAlias', '''
      g :: Int -> Int -> Int
      g x y = if x == 0 then y else x
      swapped :: Int -> Int -> Int
      swapped x y = g y x
      literal :: Int -> Int
      literal x = g x 1
      repeated :: Int -> Int
      repeated x = g x x
      withCase :: Int -> Int
      withCase x = case x of
        0 -> g x x
        _ -> g x 1
      a :: Int -> Int -> Int
      a x y = swapped x y
      main :: [Int]
      main = [swapped 1 2, literal 0, repeated 3, withCase 0, a 5 6]
      ''')
    imodule = self.icurry_of(name)
    functions = imodule.functions
    for fname in 'g', 'swapped', 'literal', 'repeated', 'withCase':
      self.assertNotIn(analysis.ALIAS_KEY, functions[fname].metadata, fname)
    self.assertEqual(
        functions['a'].metadata[analysis.ALIAS_KEY], '%s.swapped' % name
      )
    self.assertCountEqual(
        ifcalls(functions['main'])
      , [ '%s.swapped' % name, '%s.literal' % name, '%s.repeated' % name
        , '%s.withCase' % name, '%s.swapped' % name
        ]
      )
    # The comparison of g is an alias of eqInt.
    self.assertIn('Prelude.eqInt', ifcalls(functions['g']))

  def test_partial_application_keeps_the_alias(self):
    '''Only a saturated call changes.  A partial application keeps its head.'''
    name = self.write('Partial', '''
      f :: Int -> Int -> Int
      f x y = x + y
      main :: [Int]
      main = map (f 1) [1, 2, 3]
      ''')
    imodule = self.icurry_of(name)
    main = imodule.functions['main']
    self.assertEqual(ifpcalls(main), ['%s.f' % name])
    self.assertNotIn('Prelude.plusInt', ifcalls(main))
    self.assertEqual(
        imodule.functions['f'].metadata[analysis.ALIAS_KEY], 'Prelude.plusInt'
      )

  def test_cycle(self):
    '''Aliases of each other leave every call alone, and the pass ends.'''
    name = self.write('Cycle', '''
      cf :: Int -> Int
      cf x = cg x
      cg :: Int -> Int
      cg x = cf x
      ch :: Int -> Int
      ch x = cf x
      ''')
    imodule = self.icurry_of(name)
    functions = imodule.functions
    self.assertEqual(ifcalls(functions['cf']), ['%s.cg' % name])
    self.assertEqual(ifcalls(functions['cg']), ['%s.cf' % name])
    self.assertEqual(ifcalls(functions['ch']), ['%s.cf' % name])
    self.assertEqual(
        functions['cf'].metadata[analysis.ALIAS_KEY], '%s.cg' % name
      )
    self.assertEqual(
        functions['cg'].metadata[analysis.ALIAS_KEY], '%s.cf' % name
      )

  def test_external_targets(self):
    '''
    The Prelude's instance methods for Int are aliases of externals.  A call
    of one becomes the call of the built-in that the alias would have made.
    '''
    name = self.write('Arith', '''
      tak :: Int -> Int -> Int -> Int
      tak x y z = if x <= y then z
                  else tak (tak (x-1) y z) (tak (y-1) z x) (tak (z-1) x y)
      ops :: Int -> Int -> [Int]
      ops x y = [x + y, x - y, x * y]
      main :: (Int, [Int], Bool, Bool)
      main = (tak 12 8 4, ops 7 3, 3 <= 4, 3 == 4)
      ''')
    imodule = self.icurry_of(name)
    calls = ifcalls(imodule)
    for target in [
        'Prelude.ltEqInt', 'Prelude.minusInt', 'Prelude.plusInt'
      , 'Prelude.timesInt', 'Prelude.eqInt'
      ]:
      self.assertIn(target, calls)
    self.assertFalse([c for c in calls if c.startswith('Prelude._impl#')])

  @cytest.hardreset
  def test_target_module_joins_the_imports(self):
    '''
    When the target lives in a module the caller does not import, the module
    joins the imports.  The alias is read from the metadata of a module
    loaded from its compiled form.
    '''
    self.compiled()
    base = self.write('Base', '''
      g :: Int -> Int
      g x = x * 2
      ''')
    middle = self.write('Middle', '''
      import %s
      f :: Int -> Int
      f x = g x
      ''' % base)
    top = self.write('Top', '''
      import %s
      main :: Int
      main = f 21
      ''' % middle)
    middle_module = self.import_(middle)
    # The module was loaded from its compiled form: no bodies, but metadata.
    f = getattr(middle_module, '.icurry').functions['f']
    self.assertNotIsInstance(f.body.block, types.IBlock)
    self.assertEqual(f.metadata[analysis.ALIAS_KEY], '%s.g' % base)
    imodule = self.load_icurry(top)
    self.assertNotIn(base, imodule.imports)
    imports = imodule.imports
    curry.import_(imodule, currypath=self.currypath)
    self.assertEqual(ifcalls(imodule.functions['main']), ['%s.g' % base])
    self.assertEqual(imodule.imports, imports + (base,))


class TestEvaluation(ModuleTestCase):
  '''Modules compiled by name: their values, their steps, their code.'''

  @cytest.hardreset
  def test_values(self):
    # The test reads the generated code.
    self.compiled()
    name = self.write('Values', '''
      tak :: Int -> Int -> Int -> Int
      tak x y z = if x <= y then z
                  else tak (tak (x-1) y z) (tak (y-1) z x) (tak (z-1) x y)
      g :: Int -> Int -> Int
      g x y = if x == 0 then y else x
      swapped :: Int -> Int -> Int
      swapped x y = g y x
      a :: Int -> Int -> Int
      a x y = swapped x y
      f :: Int -> Int -> Int
      f x y = x + y
      main :: (Int, [Int], [Int], Bool)
      main = (tak 12 8 4, [swapped 1 2, g 0 1, a 5 6], map (f 1) [1, 2], 3 <= 4)
      ''')
    module = self.import_(name)
    self.assertEqual(
        list(curry.eval(module.main, converter='topython'))
      , [(5, [2, 1, 6], [2, 3], True)]
      )
    functions = getattr(module, '.icurry').functions
    self.assertEqual(functions['f'].metadata[analysis.ALIAS_KEY], 'Prelude.plusInt')
    self.assertEqual(functions['a'].metadata[analysis.ALIAS_KEY], '%s.swapped' % name)
    self.assertNotIn(analysis.ALIAS_KEY, functions['swapped'].metadata)
    # The code calls the externals, not the instance methods.
    text = self.generated_text(name)
    for target in 'Prelude.ltEqInt', 'Prelude.minusInt', 'Prelude.plusInt':
      self.assertIn(infotable_handle(target), text)
    for alias in [
        'Prelude._impl#<=#Prelude.Ord#Prelude.Int'
      , 'Prelude._impl#-#Prelude.Num#Prelude.Int'
      , 'Prelude._impl#+#Prelude.Num#Prelude.Int'
      , 'Prelude._impl#==#Prelude.Eq#Prelude.Int'
      ]:
      self.assertNotIn(infotable_handle(alias), text)

  def test_steps(self):
    '''A call through an alias costs the steps of a direct call.'''
    name = self.write('Steps', '''
      f :: Int -> Int -> Int
      f x y = x + y
      s :: Int -> Int -> Int
      s x y = y + x
      viaAlias :: Int
      viaAlias = f 1 2
      direct :: Int
      direct = 1 + 2
      swapped :: Int
      swapped = s 1 2
      ''')
    module = self.import_(name)
    values, via_alias = self.steps(module.viaAlias)
    self.assertEqual(values, [3])
    values, direct = self.steps(module.direct)
    self.assertEqual(values, [3])
    values, swapped = self.steps(module.swapped)
    self.assertEqual(values, [3])
    self.assertEqual(via_alias, direct)
    self.assertEqual(swapped, direct + 1)

  def test_monadic_target(self):
    '''An alias of a monadic function is monadic, and so is its caller.'''
    name = self.write('Monadic', '''
      p :: String -> IO ()
      p s = putStr s
      q :: IO ()
      q = p ""
      ''')
    module = self.import_(name)
    for fname in 'p', 'q':
      info = getattr(module, fname).info
      self.assertTrue(info.flags & common.F_MONADIC, fname)
    self.assertEqual(
        getattr(module, '.icurry').functions['p'].metadata[analysis.ALIAS_KEY]
      , 'Prelude.putStr'
      )
    self.assertEqual(list(curry.eval(module.q, converter='topython')), [()])

  @cytest.hardreset
  def test_private_target_across_modules(self):
    '''
    A call from another module may end at a function that is private to the
    module of the alias.  Both backends resolve it.
    '''
    self.compiled()
    private = self.write('Private', '''
      module %(name)s (f) where
      f :: Bool -> Int -> Int
      f x y = g x y
      g :: Bool -> Int -> Int
      g True y = y
      g False _ = 0
      ''')
    caller = self.write('Caller', '''
      import %s
      main :: Int
      main = f True 7
      ''' % private)
    module = self.import_(caller)
    self.assertEqual(list(curry.eval(module.main, converter='topython')), [7])
    text = self.generated_text(caller)
    self.assertIn(infotable_handle('%s.g' % private), text)
    self.assertNotIn(infotable_handle('%s.f' % private), text)

  @cytest.hardreset
  def test_linked_against_the_target_module(self):
    '''The module of a target joins the imports; the code loads and links.'''
    self.compiled()
    base = self.write('Base', '''
      g :: Int -> Int
      g x = x * 2
      ''')
    middle = self.write('Middle', '''
      import %s
      f :: Int -> Int
      f x = g x
      ''' % base)
    top = self.write('Top', '''
      import %s
      main :: Int
      main = f 21
      ''' % middle)
    module = self.import_(top)
    self.assertEqual(list(curry.eval(module.main, converter='topython')), [42])
    self.assertIn(base, getattr(module, '.icurry').imports)
    text = self.generated_text(top)
    self.assertIn(infotable_handle('%s.g' % base), text)
    self.assertNotIn(infotable_handle('%s.f' % middle), text)


class TestPreludeAliases(cytest.TestCase):
  '''The aliases of the installed Prelude.'''
  ALIASES = {
      '_impl#==#Prelude.Eq#Prelude.Int'       : 'Prelude.eqInt'
    , '_impl#==#Prelude.Eq#Prelude.Char'      : 'Prelude.eqChar'
    , '_impl#==#Prelude.Eq#Prelude.Float'     : 'Prelude.eqFloat'
    , '_impl#<=#Prelude.Ord#Prelude.Int'      : 'Prelude.ltEqInt'
    , '_impl#<=#Prelude.Ord#Prelude.Char'     : 'Prelude.ltEqChar'
    , '_impl#<=#Prelude.Ord#Prelude.Float'    : 'Prelude.ltEqFloat'
    , '_impl#+#Prelude.Num#Prelude.Int'       : 'Prelude.plusInt'
    , '_impl#-#Prelude.Num#Prelude.Int'       : 'Prelude.minusInt'
    , '_impl#*#Prelude.Num#Prelude.Int'       : 'Prelude.timesInt'
    , '_impl#+#Prelude.Num#Prelude.Float'     : 'Prelude.plusFloat'
    , '_impl#-#Prelude.Num#Prelude.Float'     : 'Prelude.minusFloat'
    , '_impl#*#Prelude.Num#Prelude.Float'     : 'Prelude.timesFloat'
    , '_impl#/#Prelude.Fractional#Prelude.Float': 'Prelude.divFloat'
    , '_impl#fromInt#Prelude.Num#Prelude.Float': 'Prelude.intToFloat'
    # Through _impl#fromInt#Prelude.Num#Prelude.Float.
    , '_impl#toFloat#Prelude.Real#Prelude.Int': 'Prelude.intToFloat'
    }

  def test_installed_prelude(self):
    '''
    The staged Prelude was compiled with the pass: its metadata names the
    targets, and its own code evaluates.
    '''
    imodule = getattr(curry.getInterpreter().prelude, '.icurry')
    for name, target in self.ALIASES.items():
      self.assertEqual(
          imodule.functions[name].metadata.get(analysis.ALIAS_KEY), target, name
        )
    for name in 'ltEqInt', 'plusInt', 'length', 'take', 'not':
      self.assertNotIn(analysis.ALIAS_KEY, imodule.functions[name].metadata)
    goal = curry.compile('length (take 3 [1 ..])', 'expr')
    self.assertEqual(list(curry.eval(goal, converter='topython')), [3])

  def test_prelude_source(self):
    '''
    The pass on the ICurry of the Prelude as the toolchain reads it: length
    and take call plusInt and ltEqInt instead of the instance methods.  The
    targets are resolved through the metadata of the loaded Prelude.
    '''
    jsonfile = os.path.join(
        config.system_curry_path(), '.curry', config.intermediate_subdir()
      , 'Prelude.json.z'
      )
    imodule = loadjson(jsonfile)
    imports = imodule.imports
    interp = curry.getInterpreter()
    length = imodule.functions['length']
    take = imodule.functions['take']
    self.assertIn('Prelude._impl#+#Prelude.Num#Prelude.Int', ifcalls(length))
    self.assertIn('Prelude._impl#<=#Prelude.Ord#Prelude.Int', ifcalls(take))
    optimize.inline_aliases(interp, length, imodule)
    optimize.inline_aliases(interp, take, imodule)
    self.assertCountEqual(ifcalls(length), ['Prelude.plusInt', 'Prelude.length'])
    self.assertCountEqual(
        ifcalls(take), ['Prelude.take_COMPLEXCASE0', 'Prelude.ltEqInt']
      )
    self.assertEqual(imodule.imports, imports)
