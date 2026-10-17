'''
Goals without type signatures, item Y4 of the typed boundary (#53, epic #48;
fixes #39, and #35 in its refuse-to-save form).

A goal whose scheme has class constraints is a function whose leading
parameters are dictionaries.  ``curry.typecheck.defaulting`` applies the
table of the PAKCS REPL to the constraints, and ``curry.typecheck.goals``
applies the goal to one base instance per constraint, in the order of the
scheme.  One path serves ``curry.eval`` of a module function,
``curry.parse`` without ``exprtype``, ``:eval`` and ``:type``
of the REPL, ``sprite-exec -g``, and saved modules on the Python backend.
A saved program reads ``-g`` as ``sprite-exec`` does; the goal it was saved
with is the default (issue #35).  ``curry.save`` without a goal raises on
both backends.
The text route lifts the variables of a trailing ``where x free`` to
parameters, as the REPL does, and reports the bindings of the variables
whose type is absent from the result type; a variable whose type occurs in
the result type is left in the value.  ``parse`` returns a
node; the goal objects stay inside ``curry.eval``.
'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import evaluator
from curry import config, inspect
from curry.interpreter import compile as compilemod
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import defaulting, goals, sigtable
from curry.typecheck.defaulting import DefaultingError, ORACLE_SENTENCE
from curry.typecheck.goals import Bindings, Goal
from io import StringIO
from unittest import mock
import curry, os, re, shutil, subprocess, sys, tempfile, unittest

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

def values(first, *args):
  return list(curry.eval(first(*args) if args else first))

def texts(first, *args):
  return [curry.show(value) for value in curry.eval(first(*args) if args else first)]

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
      self.assertIn('\n' + ORACLE_SENTENCE + '\n', message)
      self.assertTrue(message.endswith("state the type: curry.term(goal, type='T')"), message)
      self.assertIsNotNone(cm.exception.predicate)
    # The caller names the goal and the hint.
    with self.assertRaises(DefaultingError) as cm:
      self.default(
          [pred('Enum', tvar(0))], tvar(0), what="goal toEnum 65"
        , hint='state the type: toEnum 65 :: Int'
        )
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded goal toEnum 65 of type Enum a => a\n"
        + ORACLE_SENTENCE + "\n"
        "state the type: toEnum 65 :: Int"
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
    self.assertEqual(texts(M.main14), ['Just 5'])
    self.assertEqual(values(goals.make_goal(cytest.raw.interp(), (M.main15,))), [3])

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
    self.assertEqual(results, ['(True,_a)'])

  def test_function_values(self):
    M = self.M
    for goal in (M.main25, M.addOne):
      value, = curry.eval(goal)
      self.assertIsInstance(value, curry.Function)
    self.assertEqual(curry.show(curry.eval(M.main25).one()), 'id')
    self.assertEqual(values(curry.eval(M.addOne).one()(2)), [3])

  def test_io_goal(self):
    '''An IO goal runs during eval and yields its payload.'''
    M = self.M
    if IS_CXX:
      self.assertEqual(texts(M.main27), ['()'])
    else:
      stdout = StringIO()
      cytest.raw.interp().stdout = stdout
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
      self.assertIn("state the type: curry.term(goal, type='T')", message)
    # A class method with its own constraints names both in its type.
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot handle the overloaded goal Prelude\.round of type '
        r'\(RealFrac a, Integral b\) => a -> b\n'
      ):
      curry.eval(curry.import_('Prelude')['round'])

  def test_application(self):
    M = self.M
    P = curry.import_('Prelude')
    self.assertEqual(values(M.addOne(1)), [2])
    self.assertEqual(values(M.addOne(curry.term(1))), [2])
    self.assertEqual(values(M.addOne(1.5)), [2.5])
    self.assertEqual(values(P.fromIntegral(3)), [3])
    num_int = P['_inst#Prelude.Num#Prelude.Int']
    self.assertTrue(goals.is_dictionary(num_int))
    self.assertTrue(goals.is_dictionary(cytest.raw.expr(num_int)))
    self.assertFalse(goals.is_dictionary(M.addOne))
    self.assertFalse(goals.is_dictionary(curry.term(1)))
    self.assertFalse(goals.is_dictionary(1))
    self.assertFalse(goals.is_dictionary([]))
    self.assertEqual(values(M.main15), [3])
    self.assertEqual(values(P.id(1)), [1])


  def test_unchanged_paths(self):
    '''Symbols without dictionaries, and arguments, go through expr as before.'''
    P = curry.import_('Prelude')
    self.assertEqual(values(P.id, 1), [1])
    value, = curry.eval(P.id)
    self.assertEqual(str(value), 'id')
    self.assertEqual(texts(P.Just(1)), ['Just 1'])
    self.assertEqual(texts(self.M.main33), ['7'])
    # raw_expr keeps the partial application of a dictionary parameter.
    raw, = cytest.raw.values(cytest.raw.expr(self.M.main14))
    self.assertEqual(str(raw), 'main14')


class TestTextGoals(cytest.TestCase):
  '''curry.parse without exprtype, both backends.'''

  def compile_values(self, text, *, type=None, **kwds):
    if type is not None:
      text = '(%s) :: %s' % (text, type)
    return values(curry.parse(text, **kwds))

  def test_acceptance(self):
    self.assertEqual(self.compile_values('1+2'), [3])
    self.assertEqual(self.compile_values('[1, 2.5]'), [[1.0, 2.5]])
    e = curry.parse('id')
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
    self.assertEqual(texts(curry.parse('Just 5')), ['Just 5'])
    self.assertEqual(texts(curry.parse('fmap (+1) (Just 1)')), ['Just 2'])

  def test_io(self):
    '''IO goals: return 5 gives 5; the action runs during eval.'''
    self.assertEqual(self.compile_values('return 5'), [5])
    if IS_CXX:
      self.assertEqual(self.compile_values('mapM_ print [1, 2]'), [()])
    else:
      stdout = StringIO()
      cytest.raw.interp().stdout = stdout
      self.assertEqual(self.compile_values('mapM_ print [1, 2]'), [()])
      self.assertEqual(self.compile_values('putStrLn "x"'), [()])
      self.assertEqual(stdout.getvalue(), '1\n2\nx\n')

  def test_errors(self):
    '''toEnum 65 and maxBound + 1 fail in the table; show [] in the front end.'''
    with self.assertRaises(curry.DefaultingError) as cm:
      curry.eval(curry.parse('toEnum 65'))
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded goal toEnum 65 of type Enum a => a\n"
        + ORACLE_SENTENCE + "\n"
        "state the type: curry.term(goal, type='T')"
      )
    with self.assertRaisesRegex(
        curry.DefaultingError, r"maxBound \+ 1 of type \(Bounded a, Num a\) => a"
      ):
      curry.eval(curry.parse('maxBound + 1'))
    with self.assertRaisesRegex(curry.CompileError, 'Ambiguous type variable'):
      curry.parse('show []')
    # With exprtype the front end specializes, as before.
    self.assertEqual(self.compile_values('toEnum 65', type='Char'), ['A'])
    self.assertEqual(self.compile_values('1+2', type='Int'), [3])

  def test_single_step(self):
    for text in ('1+2', 'id'):
      term = curry.parse(text)
      root = evaluator.single_step(cytest.raw.interp(), cytest.raw.expr(term))
      root = inspect.fwd_chain_target(root)
      self.assertNotEqual(root.info.name, compilemod.COMPILED_NAME)

  def test_lambda_goal(self):
    '''
    A lambda is lifted; the binding has arity 0 and gives a function value.
    On the Python backend the expression module was compiled while it
    loaded, and importSymbol resolved the lifted lambda through interp.symbol
    before loadSymbols had loaded it; the module is now compiled after its
    load (Backend.compile_pending).
    '''
    f = curry.parse('\\x -> x')
    value, = curry.eval(f)
    P = curry.import_('Prelude')
    self.assertEqual(values(P.apply, value, 1), [1])

  def test_imports(self):
    '''The loaded module is in scope, and its goals keep their dictionaries.'''
    M = curry.import_(MODULE)
    self.assertEqual(texts(curry.parse('main14', imports=[M])), ['Just 5'])
    self.assertEqual(self.compile_values('addOne 1', imports=[M]), [2])
    self.assertEqual(self.compile_values('addOne 1.5', imports=[M]), [2.5])

  def test_where_free(self):
    text = 'xs ++ [3] =:= [1,2,3] where xs free'
    goal = curry.parse(text)
    self.assertIsInstance(goal, curry.Term)
    self.assertEqual(list(goal.free_vars), ['xs'])
    self.assertIsInstance(goal.free_vars['xs'], curry.Var)
    self.assertEqual(str(goal), text)
    answer = curry.solve(goal).one()
    self.assertEqual(answer, curry.Answer(True, curry.Bindings({'xs': [1, 2]})))
    self.assertEqual(str(answer), '{xs=[1,2]} True')
    self.assertEqual(repr(answer), 'Answer(value=True, bindings={xs=[1,2]})')
    self.assertNotEqual(answer, curry.Answer(False, answer.bindings))
    self.assertEqual(curry.show(answer), '{xs=[1,2]} True')
    self.assertEqual(values(goal), [True])

  def test_where_free_shapes(self):
    cases = [
        ('xs ++ [3] =:= [1,2,3] &> xs where xs free', ['{xs=[1,2]} [1,2]'])
      , ('x where x free', ['{x=x} x'])
      , ('(x, y) where x, y free', ['{x=x, y=y} (x,y)'])
      , ("(x, 'a') where x free", ["{x=x} (x,'a')"])
      , ('[x, 1] where x free', ['{x=x} [x,1]'])
      , ('(x ? 1) where x free', ['{x=x} x', '{x=x} 1'])
      , ('x =:= y where x, y free', ['{x=x, y=x} True'])
      , ('x =:= 1 where x free', ['{x=1} True'])
      , ('fst (1, x) where x free', ['{x=x} 1'])
      , ('head (x:xs) where x, xs free', ['{x=x, xs=xs} x'])
      , ('xs ++ ys =:= [1, 2] where xs, ys free',
          ['{xs=[], ys=[1,2]} True', '{xs=[1], ys=[2]} True', '{xs=[1,2], ys=[]} True'])
      ]
    for text, expected in cases:
      with self.subTest(text=text):
        self.assertEqual(sorted(str(a) for a in curry.solve(curry.parse(text))), sorted(expected))

  def test_where_free_variable(self):
    e = curry.parse('x :: Int where x free')
    x, = curry.eval(e)
    self.assertIs(x, e.free_vars['x'])
    self.assertEqual(curry.typeof(x), 'Int')
    constrained = curry.parse('x =:= 1 where x free')
    self.assertEqual(list(constrained.free_vars), ['x'])
    answer = curry.solve(constrained).one()
    self.assertEqual(answer.bindings['x'], 1)
    curry.reset()
    with self.assertRaises(curry.StaleError):
      curry.eval(e)

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
    e = curry.parse('(xs ++ [3] =:= [1,2,3] &> xs) :: [Int] where xs free')
    self.assertNotIsInstance(e, Goal)
    self.assertIsNone(goals.lifted_goal(cytest.raw.interp(), e))
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
    interp = cytest.raw.interp()
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
      , ['3', '1+2 :: Num a => a', '{xs=[1,2]} True', 'x where x free :: Data a => a'
        , '{x=x} x', '[1.0,2.5]']
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
        [sys.executable, '-m', 'curry.tools.icy', ':load', LAST_FILE, ':eval', 'last (replicate 8000 True)', ':quit']
      , env=env, timeout=STRESS_TIMEOUT
      )
    self.assertEqual(proc.stdout, 'True\n')

  def test_repl_loaded_module(self):
    proc = self.repl(':load ' + MODULE_FILE, ':eval main14', ':type main14', ':eval addOne 1')
    self.assertEqual(
        proc.stdout.splitlines()
      , ['Just 5', 'main14 :: Num a => Maybe a', '2']
      )

  def test_repl_set_backend(self):
    '''
    :set lists the backend of the session; :set backend NAME reloads the
    interpreter with that backend and loads the module again; an unknown
    name is refused.
    '''
    this = 'cxx' if IS_CXX else 'py'
    other = 'py' if IS_CXX else 'cxx'
    proc = self.repl(
        ':load ' + MODULE_FILE, ':set', ':set backend ' + other, ':set'
      , ':eval main14'
      )
    self.assertEqual(proc.stdout.splitlines(), ['Just 5'])
    before = proc.stderr.index("backend : %r" % this)
    after = proc.stderr.index("backend : %r" % other)
    self.assertLess(before, after)
    self.assertRegex(proc.stderr, r'backend\s+- The backend of the session')
    proc = self.repl(':set backend llvm', status=1)
    self.assertIn("Invalid backend: 'llvm'", proc.stderr)

  def test_repl_command_prefixes(self):
    '''A command may be given by any unambiguous prefix: :l, :e, :t, :q.'''
    proc = self.repl(':l ' + MODULE_FILE, ':e 1+2', ':t 1+2', ':e main14', ':q')
    self.assertEqual(
        proc.stdout.splitlines(), ['3', '1+2 :: Num a => a', 'Just 5']
      )

  def test_repl_error(self):
    proc = self.repl(':eval toEnum 65', status=1)
    self.assertEqual(proc.stdout, '')
    self.assertIn("toEnum 65 of type Enum a => a", proc.stderr)
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


class TestReplSession(cytest.TestCase):
  '''
  The state of a REPL session across :set backend, in this process.  The
  reload of the interpreter is stubbed, so the backend of this process
  stays; the loads are real.
  '''

  def setUp(self):
    from curry.tools.icy import commands, repl
    self.commands, self.repl_module = commands, repl
    path = curry.path
    self.addCleanup(path.__setitem__, slice(None), list(path))

  def test_set_backend_state(self):
    '''
    A switch whose load of the module fails leaves the session on the new
    backend: the option says so, the Prelude is at the prompt, the argument
    of the :load is kept for a switch back, and the command in flight is
    untouched.  A switch whose load succeeds shows the module again.
    '''
    this = curry.flags['backend']
    other = 'py' if IS_CXX else 'cxx'
    repl = self.repl_module.REPL([':load', MODULE_FILE])
    self.assertEqual(repl.module.__name__, MODULE)
    self.assertEqual(repl.options['backend'], this)
    real_import = curry.import_
    def failing_import(name, *args, **kwds):
      if name == MODULE:
        raise ImportError('no %s on this backend' % name)
      return real_import(name, *args, **kwds)
    repl.command, repl.args = ':set', ['backend', other]
    with mock.patch.object(curry, 'reload') as reload:
      with mock.patch.object(curry, 'import_', side_effect=failing_import):
        with self.assertRaisesRegex(ImportError, 'no %s' % MODULE):
          self.commands.eval(':set', repl)
    reload.assert_called_once_with({'backend': other})
    self.assertEqual(repl.options['backend'], other)
    self.assertEqual(repl.module.__name__, 'Prelude')
    self.assertEqual(repl.loaded, MODULE_FILE)
    self.assertEqual((repl.command, repl.args), (':set', ['backend', other]))
    with mock.patch.object(curry, 'reload') as reload:
      repl.options['backend'] = this
    reload.assert_called_once_with({'backend': this})
    self.assertEqual(repl.options['backend'], this)
    self.assertEqual(repl.module.__name__, MODULE)
    self.assertEqual(repl.loaded, MODULE_FILE)


class TestSaveRefusals(cytest.TestCase):
  '''
  What curry.save refuses, on both backends (issue #35).  A program needs a
  goal, and a goal the table cannot default fails at save time.  Nothing is
  written in either case.
  '''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-goals-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    self.M = curry.import_(MODULE)
    self.filename = os.path.join(self.tmpdir, MODULE + '.py')

  def test_without_goal(self):
    '''save without a goal raises ValueError, to a file and to a string.'''
    with self.assertRaisesRegex(ValueError, 'curry.save needs a goal'):
      curry.save(self.M, self.filename)
    self.assertFalse(os.path.exists(self.filename))
    with self.assertRaisesRegex(ValueError, 'module_main=False'):
      curry.save(self.M)
    # A module without a main program is saved on both backends.
    text = curry.save(self.M, module_main=False)
    self.assertNotIn('moduleMain', text)
    self.assertNotIn('entry()', text)

  def test_undefaultable_goal(self):
    '''save(goal='maxBound') raises at save time, with the sentence of the oracle.'''
    with self.assertRaises(curry.CurryTypeError) as cm:
      curry.save(self.M, self.filename, goal='main18')
    self.assertIn('Bounded a => a', str(cm.exception))
    self.assertIn(ORACLE_SENTENCE, str(cm.exception))
    self.assertFalse(os.path.exists(self.filename))


# The saved program belongs to the Python backend.  On the C++ backend
# curry.save writes C++ source whose entry point is a stub
# (backends.cxx.compiler._generate_main), so the tests that run the saved
# file are known failures there; a C++ form of curry.save is an open decision
# of issue #82, stage 5.
SAVED_PROGRAM = (
    'the saved form of the C++ backend is C++ source whose entry point is a '
    'stub; it does not run as a program (issue #82, stage 5)'
  )

class TestSave(cytest.TestCase):
  '''
  Saved modules.  The tests that run the saved program hold on the Python
  backend and are known failures on the C++ backend (SAVED_PROGRAM); the
  rest hold on both.
  '''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-goals-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    self.M = curry.import_(MODULE)

  def run_saved(self, filename, *argv, status=0):
    '''
    Runs a saved module from its own directory, without the search path, and
    returns the completed process.  ``argv`` is its command line.
    '''
    env = dict(os.environ)
    env.pop('CURRYPATH', None)
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), sys.executable, os.path.basename(filename)]
            + list(argv)
      , cwd=os.path.dirname(filename), env=env, capture_output=True, text=True
      )
    self.assertEqual(
        proc.returncode, status
      , 'status %s; stdout:\n%s\nstderr:\n%s' % (proc.returncode, proc.stdout, proc.stderr)
      )
    return proc

  @cytest.expectedFailureIf(IS_CXX, SAVED_PROGRAM)
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
    self.assertEqual(self.run_saved(filename).stdout, 'Just 5\n')

  @cytest.expectedFailureIf(IS_CXX, SAVED_PROGRAM)
  def test_io_goal(self):
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main16')
    self.assertEqual(self.run_saved(filename).stdout, '5\n')

  @cytest.expectedFailureIf(IS_CXX, SAVED_PROGRAM)
  def test_signed_goal(self):
    '''A goal without dictionaries gets no scheme in the footer.'''
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main33')
    with open(filename, encoding='utf-8') as stream:
      text = stream.read()
    self.assertIn("goal='main33')", text)
    self.assertNotIn('goalscheme', text)
    self.assertEqual(self.run_saved(filename).stdout, '7\n')

  @cytest.expectedFailureIf(IS_CXX, SAVED_PROGRAM)
  def test_command_line(self):
    '''
    The saved program reads its command line as sprite-exec does (issue
    #35).  -g names the goal; the goal the module was saved with is the
    default; the empty goal runs nothing; an unknown goal and a goal the
    table cannot default are errors; the switches that do not apply to a
    saved module are rejected.
    '''
    filename = os.path.join(self.tmpdir, MODULE + '.py')
    curry.save(self.M, filename, goal='main14')
    self.assertEqual(self.run_saved(filename).stdout, 'Just 5\n')
    self.assertEqual(self.run_saved(filename, '-g', 'main14').stdout, 'Just 5\n')
    # A signed goal, a constrained goal, and an IO goal print what
    # sprite-exec prints.  The goals other than the recorded one get their
    # types from the interface of the module, as under sprite-exec.
    for goal, expected in [('main33', '7\n'), ('main15', '3\n'), ('main16', '5\n')]:
      self.assertEqual(self.run_saved(filename, '-g', goal).stdout, expected)
      proc = subprocess.run(
          ['timeout', str(TIMEOUT), config.sprite_exec(), '-m', MODULE, '-g', goal]
        , capture_output=True, text=True
        )
      self.assertEqual(proc.stdout, expected, proc.stderr)
    self.assertEqual(self.run_saved(filename, '-g', '').stdout, '')
    proc = self.run_saved(filename, '-g', 'nosuch', status=1)
    self.assertEqual(proc.stdout, '')
    self.assertIn("no symbol 'nosuch'", proc.stderr)
    proc = self.run_saved(filename, '-g', 'main17', status=1)
    self.assertEqual(proc.stdout, '')
    self.assertIn('Enum a => a', proc.stderr)
    self.assertIn(ORACLE_SENTENCE, proc.stderr)
    proc = self.run_saved(filename, '--help')
    self.assertIn('usage: %s.py' % MODULE, proc.stdout)
    self.assertIn('-g', proc.stdout)
    self.assertNotIn('NAME', proc.stdout)
    # No file name, no backend switch: the file is the module.
    self.run_saved(filename, 'extra', status=2)
    self.run_saved(filename, '-b', 'cxx', status=2)

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
    self.assertEqual(Main.goal_from_scheme(self.M.main33, goals.flat_type_text(self.M.main33.scheme)), self.M.main33)

  def test_library(self):
    '''
    module_main=False saves the module without a main program, on both
    backends: no moduleMain in the Python form, no entry point in the C++
    form.
    '''
    filename = os.path.join(self.tmpdir, MODULE + ('.cpp' if IS_CXX else '.py'))
    curry.save(self.M, filename, module_main=False)
    with open(filename, encoding='utf-8') as stream:
      saved = stream.read()
    text = curry.save(self.M, module_main=False)
    for form in [saved, text, inspect.getimpl(self.M)]:
      self.assertNotIn('moduleMain', form)
      self.assertNotIn('void entry()', form)
      if IS_CXX:
        self.assertIn('/* SECTION: .header */', form)
      else:
        self.assertIn('IModule.fromBOM', form)
    if IS_CXX:
      self.assertIn('void entry()', curry.save(self.M, goal='main14'))
