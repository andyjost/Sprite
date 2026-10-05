'''
The signature table, item Y2 of the typed boundary (#51, epic #48).
``curry.typecheck.sigtable`` reads the type scheme of a symbol from the
FlatCurry interface of its module, on demand and by byte offset, recovers
the class context from the leading dictionary parameters, derives the
schemes of constructors from the ``Type`` entries, builds the instance map
from the ``_inst#Class#Type`` names, and prints a scheme in Curry syntax.
``symbol.signature`` is the printed scheme and ``symbol.scheme`` the object;
``interp.sigtable`` is the table; ``Interpreter.reset`` clears it.
'''
import cytest # from ./lib; must be first
from curry import cache
from curry.objects.handle import Handle
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import sigtable
from curry.utility.binding import binding
import curry, logging, os, re, time

logger = logging.getLogger(__name__)

# The Prelude interface, parsed in full once for the whole file.  The parse
# costs about a third of a second.
_PRELUDE = []

def prelude_prog():
  if not _PRELUDE:
    path = curry.getInterpreter().sigtable.interface_filename('Prelude')
    _PRELUDE.append(fc.load(path))
  return _PRELUDE[0]

def interface_entries(prog):
  '''The functions, types and constructors of a parsed interface, by name.'''
  funcs = {f.name[1]: f for f in prog.functions}
  types = {t.name[1]: t for t in prog.types}
  ctors = {}
  for t in prog.types:
    if isinstance(t, fc.Type):
      for c in t.constructors:
        ctors[c.name[1]] = (t, c)
    elif isinstance(t, fc.TypeNew):
      ctors[t.constructor.name[1]] = (t, t.constructor)
  return funcs, types, ctors

def has_dictionary(typeexpr):
  '''Whether a type holds a dictionary domain, () -> _Dict#C t.'''
  if isinstance(typeexpr, fc.FuncType):
    return sigtable.dict_predicate(typeexpr.domain) is not None \
        or has_dictionary(typeexpr.domain) or has_dictionary(typeexpr.range)
  if isinstance(typeexpr, fc.TCons):
    return any(has_dictionary(arg) for arg in typeexpr.args)
  if isinstance(typeexpr, fc.ForallType):
    return has_dictionary(typeexpr.typeexpr)
  return False

def compile_without_cache(text):
  '''
  Compiles a module from text with the ICurry cache off, so that the front
  end runs and writes the interface into the directory of the module.
  '''
  with binding(os.environ, 'SPRITE_CACHE_FILE', ''):
    cache.reset()
    try:
      return curry.compile(text)
    finally:
      cache.reset()

class TestSchemes(cytest.TestCase):
  '''The schemes of the Prelude and of the library modules.'''

  # The expected signatures.  The variables are named in the order of their
  # first occurrence in the type.
  SIGNATURES = {
      '+'                    : 'Num a => a -> a -> a'
    , 'show'                 : 'Show a => a -> [Char]'
    , 'fmap'                 : 'Functor c => (a -> b) -> c a -> c b'
    , '>>='                  : 'Monad a => a b -> (b -> a c) -> a c'
    , '=:='                  : 'Data a => a -> a -> Bool'
    , '?'                    : 'a -> a -> a'
    , 'unknown'              : 'Data a => a'
    , 'Just'                 : 'a -> Maybe a'
    , '[]'                   : '[a]'
    , '_inst#Prelude.Show#[]': 'Show a => () -> _Dict#Show [a]'
    , 'round'                : '(RealFrac a, Integral b) => a -> b'
    }

  def test_signatures(self):
    '''The printed schemes of the symbols named in the issue.'''
    for name, expected in self.SIGNATURES.items():
      symbol = curry.symbol('Prelude.' + name)
      self.assertEqual(symbol.signature, expected, name)
      self.assertEqual(str(symbol.scheme), expected, name)
      self.assertEqual(symbol.scheme.fullname, 'Prelude.' + name)

  def test_interface_text(self):
    '''
    The decoded schemes match the interface text: the FlatCurry type of each
    function and the argument types of each constructor, from a full parse.
    '''
    funcs, _, ctors = interface_entries(prelude_prog())
    for name in self.SIGNATURES:
      scheme = curry.symbol('Prelude.' + name).scheme
      if scheme.is_constructor:
        typedecl, cons = ctors[name]
        self.assertEqual(scheme.arity, cons.arity, name)
        self.assertEqual(scheme.typevars, tuple(typedecl.typevars), name)
        self.assertEqual(scheme.context, (), name)
        argtypes = []
        te = scheme.typeexpr
        while isinstance(te, fc.FuncType):
          argtypes.append(te.domain)
          te = te.range
        self.assertEqual(argtypes, cons.argtypes, name)
        self.assertEqual(
            te, fc.TCons(typedecl.name, [fc.TVar(i) for i, _ in typedecl.typevars])
          )
      else:
        func = funcs[name]
        self.assertEqual(scheme.flat_typeexpr, func.typeexpr, name)
        self.assertEqual(scheme.arity, func.arity, name)

  def test_context_and_arity(self):
    '''
    The dictionary parameters become the context.  A class method is a
    selector of arity 1 with no source parameters; ``=:=`` takes its Data
    dictionary first; an instance takes its context dictionaries first.
    '''
    plus = curry.symbol('Prelude.+').scheme
    self.assertEqual((plus.arity, plus.ndicts, plus.source_arity), (1, 1, 0))
    self.assertEqual(
        plus.context, (sigtable.Predicate('Prelude.Num', fc.TVar(0)),)
      )
    self.assertEqual(str(plus.context[0]), 'Num a')
    self.assertEqual(plus.typevars, ((0, fc.KStar),))
    self.assertFalse(plus.is_constructor)
    constreq = curry.symbol('Prelude.=:=').scheme
    self.assertEqual(
        (constreq.arity, constreq.ndicts, constreq.source_arity), (3, 1, 2)
      )
    inst = curry.symbol('Prelude._inst#Prelude.Show#[]').scheme
    self.assertEqual((inst.arity, inst.ndicts), (2, 1))
    fmap = curry.symbol('Prelude.fmap').scheme
    self.assertEqual(
        fmap.typevars
      , ((0, fc.KArrow(fc.KStar, fc.KStar)), (1, fc.KStar), (2, fc.KStar))
      )
    self.assertEqual(
        fmap.context, (sigtable.Predicate('Prelude.Functor', fc.TVar(0)),)
      )
    just = curry.symbol('Prelude.Just').scheme
    self.assertTrue(just.is_constructor)
    self.assertEqual((just.arity, just.ndicts), (1, 0))
    fromintegral = curry.symbol('Prelude.fromIntegral').scheme
    self.assertEqual(str(fromintegral), '(Integral a, Num b) => a -> b')
    self.assertEqual((fromintegral.arity, fromintegral.ndicts), (2, 2))

  def test_method_with_own_constraints(self):
    '''
    A class method with its own constraints has dictionaries after its own
    quantifier: round :: RealFrac a => forall b. Integral b => a -> b in the
    interface.  The context holds both, in the order the symbol takes them,
    and no dictionary stays in the type.
    '''
    for name in ['round', 'truncate', 'ceiling', 'floor']:
      scheme = curry.symbol('Prelude.' + name).scheme
      self.assertEqual(str(scheme), '(RealFrac a, Integral b) => a -> b', name)
      self.assertEqual(
          (scheme.arity, scheme.ndicts, scheme.source_arity), (1, 2, 0), name
        )
      self.assertEqual(
          [pred.classname for pred in scheme.context]
        , ['Prelude.RealFrac', 'Prelude.Integral']
        )
      self.assertEqual(len(scheme.typevars), 2, name)
    scheme = curry.symbol('Prelude.properFraction').scheme
    self.assertEqual(str(scheme), '(RealFrac a, Integral b) => a -> (b, a)')
    flat = scheme.flat_typeexpr
    self.assertIsInstance(flat, fc.ForallType)
    self.assertIsInstance(flat.typeexpr.range, fc.ForallType)
    # No function of the Prelude keeps a dictionary domain in its type,
    # apart from the lifted local functions (f._#lambdaN, f.g.N), whose
    # dictionaries lie between their parameters.
    iface = curry.getInterpreter().sigtable.interface('Prelude')
    local = re.compile(r'\._#|\.\d+(\.|$)')
    kept = [
        name for name in iface.function_names()
             if not local.search(name) and has_dictionary(iface.scheme(name).typeexpr)
      ]
    self.assertEqual(kept, [])

  def test_library_modules(self):
    '''Data.List and Control.SetFunctions find their interface.'''
    interp = curry.getInterpreter()
    for modname, symbol, expected in [
        ('Data.List', 'nub', 'Eq a => [a] -> [a]')
      , ('Data.List', '\\\\', 'Eq a => [a] -> [a] -> [a]')
      , ('Control.SetFunctions', 'set1', '(a -> b) -> a -> Values b')
      , ('Control.SetFunctions', 'Values', '[a] -> Values a')
      ]:
      module = curry.module(modname)
      iface = interp.sigtable.interface(module)
      self.assertIsNotNone(iface, modname)
      self.assertEqual(iface.name, modname)
      self.assertTrue(os.path.isfile(iface.path))
      self.assertEqual(
          iface.path, interp.sigtable.interface_filename(modname)
        )
      self.assertEqual(getattr(module, symbol).signature, expected)
    self.assertIn('Data.List', interp.sigtable.modules())
    self.assertIn('Control.SetFunctions', interp.sigtable.modules())
    # Hierarchical modules under two packages, with a newtype.
    curry.import_('Data.Functor.Identity')
    identity = curry.symbol('Data.Functor.Identity.Identity')
    self.assertEqual(identity.signature, 'a -> Identity a')
    self.assertTrue(identity.scheme.is_constructor)
    self.assertEqual(identity.scheme.arity, 1)
    self.assertEqual(curry.symbol('Data.Maybe.fromJust').signature, 'Maybe a -> a')

  def test_lookup_by_name(self):
    '''``lookup`` takes a fully-qualified name as well as a symbol.'''
    interp = curry.getInterpreter()
    scheme = interp.sigtable.lookup('Prelude.+')
    self.assertEqual(str(scheme), 'Num a => a -> a -> a')
    self.assertIs(scheme, curry.symbol('Prelude.+').scheme)
    with self.assertRaises(curry.SymbolLookupError):
      interp.sigtable.lookup('Prelude.noSuchSymbol')
    with self.assertRaises(curry.ModuleLookupError):
      interp.sigtable.interface('NoSuchModule')
    self.assertEqual(
        interp.sigtable.type_decl('Prelude.IO')
      , fc.Type(fc.prelude('IO'), fc.Public, [(0, fc.KStar)], [])
      )
    self.assertIsNone(interp.sigtable.type_decl('Prelude.NoSuchType'))

  def test_fundamental_symbols(self):
    '''
    The boxed literals Int, Char and Float have the nullary types as their
    schemes.  The other symbols of Sprite's own Prelude have none; a lifted
    case or let function has none.  Asking for one is an error only with
    ``required``.
    '''
    interp = curry.getInterpreter()
    for name in 'Int', 'Char', 'Float':
      symbol = curry.symbol('Prelude.' + name)
      self.assertEqual(symbol.signature, name)
      self.assertTrue(symbol.scheme.is_constructor)
      self.assertEqual(symbol.scheme.arity, 0)
      self.assertIsNone(symbol.scheme.flat_typeexpr)
    for name in 'IO', '->', '_biGenerator':
      symbol = curry.symbol('Prelude.' + name)
      self.assertIsNone(symbol.scheme, name)
      self.assertIsNone(symbol.signature, name)
      self.assertIsNone(interp.sigtable.lookup(symbol), name)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^no type for Prelude\._biGenerator: the FlatCurry interface \S+ has "
        r"no entry '_biGenerator'; use raw_expr$"
      ):
      interp.sigtable.lookup('Prelude._biGenerator', required=True)
    lifted = [
        name for name in Handle(curry.module('Prelude')).symbols
             if '_CASE' in name or '_LET' in name
      ]
    self.assertTrue(lifted)
    self.assertIsNone(curry.symbol('Prelude.' + lifted[0]).scheme)

  def test_bare_node(self):
    '''
    ``raw_expr`` and ``eval`` of an untyped expression never read the table.
    The typed ``expr`` (item Y7) reads the interface of the Prelude for the
    scheme of ``not``.
    '''
    interp = curry.getInterpreter()
    P = curry.import_('Prelude')
    self.assertEqual(interp.sigtable.modules(), [])
    goal = curry.raw_expr(curry.symbol('Prelude.not'), True)
    self.assertEqual(list(curry.eval(goal, converter='topython')), [False])
    self.assertEqual(interp.sigtable.modules(), [])
    goal = curry.expr(curry.symbol('Prelude.not'), True)
    self.assertEqual(interp.sigtable.modules(), ['Prelude'])
    self.assertEqual(list(curry.eval(goal, converter='topython')), [False])


class TestInstances(cytest.TestCase):
  '''The instance map from the ``_inst#Class#Type`` names.'''

  def test_prelude_instances(self):
    interp = curry.getInterpreter()
    table = interp.sigtable
    inst = table.instance('Prelude.Num', 'Prelude.Int')
    self.assertEqual(inst.fullname, 'Prelude._inst#Prelude.Num#Prelude.Int')
    self.assertEqual(inst.modulename, 'Prelude')
    self.assertEqual(inst.context, ())
    self.assertEqual(inst.head, fc.TCons(fc.prelude('Int'), []))
    self.assertEqual(str(inst.scheme), '() -> _Dict#Num Int')
    showlist = table.instance('Prelude.Show', '[]')
    self.assertEqual(
        showlist.context, (sigtable.Predicate('Prelude.Show', fc.TVar(0)),)
      )
    self.assertEqual(showlist.head, fc.TCons(fc.prelude('[]'), [fc.TVar(0)]))
    eqpair = table.instance('Prelude.Eq', '(,)')
    self.assertEqual(
        eqpair.context
      , ( sigtable.Predicate('Prelude.Eq', fc.TVar(1))
        , sigtable.Predicate('Prelude.Eq', fc.TVar(0))
        )
      )
    self.assertEqual(str(eqpair.scheme), '(Eq a, Eq b) => () -> _Dict#Eq (a, b)')
    self.assertIsNotNone(table.instance('Prelude.Monad', '(->)'))
    self.assertIsNone(table.instance('Prelude.Num', 'Prelude.Bool'))
    self.assertIn('Prelude.Float', table.instances_of('Prelude.Fractional'))
    self.assertNotIn('Prelude.Int', table.instances_of('Prelude.Fractional'))
    # The Prelude declares 124 instances.
    prelude_instances = [
        inst for inst in table.instances().values()
             if inst.modulename == 'Prelude'
      ]
    self.assertEqual(len(prelude_instances), 124)

  def test_loaded_modules(self):
    '''A module loaded later adds its instances on the next call.'''
    table = curry.getInterpreter().sigtable
    self.assertIsNone(
        table.instance('Prelude.Data', 'Control.SetFunctions.Values')
      )
    curry.module('Control.SetFunctions')
    inst = table.instance('Prelude.Data', 'Control.SetFunctions.Values')
    self.assertEqual(inst.modulename, 'Control.SetFunctions')
    self.assertEqual(
        str(inst.scheme), 'Data a => () -> _Dict#Data (Values a)'
      )

  def test_bad_names(self):
    '''A name outside the convention of curry-frontend 2.0.0 is an error.'''
    for name in ['_inst#M.C(Prelude.Int)', '_inst#M.C', '_inst##', 'inst#A#B']:
      with self.assertRaisesRegex(sigtable.InterfaceError, 'cannot read'):
        sigtable.parse_instance_name(name, 'M')
    self.assertEqual(
        sigtable.parse_instance_name('_inst#Prelude.Show#[]', 'Prelude')
      , ('Prelude.Show', '[]')
      )

  def test_frontend_check(self):
    '''The interface of the Prelude must hold _inst#Prelude.Num#Prelude.Int.'''
    iface = curry.getInterpreter().sigtable.interface('Prelude')
    sigtable.SignatureTable.check_frontend(iface)
    text = (
        b'Prog "Prelude" [] [] [Func ("Prelude","id") 1 Public (ForallType '
        b'[(0,KStar)] (FuncType (TVar 0) (TVar 0))) (Rule [] (Var 0))] []'
      )
    bad = sigtable.Interface('<text>', text)
    with self.assertRaisesRegex(
        sigtable.InterfaceError, 'no entry _inst#Prelude.Num#Prelude.Int'
      ):
      sigtable.SignatureTable.check_frontend(bad)


class TestInterface(cytest.TestCase):
  '''The index over one interface file.'''

  def check_against_full_parse(self, path):
    '''Every entry of the index decodes to the entry of a full parse.'''
    prog = fc.load(path)
    iface = sigtable.Interface(path)
    self.assertEqual(iface.name, prog.name)
    self.assertEqual(iface.imports, tuple(prog.imports))
    funcs, types, ctors = interface_entries(prog)
    self.assertEqual(set(iface.function_names()), set(funcs))
    self.assertEqual(set(iface.type_names()), set(types))
    self.assertEqual(set(iface.constructor_names()), set(ctors))
    for name, func in funcs.items():
      self.assertEqual(iface.function(name), func, name)
    for name, typedecl in types.items():
      self.assertEqual(iface.type_decl(name), typedecl, name)
    for name, (typedecl, cons) in ctors.items():
      self.assertEqual(iface.constructor(name), (typedecl, cons), name)
    self.assertIsNone(iface.function('no such name'))
    self.assertIsNone(iface.type_decl('no such name'))
    self.assertIsNone(iface.constructor('no such name'))
    return iface

  def test_index_agrees_with_full_parse(self):
    '''Data/Maybe.fint, Data/List.fint and the interface of the test module.'''
    interp = curry.getInterpreter()
    for modname in 'Data.Maybe', 'Data.List', 'SigTable':
      curry.import_(modname)
      self.check_against_full_parse(interp.sigtable.interface_filename(modname))

  def test_prelude_names(self):
    '''The index of the Prelude finds every entry of the full parse.'''
    iface = curry.getInterpreter().sigtable.interface('Prelude')
    funcs, types, ctors = interface_entries(prelude_prog())
    self.assertEqual(set(iface.function_names()), set(funcs))
    self.assertEqual(set(iface.type_names()), set(types))
    self.assertEqual(set(iface.constructor_names()), set(ctors))
    self.assertEqual(len(funcs), 1267)
    self.assertEqual(iface.function('(,)'), None)
    self.assertEqual(iface.constructor('(,)')[1], ctors['(,)'][1])
    self.assertEqual(iface.type_decl('_Dict#Ord'), types['_Dict#Ord'])
    self.assertEqual(len(iface.instance_names()), 124)

  def test_timing(self):
    '''
    Times the index of the Prelude interface and one lookup, once.  The
    numbers go to the log and to the issue; nothing is asserted about them.
    '''
    interp = curry.getInterpreter()
    path = interp.sigtable.interface_filename('Prelude')
    t0 = time.perf_counter()
    iface = sigtable.Interface(path)
    t1 = time.perf_counter()
    scheme = iface.scheme('+')
    t2 = time.perf_counter()
    curry.reset()
    t3 = time.perf_counter()
    cold = curry.symbol('Prelude.+').scheme
    t4 = time.perf_counter()
    warm = curry.symbol('Prelude.+').scheme
    t5 = time.perf_counter()
    logger.info(
        'Prelude.fint: index %.2f ms, one entry %.3f ms, cold lookup after '
        'reset %.3f ms, warm lookup %.3f ms'
      , (t1 - t0) * 1e3, (t2 - t1) * 1e3, (t4 - t3) * 1e3, (t5 - t4) * 1e3
      )
    self.assertEqual(str(scheme), 'Num a => a -> a -> a')
    self.assertEqual(str(cold), str(scheme))
    self.assertIs(warm, cold)

  def test_malformed(self):
    '''A file that is not an interface, and an entry that does not decode.'''
    with self.assertRaisesRegex(sigtable.InterfaceError, 'not a FlatCurry'):
      sigtable.Interface('<text>', b'Hello')
    text = (
        b'Prog "M" ["Prelude"] [] [Func ("M","f") 1 Public (FuncType (TVar 0)) '
        b'(Rule [] (Var 0))] []'
      )
    iface = sigtable.Interface('<text>', text)
    self.assertEqual(iface.imports, ('Prelude',))
    with self.assertRaisesRegex(sigtable.InterfaceError, 'cannot decode'):
      iface.function('f')

  def test_candidates(self):
    '''
    The search order of the interface file: the copies beside the ICurry
    file only.  The front end's own copy is never a candidate.
    '''
    from curry import config
    sub, front = config.intermediate_subdir(), config.frontend_subdir()
    self.assertEqual(
        sigtable.interface_candidates('/r/Data/List.curry', 'Data.List')
      , [ '/r/Data/.curry/%s/List.fint' % sub
        , '/r/.curry/%s/Data/List.fint' % sub
        ]
      )
    self.assertEqual(
        sigtable.interface_candidates('/r/M.curry', 'M')
      , ['/r/.curry/%s/M.fint' % sub]
      )
    for candidate in sigtable.interface_candidates('/r/Data/List.curry', 'Data.List'):
      self.assertNotIn(os.sep + front + os.sep, candidate)
    self.assertEqual(sigtable.module_root('/r/A/B', 'A.B.C'), '/r')
    self.assertEqual(sigtable.module_root('/r', 'M'), '/r')
    self.assertEqual(sigtable.module_root('/r/X', 'A.B'), '/r/X')
    self.assertIsNone(sigtable.find_interface('/no/such/dir/M.curry', 'M'))


class TestModules(cytest.TestCase):
  '''A test module, a dynamic module, and the reset.'''

  def test_test_module(self):
    '''The module SigTable under tests/data/curry.'''
    M = curry.import_('SigTable')
    interp = curry.getInterpreter()
    iface = interp.sigtable.interface(M)
    self.assertEqual(iface.name, 'SigTable')
    self.assertEqual(M.pretty.signature, 'Pretty a => a -> [Char]')
    self.assertEqual(M.prettyList.signature, 'Pretty a => [a] -> [Char]')
    self.assertEqual(M.twice.signature, 'Num a => a -> a')
    self.assertEqual(
        (M.twice.scheme.arity, M.twice.scheme.ndicts, M.twice.scheme.source_arity)
      , (2, 1, 1)
      )
    self.assertEqual(M.showTwice.signature, '(Num a, Show a) => a -> [Char]')
    self.assertEqual(M.showTwice.scheme.ndicts, 2)
    self.assertEqual(M.unsigned.signature, 'Num a => Maybe a')
    self.assertEqual(
        (M.unsigned.scheme.arity, M.unsigned.scheme.source_arity), (1, 0)
      )
    self.assertEqual(M.prettyMaybe.signature, 'Maybe Shape -> [Char]')
    self.assertEqual(M.prettyMaybe.scheme.arity, 0)
    self.assertEqual(M.Circle.signature, 'Float -> Shape')
    self.assertEqual(M.Rect.signature, 'Float -> Float -> Shape')
    self.assertEqual(M.Age.signature, 'Int -> Age')
    self.assertTrue(M.Age.scheme.is_constructor)
    hidden = curry.symbol('SigTable.hidden')
    self.assertEqual(hidden.signature, 'Int -> Int')
    default = curry.symbol('SigTable._def#prettyList#SigTable.Pretty')
    self.assertEqual(default.signature, 'Pretty a => [a] -> [Char]')
    self.assertEqual(default.scheme.arity, 2)
    # Names outside the Prelude and the own module are qualified.
    self.assertEqual(
        sigtable.show_scheme(M.Circle.scheme, qualify=True)
      , 'Float -> SigTable.Shape'
      )
    self.assertEqual(
        sigtable.show_scheme(M.pretty.scheme, module='Prelude')
      , 'SigTable.Pretty a => a -> [Char]'
      )
    self.assertEqual(
        sigtable.show_scheme(curry.symbol('Prelude.+').scheme, module='SigTable')
      , 'Num a => a -> a -> a'
      )
    # The instances of the module.
    shape = interp.sigtable.instance('SigTable.Pretty', 'SigTable.Shape')
    self.assertEqual(shape.fullname, 'SigTable._inst#SigTable.Pretty#SigTable.Shape')
    self.assertEqual(shape.context, ())
    maybe = interp.sigtable.instance('SigTable.Pretty', 'Prelude.Maybe')
    self.assertEqual(
        maybe.context, (sigtable.Predicate('SigTable.Pretty', fc.TVar(0)),)
      )
    self.assertEqual(
        str(maybe.scheme), 'Pretty a => () -> _Dict#Pretty (Maybe a)'
      )
    self.assertEqual(
        sigtable.show_scheme(maybe.scheme, qualify=True)
      , 'SigTable.Pretty a => () -> SigTable._Dict#Pretty (Maybe a)'
      )
    self.assertIsNotNone(interp.sigtable.instance('Prelude.Data', 'SigTable.Age'))

  def test_dynamic_module(self):
    '''
    A module compiled from text finds its interface in its own directory.
    Without the file, the symbols have no scheme, and the typed path gets
    the error that names the module and raw_expr.
    '''
    interp = curry.getInterpreter()
    M = compile_without_cache(
        'f :: Int -> Int\n'
        'f x = x + 1\n'
        'g = Just 5\n'
        'data T a = T a Bool\n'
      )
    tmpd = Handle(M).icurry.metadata['all.tmpd']
    path = interp.sigtable.interface_filename(M)
    self.assertTrue(path.startswith(tmpd + os.sep), path)
    self.assertEqual(M.f.signature, 'Int -> Int')
    self.assertEqual(M.g.signature, 'Num a => Maybe a')
    self.assertEqual(M.T.signature, 'a -> Bool -> T a')
    self.assertIs(M.f.scheme, M.f.scheme)
    for candidate in sigtable.interface_candidates(M.__file__, M.__name__):
      if os.path.isfile(candidate):
        os.remove(candidate)
    interp.sigtable.clear()
    self.assertIsNone(interp.sigtable.interface(M))
    self.assertIsNone(M.f.signature)
    self.assertIsNone(M.f.scheme)
    name = M.__name__
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^no type for %s\.f: no FlatCurry interface found; recompile %s or '
        r'use raw_expr$' % (name, name)
      ):
      interp.sigtable.lookup(M.f, required=True)

  def test_reset(self):
    '''Interpreter.reset clears the table.'''
    interp = curry.getInterpreter()
    table = interp.sigtable
    self.assertEqual(table.modules(), [])
    curry.symbol('Prelude.+').scheme
    curry.module('Data.List').nub.scheme
    table.instances()
    self.assertLessEqual({'Data.List', 'Prelude'}, set(table.modules()))
    curry.reset()
    self.assertIs(interp.sigtable, table)
    self.assertEqual(table.modules(), [])
    self.assertNotIn('Data.List', curry.modules)
    self.assertEqual(curry.symbol('Prelude.+').signature, 'Num a => a -> a -> a')
    self.assertEqual(table.modules(), ['Prelude'])
    self.assertIsNotNone(table.instance('Prelude.Num', 'Prelude.Int'))
    self.assertIsNone(table.instance('Prelude.Data', 'Control.SetFunctions.Values'))


class TestPrinter(cytest.TestCase):
  '''The printer of types and schemes.'''

  def test_show_type(self):
    P = fc.prelude
    a, b, c = fc.TVar(0), fc.TVar(1), fc.TVar(2)
    maybe = lambda t: fc.TCons(P('Maybe'), [t])
    show = sigtable.show_type
    self.assertEqual(show(a), 'a')
    self.assertEqual(show(fc.FuncType(a, fc.FuncType(b, c))), 'a -> b -> c')
    self.assertEqual(show(fc.FuncType(fc.FuncType(a, b), c)), '(a -> b) -> c')
    self.assertEqual(show(maybe(fc.FuncType(a, b))), 'Maybe (a -> b)')
    self.assertEqual(show(maybe(maybe(a))), 'Maybe (Maybe a)')
    self.assertEqual(show(maybe(fc.TCons(P('[]'), [a]))), 'Maybe [a]')
    self.assertEqual(show(fc.TCons(P('(,)'), [a, maybe(b)])), '(a, Maybe b)')
    self.assertEqual(show(fc.TCons(P('(,,)'), [a, b, c])), '(a, b, c)')
    self.assertEqual(show(fc.TCons(P('()'), [])), '()')
    self.assertEqual(show(fc.TCons(P('[]'), [])), '[]')
    self.assertEqual(show(fc.TCons(P('(->)'), [a])), '(->) a')
    self.assertEqual(show(fc.TCons(P('(->)'), [a, b])), 'a -> b')
    self.assertEqual(
        show(fc.TCons(P('Apply'), [fc.TCons(P('Apply'), [a, b]), c])), 'a b c'
      )
    self.assertEqual(
        show(fc.TCons(P('Apply'), [a, fc.TCons(P('Apply'), [b, c])])), 'a (b c)'
      )
    self.assertEqual(
        show(fc.ForallType([(1, fc.KStar)], fc.FuncType(b, a)))
      , 'forall a. a -> b'
      )
    self.assertEqual(
        show(fc.FuncType(fc.ForallType([(0, fc.KStar)], a), b))
      , '(forall a. a) -> b'
      )
    T = fc.TCons(('M', 'T'), [a])
    self.assertEqual(show(T), 'M.T a')
    self.assertEqual(show(T, module='M'), 'T a')
    self.assertEqual(show(fc.FuncType(b, a), names={1: 'x'}), 'x -> a')
    self.assertEqual(
        show(fc.FuncType(fc.TVar(26), fc.TVar(27))), 'a -> b'
      )
    self.assertEqual(
        [sigtable.typevar_name(i) for i in (0, 25, 26, 27, 52)]
      , ['a', 'z', 'a1', 'b1', 'a2']
      )
    with self.assertRaises(TypeError):
      show(fc.KStar)

  def test_show_scheme(self):
    P = fc.prelude
    a, b = fc.TVar(0), fc.TVar(1)
    num, show_ = sigtable.Predicate('Prelude.Num', a), sigtable.Predicate('Prelude.Show', b)
    scheme = sigtable.Scheme(
        'M', 'f', [(0, fc.KStar), (1, fc.KStar)], [num, show_]
      , fc.FuncType(b, a), 3, 2
      )
    self.assertEqual(str(scheme), '(Num b, Show a) => a -> b')
    self.assertEqual(repr(scheme), '<Scheme M.f :: (Num b, Show a) => a -> b>')
    self.assertEqual(scheme.source_arity, 1)
    only_context = sigtable.Scheme('M', 'g', [(0, fc.KStar)], [num], b, 1, 1)
    self.assertEqual(str(only_context), 'Num b => a')
    pred = sigtable.Predicate('M.C', fc.TCons(P('Maybe'), [a]))
    self.assertEqual(str(pred), 'M.C (Maybe a)')
    self.assertEqual(sigtable.show_predicate(pred, module='M'), 'C (Maybe a)')
    functor = curry.symbol('Prelude._Dict#Functor').signature
    self.assertEqual(
        functor
      , '(forall a b. (a -> b) -> c a -> c b) -> (forall a b. a -> c b -> c a)'
        ' -> _Dict#Functor c'
      )
