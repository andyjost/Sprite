'''
Goals without type signatures, item Y4 of the typed boundary (#53, epic #48;
fixes #39, and #35 in its refuse-to-save form).

A goal whose scheme has class constraints is a function whose leading
parameters are dictionaries.  ``curry.typecheck.defaulting`` applies the
table of the PAKCS REPL to the constraints, and ``curry.typecheck.goals``
applies the goal to one base instance per constraint, in the order of the
scheme.  One path serves ``curry.eval`` of a module function,
``curry.compile(mode='expr')`` without ``exprtype``, ``:eval`` and ``:type``
of the REPL, ``sprite-exec -g``, and saved modules on the Python backend.
The text route lifts the variables of a trailing ``where x free`` to
parameters, as the REPL does, and reports the bindings of the variables
whose type is absent from the result type; a variable whose type occurs in
the result type is left in the value.  ``compile(mode='expr')`` returns a
node; the goal objects stay inside ``curry.eval``.
'''
import cytest # from ./lib; must be first
from curry import config, inspect
from curry.interpreter import compile as compilemod
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import defaulting, goals, sigtable
from curry.typecheck.defaulting import DefaultingError, ORACLE_SENTENCE
from curry.typecheck.goals import Bindings, Goal
from io import StringIO
import curry, os, re, subprocess, sys, tempfile, unittest

MODULE = 'UnsignedGoals'
MODULE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', MODULE + '.curry'
  )
LAST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'benchmarks'
  , 'Last.curry'
  )
TIMEOUT = 300
# The bound of the search under the stress mode of the collector; see
# TestPrograms.test_repl_eval_under_stress.
STRESS_TIMEOUT = 60
IS_CXX = curry.flags['backend'] == 'cxx'

def values(*args, **kwds):
  '''The values of a goal, converted to Python.'''
  kwds.setdefault('converter', 'topython')
  return list(curry.eval(*args, **kwds))

def texts(*args):
  '''The values of a goal as Curry text.'''
  return [str(value) for value in curry.eval(*args)]

def tvar(i):
  return fc.TVar(i)

def tcons(name, *args):
  return fc.TCons(fc.prelude(name), list(args))

def pred(classname, typeexpr):
  return sigtable.Predicate('Prelude.' + classname, typeexpr)

def scheme(context, typeexpr, source_arity=0, name='goal'):
  '''A scheme with the given context, as the front end would generalize it.'''
  typevars = sorted(set(_typevars(typeexpr)) | set(
      i for p in context for i in _typevars(p.typeexpr)
    ))
  return sigtable.Scheme(
      'M', name, [(i, fc.KStar) for i in typevars], context, typeexpr
    , len(context) + source_arity, len(context)
    )

def _typevars(te):
  if isinstance(te, fc.TVar):
    yield te.index
  elif isinstance(te, fc.FuncType):
    yield from _typevars(te.domain)
    yield from _typevars(te.range)
  elif isinstance(te, fc.TCons):
    for arg in te.args:
      yield from _typevars(arg)

class TestDefaulting(cytest.TestCase):
  '''The table of the PAKCS REPL over schemes built by hand.'''

  def default(self, context, typeexpr, **kwds):
    return defaulting.default_scheme(scheme(context, typeexpr), **kwds)

  def test_pass_one(self):
    '''Num and Integral give Int, Fractional and Floating Float, Monad and MonadFail IO.'''
    for classname, expected in [
        ('Num', 'Int'), ('Integral', 'Int'), ('Fractional', 'Float')
      , ('Floating', 'Float')
      ]:
      d = self.default([pred(classname, tvar(0))], tvar(0))
      self.assertEqual(d.substitution, {0: expected})
      self.assertEqual(d.show_type(), expected)
      self.assertEqual(d.instances, [(pred(classname, tvar(0)), 'Prelude.' + expected)])
      self.assertTrue(d.changed)
    for classname in ['Monad', 'MonadFail']:
      d = self.default([pred(classname, tvar(1)), pred('Num', tvar(0))], tcons('Apply', tvar(1), tvar(0)))
      self.assertEqual(d.substitution, {0: 'Int', 1: 'IO'})
      # Apply IO Int is folded to IO Int.
      self.assertEqual(d.typeexpr, tcons('IO', tcons('Int')))
      self.assertEqual(d.show_type(), 'IO Int')
      self.assertEqual(
          [typename for _, typename in d.instances], ['Prelude.IO', 'Prelude.Int']
        )

  def test_pass_two(self):
    '''Data, Eq, Ord, Read and Show are dropped on Int and Float; Enum on Int.'''
    for dropped in ['Data', 'Eq', 'Ord', 'Read', 'Show', 'Enum']:
      d = self.default([pred(dropped, tvar(0)), pred('Num', tvar(0))], tvar(0))
      self.assertEqual(d.show_type(), 'Int')
      self.assertEqual(len(d.instances), 2)
      self.assertEqual(d.instances[0][1], 'Prelude.Int')
    for dropped in ['Data', 'Eq', 'Ord', 'Read', 'Show']:
      d = self.default([pred(dropped, tvar(0)), pred('Fractional', tvar(0))], tvar(0))
      self.assertEqual(d.show_type(), 'Float')
    # Enum is not dropped on Float.
    with self.assertRaisesRegex(DefaultingError, ORACLE_SENTENCE):
      self.default([pred('Enum', tvar(0)), pred('Fractional', tvar(0))], tvar(0))
    # Monad is dropped on IO.
    d = self.default([pred('Monad', tvar(0)), pred('MonadFail', tvar(0))], tcons('Apply', tvar(0), tcons('Int')))
    self.assertEqual(d.show_type(), 'IO Int')

  def test_data_alone(self):
    '''A variable with Data alone defaults to Bool.'''
    d = self.default([pred('Data', tvar(0))], tcons('(,)', tcons('Bool'), tvar(0)))
    self.assertEqual(d.substitution, {0: 'Bool'})
    self.assertEqual(d.data_defaults, [0])
    self.assertEqual(d.show_type(), '(Bool, Bool)')
    self.assertEqual(d.instances, [(pred('Data', tvar(0)), 'Prelude.Bool')])
    # Data with another class on an unbound variable fails, in either order.
    for context in [
        [pred('Data', tvar(0)), pred('Eq', tvar(0))]
      , [pred('Eq', tvar(0)), pred('Data', tvar(0))]
      , [pred('Data', tvar(0)), pred('Show', tvar(0))]
      ]:
      with self.assertRaisesRegex(DefaultingError, ORACLE_SENTENCE):
        self.default(context, tvar(0))
    # The walk follows the reversed context, as the oracle does.  It meets
    # Data first in [Enum a, Data a], binds a to Bool and drops Enum on
    # Bool; in [Data a, Enum a], the order the front end writes, it meets
    # Enum on an unbound variable and rejects the scheme.
    d = self.default([pred('Enum', tvar(0)), pred('Data', tvar(0))], tvar(0))
    self.assertEqual(d.show_type(), 'Bool')
    self.assertEqual(
        d.instances
      , [(pred('Enum', tvar(0)), 'Prelude.Bool'), (pred('Data', tvar(0)), 'Prelude.Bool')]
      )
    with self.assertRaisesRegex(DefaultingError, ORACLE_SENTENCE):
      self.default([pred('Data', tvar(0)), pred('Enum', tvar(0))], tvar(0))

  def test_polymorphic_and_functional(self):
    '''Unconstrained variables stay; a functional type is accepted.'''
    d = self.default([], tcons('[]', tvar(0)))
    self.assertFalse(d.changed)
    self.assertEqual(d.show_type(), '[a]')
    d = self.default([pred('Num', tvar(0))], fc.FuncType(tvar(1), fc.FuncType(tvar(0), tvar(1))))
    self.assertEqual(d.show_type(), 'a -> Int -> a')
    self.assertEqual(d.instances, [(pred('Num', tvar(0)), 'Prelude.Int')])

  def test_errors(self):
    '''The classes outside the table, with the oracle's sentence and the type.'''
    cases = [
        ([pred('Enum', tvar(0))], tvar(0), 'Enum a => a')
      , ([pred('Bounded', tvar(0))], tvar(0), 'Bounded a => a')
      , ([pred('Bounded', tvar(0)), pred('Num', tvar(0))], tvar(0), r'\(Bounded a, Num a\) => a')
      , ([pred('Show', tvar(0))], tcons('[]', tcons('Char')), r'Show a => \[Char\]')
      , ([pred('Applicative', tvar(1)), pred('Num', tvar(0))], tcons('Apply', tvar(1), tvar(0)), r'\(Applicative a, Num b\) => a b')
      , ([pred('Functor', tvar(0))], tcons('Apply', tvar(0), tcons('Int')), 'Functor a => a Int')
      # A constraint on a type that is not a variable.
      , ([pred('Num', tcons('[]', tvar(0)))], tcons('[]', tvar(0)), r'Num \[a\] => \[a\]')
      ]
    for context, typeexpr, shown in cases:
      with self.assertRaises(DefaultingError) as cm:
        self.default(context, typeexpr)
      message = str(cm.exception)
      self.assertRegex(message, '^cannot handle the overloaded goal M.goal of type ' + shown)
      self.assertIn('\n  ' + ORACLE_SENTENCE + '\n', message)
      self.assertTrue(message.endswith('add a type signature'), message)
      self.assertIsNotNone(cm.exception.predicate)
    # The caller names the goal and the hint.
    with self.assertRaises(DefaultingError) as cm:
      self.default(
          [pred('Enum', tvar(0))], tvar(0), what="expression 'toEnum 65'"
        , hint='add a type annotation (exprtype)'
        )
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded expression 'toEnum 65' of type Enum a => a\n"
        "  " + ORACLE_SENTENCE + "\n"
        "  add a type annotation (exprtype)"
      )
    self.assertIsInstance(cm.exception, curry.CurryTypeError)

  def test_normalize(self):
    '''Apply of a constructor folds up to the declared arity.'''
    arity = {'Prelude.IO': 1, 'Prelude.Maybe': 1, 'Prelude.Either': 2}.get
    io_int = tcons('Apply', tcons('IO'), tcons('Int'))
    self.assertEqual(defaulting.normalize(io_int), tcons('IO', tcons('Int')))
    self.assertEqual(defaulting.normalize(io_int, arity), tcons('IO', tcons('Int')))
    # Either a applied twice.
    e = tcons('Apply', tcons('Apply', tcons('Either'), tvar(0)), tvar(1))
    self.assertEqual(defaulting.normalize(e, arity), tcons('Either', tvar(0), tvar(1)))
    # A full constructor at the head stays an Apply.
    over = tcons('Apply', tcons('Int'), tvar(0))
    self.assertEqual(defaulting.normalize(over, lambda name: 0), over)
    # A variable at the head stays.
    m = tcons('Apply', tvar(0), tcons('Int'))
    self.assertEqual(defaulting.normalize(m, arity), m)
    # Inside an arrow.
    f = fc.FuncType(io_int, io_int)
    self.assertEqual(defaulting.normalize(f, arity), fc.FuncType(tcons('IO', tcons('Int')), tcons('IO', tcons('Int'))))

  def test_substitute(self):
    te = fc.FuncType(tvar(0), tcons('[]', tvar(1)))
    self.assertEqual(
        defaulting.substitute(te, {0: tcons('Int')})
      , fc.FuncType(tcons('Int'), tcons('[]', tvar(1)))
      )
    inner = fc.ForallType([(0, fc.KStar)], tvar(0))
    self.assertEqual(defaulting.substitute(inner, {0: tcons('Int')}), inner)


class TestModuleGoals(cytest.TestCase):
  '''curry.eval of a module function without a signature, both backends.'''

  def setUp(self):
    self.M = curry.import_(MODULE)

  def test_schemes(self):
    '''The front end generalized the goals with dictionaries.'''
    M = self.M
    self.assertEqual(M.main14.info.arity, 1)
    self.assertEqual(M.main14.signature, 'Num a => Maybe a')
    self.assertEqual(M.main16.signature, '(Monad a, Num b) => a b')
    self.assertEqual(M.main16.scheme.ndicts, 2)
    self.assertEqual(M.addOne.signature, 'Num a => a -> a')
    self.assertEqual(M.addOne.scheme.source_arity, 1)
    self.assertEqual(M.main33.signature, 'Int')

  def test_acceptance(self):
    '''main14 = Just 5, main15 = 1 + 2, main16 = return 5 give Just 5, 3, 5.'''
    M = self.M
    self.assertEqual(texts(M.main14), ['Just 5'])
    self.assertEqual(values(M.main15), [3])
    self.assertEqual(values(M.main16), [5])
    # The list form and the goal object.
    self.assertEqual(texts([M.main14]), ['Just 5'])
    self.assertEqual(values(goals.make_goal(curry.getInterpreter(), (M.main15,))), [3])

  def test_table_cases(self):
    '''The rows of the table on module goals.'''
    M = self.M
    self.assertEqual(values(M.main19), [1.5])          # Fractional a => a
    self.assertEqual(values(M.main20), [3])            # fromIntegral 3
    self.assertEqual(values(M.main21), [[1.0, 2.5]])   # Fractional a => [a]
    self.assertEqual(values(M.main22), [(1, 'a')])     # Num a => (a, Char)
    self.assertEqual(values(M.main23), [8])            # (Num a, Integral b)
    self.assertEqual(values(M.main24), [[]])           # [a] stays polymorphic
    self.assertEqual(texts(M.main28), ['Just 2'])      # fmap (+1) (Just 1)
    self.assertEqual(values(M.main30), ['3'])          # show (1 + 2): the front end defaulted it
    self.assertEqual(values(M.main31), [[1, 2, 3]])    # (Enum a, Num a) => [a]
    self.assertEqual(values(M.main33), [7])            # a signed goal, as before

  def test_data_to_bool(self):
    '''A lone Data constraint defaults to Bool: x =:= y binds the variables.'''
    results = texts(self.M.main29)
    self.assertEqual(results, ['(True, _a)'])

  def test_function_values(self):
    '''Value parameters that remain give a function value.'''
    M = self.M
    main25, = curry.eval(M.main25)
    self.assertEqual(str(main25), 'id')
    addOne, = curry.eval(M.addOne)
    self.assertRegex(str(addOne), r'addOne _inst#Prelude\.Num#Prelude\.Int')

  def test_io_goal(self):
    '''An IO goal runs during eval and yields its payload.'''
    M = self.M
    if IS_CXX:
      self.assertEqual(texts(M.main27), ['()'])
    else:
      stdout = StringIO()
      curry.getInterpreter().stdout = stdout
      self.assertEqual(texts(M.main27), ['()'])
      self.assertEqual(stdout.getvalue(), '1\n2\n')

  def test_errors(self):
    '''A goal the table cannot default raises with the type in the message.'''
    M = self.M
    for symbol, shown in [
        (M.main17, 'Enum a => a')
      , (M.main18, 'Bounded a => a')
      , (M.main26, r'\(Applicative a, Num b\) => a \(b, Char\)')
      , (M.main32, r'\(Bounded a, Num a\) => a')
      ]:
      with self.assertRaises(curry.CurryTypeError) as cm:
        curry.eval(symbol)
      message = str(cm.exception)
      self.assertRegex(
          message
        , '^cannot handle the overloaded goal %s\\.%s of type %s\n'
              % (MODULE, symbol.name, shown)
        )
      self.assertIn(ORACLE_SENTENCE, message)
      self.assertIn('add a type signature', message)
    # A class method with its own constraints names both in its type.
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot handle the overloaded goal Prelude\.round of type '
        r'\(RealFrac a, Integral b\) => a -> b\n'
      ):
      curry.eval(curry.symbol('Prelude.round'))

  def test_application(self):
    '''
    A symbol with dictionary parameters applied to arguments.  The typed
    builder of curry.expr (item Y7) supplies the dictionaries, so the call
    evaluates.  The dictionaries passed first, and raw_expr, work as before.
    '''
    M = self.M
    P = curry.import_('Prelude')
    self.assertEqual(values(M.addOne, 1), [2])
    self.assertEqual(values([M.addOne, 1]), [2])
    self.assertEqual(values(M.addOne, curry.expr(1)), [2])
    self.assertEqual(values(M.addOne, 1.5), [2.5])
    self.assertEqual(values(P.fromIntegral, 3), [3])
    num_int = curry.symbol('Prelude._inst#Prelude.Num#Prelude.Int')
    self.assertEqual(values(M.addOne, num_int, 1), [2])
    self.assertEqual(values([M.addOne, num_int, 1]), [2])
    self.assertEqual(values(M.addOne, curry.expr(num_int), 1), [2])
    self.assertEqual(values(M.addOne, [num_int], 1), [2])
    self.assertEqual(values(curry.raw_expr(M.addOne, num_int, 1)), [2])
    self.assertTrue(goals.is_dictionary(num_int))
    self.assertTrue(goals.is_dictionary(curry.expr(num_int)))
    self.assertFalse(goals.is_dictionary(M.addOne))
    self.assertFalse(goals.is_dictionary(curry.expr(1)))
    self.assertFalse(goals.is_dictionary(1))
    self.assertFalse(goals.is_dictionary([]))
    # The check does not touch a goal without arguments or a symbol without
    # dictionaries, and the string form of a value still works.
    self.assertEqual(values(M.main15), [3])
    self.assertEqual(values(P.id, 1), [1])

  def test_application_untyped(self):
    '''
    With the flag typed_expr off, a symbol with dictionary parameters
    applied to arguments is an error that names the alternatives; the
    literal would fill the dictionary slot otherwise.
    '''
    M = self.M
    P = curry.import_('Prelude')
    pattern = (
        r"^cannot apply UnsignedGoals\.addOne :: Num a => a -> a to arguments: "
        r"the symbol takes 1 class dictionary before its value parameters, "
        r"and curry\.eval supplies them only for a goal without arguments; "
        r"compile the call from text with curry\.compile\(\.\.\., mode='expr'\), "
        r"with exprtype for its type, or pass the dictionaries first$"
      )
    flags = curry.getInterpreter().flags
    flags['typed_expr'] = False
    try:
      for args in [(M.addOne, 1), ([M.addOne, 1],), (M.addOne, curry.expr(1))]:
        with self.assertRaisesRegex(curry.CurryTypeError, pattern):
          curry.eval(*args)
      with self.assertRaisesRegex(curry.CurryTypeError, '2 class dictionaries'):
        curry.eval(P.fromIntegral, 3)
      num_int = curry.symbol('Prelude._inst#Prelude.Num#Prelude.Int')
      self.assertEqual(values(M.addOne, num_int, 1), [2])
      self.assertEqual(values(M.main15), [3])
      self.assertEqual(values(P.id, 1), [1])
    finally:
      flags['typed_expr'] = True

  def test_unchanged_paths(self):
    '''Symbols without dictionaries, and arguments, go through expr as before.'''
    P = curry.import_('Prelude')
    self.assertEqual(values(P.id, 1), [1])
    value, = curry.eval(P.id)
    self.assertEqual(str(value), 'id')
    self.assertEqual(texts([P.Just, 1]), ['Just 1'])
    self.assertEqual(texts(self.M.main33), ['7'])
    # raw_expr keeps the partial application of a dictionary parameter.
    raw, = curry.eval(curry.raw_expr(self.M.main14))
    self.assertEqual(str(raw), 'main14')


class TestTextGoals(cytest.TestCase):
  '''curry.compile(mode='expr') without exprtype, both backends.'''

  def compile_values(self, text, **kwds):
    return values(curry.compile(text, mode='expr', **kwds))

  def test_acceptance(self):
    self.assertEqual(self.compile_values('1+2'), [3])
    self.assertEqual(self.compile_values('[1, 2.5]'), [[1.0, 2.5]])
    e = curry.compile('id', mode='expr')
    value, = curry.eval(e)
    self.assertEqual(str(value), 'id')

  def test_table_cases(self):
    self.assertEqual(self.compile_values('3 / 2'), [1.5])
    self.assertEqual(self.compile_values('fromIntegral 3'), [3])
    self.assertEqual(self.compile_values('[]'), [[]])
    self.assertEqual(self.compile_values("(1, 'a')"), [(1, 'a')])
    self.assertEqual(self.compile_values('2 ^ 3'), [8])
    self.assertEqual(self.compile_values('1 ? 2'), [1, 2])
    self.assertEqual(self.compile_values('show (1+2)'), ['3'])
    self.assertEqual(texts(curry.compile('Just 5', mode='expr')), ['Just 5'])
    self.assertEqual(texts(curry.compile('fmap (+1) (Just 1)', mode='expr')), ['Just 2'])

  def test_io(self):
    '''IO goals: return 5 gives 5; the action runs during eval.'''
    self.assertEqual(self.compile_values('return 5'), [5])
    if IS_CXX:
      self.assertEqual(self.compile_values('mapM_ print [1, 2]'), [()])
    else:
      stdout = StringIO()
      curry.getInterpreter().stdout = stdout
      self.assertEqual(self.compile_values('mapM_ print [1, 2]'), [()])
      self.assertEqual(self.compile_values('putStrLn "x"'), [()])
      self.assertEqual(stdout.getvalue(), '1\n2\nx\n')

  def test_errors(self):
    '''toEnum 65 and maxBound + 1 fail in the table; show [] in the front end.'''
    with self.assertRaises(curry.CompileError) as cm:
      curry.compile('toEnum 65', mode='expr')
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded expression 'toEnum 65' of type Enum a => a\n"
        "  " + ORACLE_SENTENCE + "\n"
        "  add a type annotation (exprtype)"
      )
    with self.assertRaisesRegex(
        curry.CompileError, r"'maxBound \+ 1' of type \(Bounded a, Num a\) => a"
      ):
      curry.compile('maxBound + 1', mode='expr')
    with self.assertRaisesRegex(curry.CompileError, 'Ambiguous type variable'):
      curry.compile('show []', mode='expr')
    # With exprtype the front end specializes, as before.
    self.assertEqual(self.compile_values('toEnum 65', exprtype='Char'), ['A'])
    self.assertEqual(self.compile_values('1+2', exprtype='Int'), [3])

  def test_single_step(self):
    '''A saturated call takes one step at compile time, as before.'''
    e = curry.compile('1+2', mode='expr')
    root = inspect.fwd_chain_target(e)
    self.assertNotEqual(root.info.name, compilemod.COMPILED_NAME)
    e = curry.compile('id', mode='expr')
    root = inspect.fwd_chain_target(e)
    self.assertNotEqual(root.info.name, compilemod.COMPILED_NAME)

  def test_lambda_goal(self):
    '''
    A lambda is lifted; the binding has arity 0 and gives a function value.
    On the Python backend the expression module was compiled while it
    loaded, and importSymbol resolved the lifted lambda through interp.symbol
    before loadSymbols had loaded it; the module is now compiled after its
    load (Backend.compile_pending).
    '''
    f = curry.compile('\\x -> x', mode='expr')
    value, = curry.eval(f)
    P = curry.import_('Prelude')
    self.assertEqual(values(P.apply, value, 1), [1])

  def test_imports(self):
    '''The loaded module is in scope, and its goals keep their dictionaries.'''
    M = curry.import_(MODULE)
    self.assertEqual(texts(curry.compile('main14', mode='expr', imports=[M])), ['Just 5'])
    self.assertEqual(self.compile_values('addOne 1', imports=[M]), [2])
    self.assertEqual(self.compile_values('addOne 1.5', imports=[M]), [2.5])

  def test_where_free(self):
    '''
    The variables of a trailing where ... free are lifted, and a variable
    whose type is absent from the result type is reported.  compile returns
    a node, the constructor of the expression module around the tuple of
    the expression and the variable; curry.eval finds the names through
    goals.lifted_goal, after an evaluation as before it.
    '''
    goal = curry.compile('xs ++ [3] =:= [1,2,3] where xs free', mode='expr')
    self.assertNotIsInstance(goal, Goal)
    self.assertEqual(goal.info.name, compilemod.LIFTED_NAME)
    self.assertTrue(inspect.isa_tuple(goal[0]))
    lifted = goals.lifted_goal(curry.getInterpreter(), goal)
    self.assertIsInstance(lifted, Goal)
    self.assertEqual(lifted.freevars, ('xs',))
    self.assertEqual(str(lifted.scheme), '(Data a, Num a) => [a] -> Bool')
    self.assertEqual(lifted.text, 'xs ++ [3] =:= [1,2,3] where xs free')
    self.assertIn('xs', repr(lifted))
    results = list(curry.eval(goal))
    self.assertEqual(len(results), 1)
    result, = results
    self.assertIsInstance(result, Bindings)
    self.assertEqual(str(result), '{xs=[1, 2]} True')
    self.assertEqual(str(result.value), 'True')
    self.assertEqual(list(result.bindings), ['xs'])
    self.assertEqual(str(result.bindings['xs']), '[1, 2]')
    self.assertEqual(curry.show_value(result), '{xs=[1, 2]} True')
    # Converted to Python.
    self.assertEqual(values(goal), [Bindings(True, {'xs': [1, 2]})])
    self.assertEqual(str(values(goal)[0]), '{xs=[1,2]} True')
    self.assertEqual(repr(values(goal)[0]), '<curry value {xs=[1,2]} True>')
    self.assertNotEqual(values(goal)[0], Bindings(False, {'xs': [1, 2]}))

  def test_where_free_shapes(self):
    '''
    The REPL's forms.  A variable whose type occurs in the result type is
    left in the value, bound or not; a variable whose type is absent from
    the result type is reported, bound or not.
    '''
    cases = [
        ('xs ++ [3] =:= [1,2,3] &> xs where xs free', ['[1, 2]'])
      , ('x where x free', ['_a'])
      , ('(x, y) where x, y free', ['(_a, _b)'])
      , ("(x, 'a') where x free", ["(_a, 'a')"])
      , ('[x, 1] where x free', ['[_a, 1]'])
      , ('(x ? 1) where x free', ['_a', '1'])
      , ('x =:= y where x, y free', ['{x=_a, y=_a} True'])
      , ('x =:= 1 where x free', ['{x=1} True'])
      , ('fst (1, x) where x free', ['{x=_a} 1'])
      , ('head (x:xs) where x, xs free', ['{xs=_b} _a'])
      , ('xs ++ ys =:= [1, 2] where xs, ys free'
        , ['{xs=[], ys=[1, 2]} True', '{xs=[1], ys=[2]} True', '{xs=[1, 2], ys=[]} True'])
      ]
    for text, expected in cases:
      with self.subTest(text=text):
        self.assertEqual(sorted(texts(curry.compile(text, mode='expr'))), sorted(expected))

  def test_where_free_node(self):
    '''
    A variable in the result type: compile returns the stepped expression,
    as for any text, and its value is the variable itself (the tests of the
    runtime build their variables this way).  A reported variable: the root
    is a tuple that curry.eval recognizes; a tuple built in Python is not a
    goal, and the records go with the reset of the interpreter.
    '''
    interp = curry.getInterpreter()
    e = curry.compile('x :: Int where x free', mode='expr')
    self.assertNotIsInstance(e, Goal)
    self.assertIsNone(goals.lifted_goal(interp, e))
    x, = curry.eval(e)
    self.assertTrue(inspect.isa_freevar(x))
    e = curry.compile('x =:= 1 where x free', mode='expr')
    self.assertIsNotNone(goals.lifted_goal(interp, e))
    self.assertIsNone(goals.lifted_goal(interp, curry.expr((1, 2))))
    self.assertIsNone(goals.lifted_goal(interp, 1))
    self.assertTrue(interp._lifted_goals)
    curry.reset()
    self.assertEqual(interp._lifted_goals, {})

  def test_absent_from_result(self):
    '''The rule on schemes built by hand.'''
    arrow = fc.FuncType
    Int, Bool = tcons('Int'), tcons('Bool')
    def absent(typeexpr, nfree):
      return goals.absent_from_result(
          scheme([], typeexpr, source_arity=nfree), nfree
        )
    self.assertEqual(absent(arrow(tcons('[]', Int), Bool), 1), [0])
    self.assertEqual(absent(arrow(tvar(0), tvar(0)), 1), [])
    self.assertEqual(
        absent(arrow(tvar(0), arrow(tvar(1), tcons('(,)', tvar(0), tvar(1)))), 2), []
      )
    self.assertEqual(absent(arrow(tvar(0), arrow(tcons('[]', tvar(0)), tvar(0))), 2), [1])
    self.assertEqual(absent(arrow(Int, tcons('[]', Int)), 1), [])
    self.assertEqual(absent(arrow(tcons('[]', Int), Int), 1), [0])
    self.assertEqual(absent(arrow(Int, arrow(Bool, Int)), 2), [1])
    self.assertEqual(absent(Int, 0), [])
    with self.assertRaises(curry.CurryTypeError):
      absent(Int, 1)
    self.assertTrue(goals.type_occurs(Int, arrow(Bool, tcons('[]', Int))))
    self.assertFalse(goals.type_occurs(tcons('[]', Int), tcons('[]', tcons('[]', Bool))))

  def test_where_free_with_exprtype(self):
    '''With exprtype the clause stays a local declaration, as before.'''
    e = curry.compile(
        'xs ++ [3] =:= [1,2,3] &> xs where xs free', mode='expr', exprtype='[Int]'
      )
    self.assertNotIsInstance(e, Goal)
    self.assertIsNone(goals.lifted_goal(curry.getInterpreter(), e))
    self.assertEqual(values(e), [[1, 2]])

  def test_split_where_free(self):
    split = goals.split_where_free
    self.assertEqual(split('x where x free'), ('x', ['x']))
    self.assertEqual(split('(x, y) where x, y free'), ('(x, y)', ['x', 'y']))
    self.assertEqual(split("f x' where x' free "), ('f x\'', ['x\'']))
    self.assertEqual(split('x where x = 1'), ('x where x = 1', []))
    self.assertEqual(split('let x free in x'), ('let x free in x', []))
    self.assertEqual(split('xs where xs free\n'), ('xs', ['xs']))
    self.assertEqual(split('x where 1 free'), ('x where 1 free', []))

  def test_split_tuple_text(self):
    split = goals.split_tuple_text
    self.assertEqual(split('(True, [1, 2])', 2), ['True', '[1, 2]'])
    self.assertEqual(split('("a, b", \'x\', [1, (2, 3)])', 3), ['"a, b"', "'x'", '[1, (2, 3)]'])
    self.assertEqual(split("(',', '\\'', \"\\\"\")", 3), ["','", "'\\''", '"\\""'])
    self.assertEqual(split("(Foo' 1, x)", 2), ["Foo' 1", 'x'])
    self.assertIsNone(split('(a, b)', 3))
    self.assertIsNone(split('a', 2))
    self.assertIsNone(split('(a, )', 2))

  def test_expression_scheme(self):
    '''The undefaulted type of a text, what :type prints.'''
    interp = curry.getInterpreter()
    def typeof(text, **kwds):
      return str(compilemod.expression_scheme(interp, text, **kwds))
    self.assertEqual(typeof('1+2'), 'Num a => a')
    self.assertEqual(typeof('[]'), '[a]')
    self.assertEqual(typeof('id'), 'a -> a')
    self.assertEqual(typeof('toEnum 65'), 'Enum a => a')
    self.assertEqual(typeof('return 1'), '(Monad a, Num b) => a b')
    self.assertEqual(typeof('x where x free'), 'Data a => a')
    M = curry.import_(MODULE)
    self.assertEqual(typeof('main14', imports=[M]), 'Num a => Maybe a')


class TestPrograms(cytest.TestCase):
  '''The REPL and sprite-exec, in child processes on the backend of this one.'''

  def run_child(self, cmd, status=0, cwd=None, env=None, timeout=TIMEOUT):
    proc = subprocess.run(
        ['timeout', str(timeout)] + cmd, capture_output=True, text=True
      , cwd=cwd, env=env
      )
    self.assertEqual(
        proc.returncode, status
      , 'status %s; stdout:\n%s\nstderr:\n%s' % (proc.returncode, proc.stdout, proc.stderr)
      )
    return proc

  def repl(self, *commands, status=0):
    '''Runs the REPL with the commands and returns the completed process.'''
    args = []
    for command in commands:
      args.extend(command.split())
    return self.run_child(
        [sys.executable, '-m', 'curry.tools.icy'] + args + [':quit'], status=status
      )

  def test_repl_eval_and_type(self):
    proc = self.repl(
        ':eval 1+2', ':type 1+2', ':eval xs ++ [3] =:= [1,2,3] where xs free'
      , ':type x where x free', ':eval x where x free', ':eval [1, 2.5]'
      )
    self.assertEqual(
        proc.stdout.splitlines()
      , ['3', '1+2 :: Num a => a', '{xs=[1, 2]} True', 'x where x free :: Data a => a'
        , '_a', '[1.0000000000000000, 2.5000000000000000]' if IS_CXX else '[1.0, 2.5]']
      )

  @unittest.skipUnless(IS_CXX, 'the stress mode belongs to the collector of the C++ backend')
  def test_repl_eval_under_stress(self):
    '''
    :eval of a long search under the stress mode of the collector, within a
    bound.  The REPL hands the expression to curry.eval and keeps no
    reference to it, and the goal object drops its node when the evaluation
    starts.  A reference to the root keeps the history of the search (the
    choices pulled to the root with their failed alternatives) reachable,
    every collection of the stress mode marks it, and the run grows with
    the square of the length: on a 12-core machine, last of 3000 elements
    took 26 s with the reference and 1 s without, and 8000 elements take
    1 s without it and minutes with it.
    '''
    env = dict(os.environ, SPRITE_GC_STRESS='1')
    proc = self.run_child(
        [ sys.executable, '-m', 'curry.tools.icy', ':load', LAST_FILE
        , ':eval', 'last (replicate 8000 True)', ':quit'
        ]
      , env=env, timeout=STRESS_TIMEOUT
      )
    self.assertEqual(proc.stdout, 'True\n')

  def test_repl_loaded_module(self):
    proc = self.repl(':load ' + MODULE_FILE, ':eval main14', ':type main14', ':eval addOne 1')
    self.assertEqual(
        proc.stdout.splitlines()
      , ['Just 5', 'main14 :: Num a => Maybe a', '2']
      )

  def test_repl_command_prefixes(self):
    '''A command may be given by any unambiguous prefix: :l, :e, :t, :q.'''
    proc = self.repl(':l ' + MODULE_FILE, ':e 1+2', ':t 1+2', ':e main14', ':q')
    self.assertEqual(
        proc.stdout.splitlines(), ['3', '1+2 :: Num a => a', 'Just 5']
      )

  def test_repl_error(self):
    proc = self.repl(':eval toEnum 65', status=1)
    self.assertEqual(proc.stdout, '')
    self.assertIn("'toEnum 65' of type Enum a => a", proc.stderr)
    self.assertIn(ORACLE_SENTENCE, proc.stderr)

  def test_sprite_exec(self):
    proc = self.run_child([config.sprite_exec(), '-m', MODULE, '-g', 'main14'])
    self.assertEqual(proc.stdout, 'Just 5\n')
    proc = self.run_child([config.sprite_exec(), '-m', MODULE, '-g', 'main16'])
    self.assertEqual(proc.stdout, '5\n')
    proc = self.run_child([config.sprite_exec(), '-m', MODULE, '-g', 'main17'], status=1)
    self.assertEqual(proc.stdout, '')
    self.assertIn(ORACLE_SENTENCE, proc.stderr)
    self.assertIn('Enum a => a', proc.stderr)


@unittest.skipIf(IS_CXX, 'curry.save writes C++ source on the C++ backend')
class TestSave(cytest.TestCase):
  '''Saved modules on the Python backend.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-goals-')
    self.addCleanup(lambda: __import__('shutil').rmtree(self.tmpdir, ignore_errors=True))
    self.M = curry.import_(MODULE)

  def run_saved(self, filename):
    '''Runs a saved module from its own directory, without the search path.'''
    env = dict(os.environ)
    env.pop('CURRYPATH', None)
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), sys.executable, os.path.basename(filename)]
      , cwd=os.path.dirname(filename), env=env, capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def test_constrained_goal(self):
    '''A saved module with a constrained goal runs from another directory.'''
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main14')
    with open(filename, encoding='utf-8') as stream:
      text = stream.read()
    footer = text[text.index('# SECTION: .footer'):]
    self.assertIn("goal='main14', goalscheme='(ForallType", footer)
    self.assertIn('_Dict#Num', footer)
    # The functions have bodies, not failing stubs (the defect behind the
    # known failure of examples/04-static-compile).
    self.assertLess(text.count('_0.rewrite(rts.Failure)'), 5)
    self.assertEqual(self.run_saved(filename), 'Just 5\n')

  def test_io_goal(self):
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main16')
    self.assertEqual(self.run_saved(filename), '5\n')

  def test_signed_goal(self):
    '''A goal without dictionaries gets no scheme in the footer.'''
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main33')
    with open(filename, encoding='utf-8') as stream:
      text = stream.read()
    self.assertIn("goal='main33')", text)
    self.assertNotIn('goalscheme', text)
    self.assertEqual(self.run_saved(filename), '7\n')

  def test_goal_from_scheme(self):
    '''The footer's scheme rebuilds the goal without an interface file.'''
    from curry.__main__ import Main
    scheme = self.M.main14.scheme
    text = goals.flat_type_text(scheme)
    rebuilt = goals.scheme_from_flat_text(self.M.main14, text)
    self.assertEqual(str(rebuilt), str(scheme))
    self.assertEqual(rebuilt.ndicts, 1)
    goal = Main.goal_from_scheme(self.M.main14, text)
    self.assertEqual(texts(goal), ['Just 5'])
    self.assertIs(Main.goal_from_scheme(self.M.main33, goals.flat_type_text(self.M.main33.scheme)), self.M.main33)

  def test_refusals(self):
    '''save(goal='maxBound') raises at save time; save without a goal raises.'''
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    with self.assertRaises(curry.CurryTypeError) as cm:
      curry.save(self.M, filename, goal='main18')
    self.assertIn('Bounded a => a', str(cm.exception))
    self.assertIn(ORACLE_SENTENCE, str(cm.exception))
    self.assertFalse(os.path.exists(filename))
    with self.assertRaisesRegex(ValueError, 'curry.save needs a goal'):
      curry.save(self.M, filename)
    self.assertFalse(os.path.exists(filename))
    with self.assertRaisesRegex(ValueError, 'curry.save needs a goal'):
      curry.save(self.M)
    # A module without a main program is still saved and loaded.
    curry.save(self.M, filename, module_main=False)
    with open(filename, encoding='utf-8') as stream:
      self.assertNotIn('moduleMain', stream.read())
    text = curry.save(self.M, module_main=False)
    self.assertIn('IModule.fromBOM', text)
    self.assertNotIn('moduleMain', text)
    self.assertIn('IModule.fromBOM', inspect.getimpl(self.M))
