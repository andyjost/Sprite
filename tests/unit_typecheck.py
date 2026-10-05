'''
The engine of the typed boundary, item Y6 (#55, epic #48).

``curry.typecheck.engine`` types one Python-built expression over the
schemes of the front end: union-find type variables, unification with an
occurs check and the rule for ``Prelude.Apply``, the normalization of an
``Apply`` whose head became a constructor, context reduction through the
instance contexts, the defaulting of the front end for ambiguous numeric
variables, the table of the PAKCS REPL, the resolution of every predicate
to a dictionary term, newtype constructors erased, the ``exprtype`` parser
with the synonyms of the ``.icurry`` interfaces, and the error catalogue.
The reference materializer builds the node of a solved problem through
``raw_expr``; the tests evaluate it on the backend of the process.  The
module of the tests is data/curry/TypeCheck.curry.
'''
import cytest # from ./lib; must be first
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import engine, errors, exprtype, instances, sigtable, terms, unify
from curry.typecheck.defaulting import DefaultingError, ORACLE_SENTENCE
from curry.typecheck.engine import (
    App, Free, Iter, Known, List, Lit, Problem, Tuple, Typed, describe
  )
from curry.typecheck.instances import DictTerm, InstanceEnv, Pred
from curry.typecheck.terms import Rigid, Var, tcons
from io import StringIO
import curry, os, re, unittest

GOLDENS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'goal_defaulting'
  )
IS_CXX = curry.flags['backend'] == 'cxx'
MODULE = 'TypeCheck'

def P(name):
  return curry.symbol('Prelude.' + name)

def problem(*args, **kwds):
  '''A problem over the arguments of ``curry.expr``, typed and not solved.'''
  return Problem(curry.getInterpreter(), engine.spec_of(*args), **kwds)

def solved(*args, **kwds):
  return problem(*args, **kwds).solve()

def build(*args, **kwds):
  return engine.build(curry.getInterpreter(), *args, **kwds)

def floats(text):
  '''
  A value text with the floats in the format of the Python backend.  The
  C++ backend prints 1.5 as 1.5000000000000000 (issue #34).
  '''
  return re.sub(r'(\d\.\d*?)0+(?!\d)', lambda m: m.group(1) if not m.group(1).endswith('.') else m.group(1) + '0', text)

def values(*args, **kwds):
  '''The values of the built expression, as Curry text.'''
  return [floats(str(value)) for value in curry.eval(build(*args, **kwds))]

def oracle(name, kind=''):
  '''
  The recorded output of the PAKCS REPL for a text goal of
  func_goal_defaulting.py: the lines after the header ``!goal <text>``.
  ``kind`` is ``'type'`` for the output of ``:type``.
  '''
  suffix = '.type' if kind == 'type' else ''
  path = os.path.join(GOLDENS, 'text.%s%s.au-gen' % (name, suffix))
  with open(path) as istream:
    lines = istream.read().splitlines()
  assert lines[0].startswith('!goal ')
  return '\n'.join(lines[1:]).strip()

def squeeze(text):
  '''A type text without its spaces, for a comparison with the oracle.'''
  return re.sub(r'\s+', '', text)

def dicts(prob):
  '''The dictionary terms of every application of a solved problem, as text.'''
  return [str(d) for app in prob.apps for d in app.dicts]

# Terms for the tests of the unifier.
A = lambda f, x: tcons('Apply', f, x)
INT, CHAR, BOOL, FLOAT = tcons('Int'), tcons('Char'), tcons('Bool'), tcons('Float')
MAYBE = lambda t: tcons('Maybe', t)
LIST = lambda t: tcons('[]', t)

def show(term):
  return sigtable.show_type(terms.zonk(term))

class TestUnify(cytest.TestCase):
  '''Unification with the occurs check and the Apply rule.'''

  def test_variables(self):
    a, b = Var(), Var()
    unify.unify(a, b)
    self.assertIs(a.find(), b.find())
    unify.unify(a, INT)
    self.assertEqual(terms.prune(b), INT)
    self.assertEqual(show(b), 'Int')
    # A bound variable unifies with its binding and with nothing else.
    unify.unify(b, INT)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(a, CHAR)

  def test_structures(self):
    a, b = Var(), Var()
    unify.unify(fc.FuncType(a, LIST(b)), fc.FuncType(INT, LIST(CHAR)))
    self.assertEqual((show(a), show(b)), ('Int', 'Char'))
    with self.assertRaises(unify.TypeMismatch) as cm:
      unify.unify(tcons('(,)', INT, CHAR), tcons('(,,)', INT, CHAR, BOOL))
    self.assertIsInstance(cm.exception, unify.UnifyError)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(fc.FuncType(INT, INT), INT)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(MAYBE(INT), MAYBE(CHAR))

  def test_occurs_check(self):
    a = Var()
    with self.assertRaises(unify.OccursError) as cm:
      unify.unify(a, LIST(a))
    self.assertIs(cm.exception.lhs, a)
    self.assertIsNone(a.binding)
    b = Var()
    with self.assertRaises(unify.OccursError):
      unify.unify(fc.FuncType(b, INT), fc.FuncType(MAYBE(b), INT))

  def test_apply(self):
    '''Apply f a against T a1 .. an binds f to T a1 .. a(n-1).'''
    m, a = Var(), Var()
    unify.unify(A(m, a), MAYBE(INT))
    self.assertEqual(show(m), 'Maybe')
    self.assertEqual(show(a), 'Int')
    self.assertEqual(terms.zonk(A(m, a)), MAYBE(INT))
    # whnf resolves the head alone.
    self.assertEqual(terms.whnf(A(m, a)).name, fc.prelude('Maybe'))
    # Two Apply terms unify pairwise.
    f, x, g, y = Var(), Var(), Var(), Var()
    unify.unify(A(f, x), A(g, y))
    self.assertIs(f.find(), g.find())
    self.assertIs(x.find(), y.find())
    # Either applied twice.
    e, p, q = Var(), Var(), Var()
    unify.unify(A(A(e, p), q), tcons('Either', INT, BOOL))
    self.assertEqual((show(e), show(p), show(q)), ('Either', 'Int', 'Bool'))
    # A function type is the constructor (->) with two arguments.
    m2, b = Var(), Var()
    unify.unify(A(m2, b), fc.FuncType(INT, BOOL))
    self.assertEqual(terms.prune(m2), fc.TCons(terms.ARROW, [INT]))
    self.assertEqual(show(b), 'Bool')
    # A nullary constructor is no application.
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(A(Var(), Var()), INT)
    # The other way round.
    n, c = Var(), Var()
    unify.unify(LIST(CHAR), A(n, c))
    self.assertEqual((show(n), show(c)), ('[]', 'Char'))

  def test_normalization(self):
    '''Apply of a constructor folds, up to the declared arity.'''
    m = Var()
    t = A(m, INT)
    unify.unify(m, tcons('IO'))
    self.assertEqual(terms.whnf(t), tcons('IO', INT))
    self.assertEqual(terms.zonk(t), tcons('IO', INT))
    self.assertEqual(show(t), 'IO Int')
    # With an arity function, a saturated head stays an Apply.
    arity = {'Prelude.Int': 0, 'Prelude.IO': 1}.get
    over = A(INT, INT)
    self.assertEqual(terms.whnf(over, arity), over)
    self.assertEqual(terms.whnf(A(tcons('IO'), INT), arity), tcons('IO', INT))
    self.assertEqual(terms.whnf(A(tcons('IO', INT), INT), arity), A(tcons('IO', INT), INT))
    # (->) with two arguments is a function type.
    self.assertEqual(
        terms.whnf(fc.TCons(terms.ARROW, [INT, BOOL])), fc.FuncType(INT, BOOL)
      )
    self.assertEqual(show(A(fc.TCons(terms.ARROW, [INT]), BOOL)), 'Int -> Bool')
    # A variable at the head stays an Apply.
    v = Var()
    self.assertEqual(show(A(v, INT)), 'a Int')

  def test_rigid(self):
    r, s = Rigid('a'), Rigid('b')
    unify.unify(r, r)
    v = Var()
    unify.unify(v, r)
    self.assertIs(terms.prune(v), r)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(r, s)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(r, INT)
    with self.assertRaises(unify.TypeMismatch):
      unify.unify(LIST(r), LIST(INT))
    naming = terms.Naming()
    te = terms.zonk(LIST(r), naming)
    self.assertEqual(naming.show(te), '[a]')

  def test_nested_forall(self):
    '''A nested ForallType is instantiated when the unifier reaches it.'''
    poly = fc.ForallType([(0, fc.KStar)], fc.FuncType(fc.TVar(0), fc.TVar(0)))
    v = Var()
    unify.unify(fc.FuncType(poly, INT), fc.FuncType(fc.FuncType(v, CHAR), INT))
    self.assertEqual(show(v), 'Char')
    unify.unify(poly, fc.FuncType(BOOL, BOOL))

  def test_on_bind(self):
    seen = []
    a, b = Var(), Var()
    unify.unify(fc.FuncType(a, b), fc.FuncType(INT, LIST(CHAR)), on_bind=lambda v, t: seen.append((v, t)))
    self.assertEqual([(v is a, t) for v, t in seen], [(True, INT), (False, LIST(CHAR))])

  def test_terms(self):
    a, b = Var(), Var()
    t = fc.FuncType(a, tcons('(,)', b, a))
    self.assertEqual(terms.free_vars(t), [a, b])
    self.assertFalse(terms.is_ground(t))
    self.assertTrue(terms.is_ground(MAYBE(INT)))
    self.assertTrue(terms.occurs(a, t))
    self.assertFalse(terms.occurs(Var(), t))
    self.assertEqual(show(t), 'a -> (b, a)')
    # instantiate maps the indices of a FlatCurry type to variables.
    mapping = {}
    te = terms.instantiate(fc.FuncType(fc.TVar(0), fc.TVar(1)), mapping)
    self.assertEqual(sorted(mapping), [0, 1])
    self.assertIs(te.domain, mapping[0])
    with self.assertRaises(TypeError):
      terms.instantiate(fc.KStar, {})


class TestNormalization(cytest.TestCase):
  '''return 5, fmap (+1) (Just 1), pure 1: an Apply whose head becomes a constructor.'''

  def test_return(self):
    prob = problem(P('return'), 5)
    self.assertEqual(prob.signature, '(Monad a, Num b) => a b')
    prob.solve()
    self.assertEqual(prob.defaulted_signature, 'IO Int')
    self.assertEqual(prob.typeexpr, tcons('IO', INT))
    self.assertEqual(dicts(prob), ['_inst#Prelude.Monad#Prelude.IO'])
    self.assertEqual(values(P('return'), 5), ['5'])

  def test_fmap(self):
    prob = problem(P('fmap'), [P('+'), 1], [P('Just'), 1])
    self.assertEqual(prob.signature, 'Num a => Maybe a')
    self.assertEqual(squeeze(prob.signature), squeeze(oracle('fmap', 'type')))
    prob.solve()
    self.assertEqual(prob.defaulted_signature, 'Maybe Int')
    self.assertEqual(
        dicts(prob)
      , ['_inst#Prelude.Functor#Prelude.Maybe', '_inst#Prelude.Num#Prelude.Int']
      )
    self.assertEqual(values(P('fmap'), [P('+'), 1], [P('Just'), 1]), ['Just 2'])

  def test_pure(self):
    '''pure 1 is Applicative, which the table rejects, as the oracle does; exprtype fixes it.'''
    prob = problem(P('pure'), 1)
    self.assertEqual(prob.signature, '(Applicative a, Num b) => a b')
    with self.assertRaises(DefaultingError) as cm:
      prob.solve()
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded expression 'pure 1' of type "
        "(Applicative a, Num b) => a b\n  " + ORACLE_SENTENCE + "\n"
        "  add a type annotation (exprtype)"
      )
    prob = solved(P('pure'), 1, exprtype='Maybe Int')
    self.assertEqual(prob.signature, 'Maybe Int')
    self.assertEqual(dicts(prob), ['_inst#Prelude.Applicative#Prelude.Maybe'])
    self.assertEqual(values(P('pure'), 1, exprtype='Maybe Int'), ['Just 1'])
    prob = solved(P('pure'), 1, exprtype='IO Int')
    self.assertEqual(prob.defaulted_signature, 'IO Int')
    self.assertEqual(values(P('pure'), 1, exprtype='IO Int'), ['1'])


class TestSchemes(cytest.TestCase):
  '''The schemes of fmap, >>=, return and mapM_ instantiate and unify.'''

  def test_bind(self):
    prob = solved(P('>>='), [P('Just'), 1], P('Just'))
    bind = prob.root
    self.assertIs(bind.scheme, P('>>=').scheme)
    self.assertEqual(prob.show_type_of(bind.args[0]), 'Maybe Int')
    self.assertEqual(prob.show_type_of(bind.args[1]), 'Int -> Maybe Int')
    self.assertEqual(prob.defaulted_signature, 'Maybe Int')
    self.assertEqual(dicts(prob), ['_inst#Prelude.Monad#Prelude.Maybe'])
    self.assertEqual(values(P('>>='), [P('Just'), 1], P('Just')), ['Just 1'])

  def test_mapm(self):
    prob = problem(P('mapM_'), P('print'), [1, 2])
    self.assertEqual(prob.signature, 'IO ()')
    prob.solve()
    self.assertEqual(
        dicts(prob)
      , ['_inst#Prelude.Monad#Prelude.IO', '_inst#Prelude.Show#Prelude.Int']
      )
    mapm = prob.root
    self.assertEqual(prob.show_type_of(mapm.args[0]), 'Int -> IO ()')
    self.assertEqual(prob.show_type_of(mapm.args[1]), '[Int]')
    if IS_CXX:
      self.assertEqual(values(P('mapM_'), P('print'), [1, 2]), ['()'])
    else:
      stdout = StringIO()
      curry.getInterpreter().stdout = stdout
      self.assertEqual(values(P('mapM_'), P('print'), [1, 2]), ['()'])
      self.assertEqual(stdout.getvalue(), '1\n2\n')

  def test_fmap_and_return(self):
    prob = solved(P('fmap'), P('not'), [P('return'), True], exprtype='IO Bool')
    self.assertEqual(prob.defaulted_signature, 'IO Bool')
    self.assertEqual(
        dicts(prob)
      , ['_inst#Prelude.Functor#Prelude.IO', '_inst#Prelude.Monad#Prelude.IO']
      )
    self.assertEqual(values(P('fmap'), P('not'), [P('return'), True], exprtype='IO Bool'), ['False'])
    # The kind of the variable of fmap comes from the scheme.
    prob = problem(P('fmap'))
    self.assertEqual(prob.signature, 'Functor c => (a -> b) -> c a -> c b')
    kinds = [v.kind for v in terms.free_vars(prob.root.type)]
    self.assertEqual(kinds, [fc.KStar, fc.KStar, fc.KArrow(fc.KStar, fc.KStar)])

  def test_arity_forms(self):
    '''Under-application, over-application through apply, and a method.'''
    prob = solved(P('+'), 1)
    self.assertEqual(prob.signature, 'Num a => a -> a')
    self.assertEqual(prob.defaulted_signature, 'Int -> Int')
    self.assertEqual(prob.root.scheme.arity, 1)
    self.assertEqual(values(P('apply'), [P('+'), 1], 6), ['7'])
    self.assertEqual(values(P('id'), P('not'), True), ['False'])
    self.assertEqual(values(P('const'), 1, 2), ['1'])
    self.assertEqual(solved(P('const'), 1, 2).signature, 'Num a => a')
    with self.assertRaises(errors.ArityError) as cm:
      problem(P('Just'), 1, 2)
    self.assertEqual(str(cm.exception), 'Prelude.Just :: a -> Maybe a takes 1 argument, 2 given')
    self.assertEqual((cm.exception.ntaken, cm.exception.ngiven), (1, 2))
    with self.assertRaisesRegex(errors.ArityError, r'takes 1 argument, 2 given'):
      problem(P('length'), [1], True)


class TestReduction(cytest.TestCase):
  '''Context reduction through the instance contexts.'''

  def test_show_list(self):
    prob = problem(P('show'), [1, 2])
    self.assertEqual(prob.signature, '[Char]')
    prob.solve()
    d, = prob.dictionaries(prob.root)
    self.assertIsInstance(d, DictTerm)
    self.assertEqual(d.fullname, 'Prelude._inst#Prelude.Show#[]')
    self.assertEqual([a.fullname for a in d.args], ['Prelude._inst#Prelude.Show#Prelude.Int'])
    self.assertEqual(str(d), '_inst#Prelude.Show#[] _inst#Prelude.Show#Prelude.Int')
    self.assertEqual(values(P('show'), [1, 2]), ['"[1,2]"'])
    self.assertEqual(values(P('show'), [[1], [2, 3]]), ['"[[1],[2,3]]"'])

  def test_show_maybe(self):
    prob = solved(P('show'), [P('Just'), 1])
    self.assertEqual(dicts(prob), ['_inst#Prelude.Show#Prelude.Maybe _inst#Prelude.Show#Prelude.Int'])
    self.assertEqual(values(P('show'), [P('Just'), 1]), ['"Just 1"'])
    self.assertEqual(values(P('show'), [P('Just'), [P('Just'), 'a']]), ['"Just (Just \'a\')"'])

  def test_eq_pair(self):
    prob = solved(P('=='), (1, 'a'), (2, 'b'))
    d, = prob.dictionaries(prob.root)
    self.assertEqual(
        str(d)
      , '_inst#Prelude.Eq#(,) _inst#Prelude.Eq#Prelude.Int _inst#Prelude.Eq#Prelude.Char'
      )
    self.assertEqual(values(P('=='), (1, 'a'), (2, 'b')), ['False'])
    self.assertEqual(values(P('=='), (1, 'a'), (1, 'a')), ['True'])
    # The predicates record the instance and its context.
    pred, = prob.root.preds
    self.assertEqual(pred.instance.fullname, 'Prelude._inst#Prelude.Eq#(,)')
    self.assertEqual([p.classname for p in pred.subpreds], ['Prelude.Eq', 'Prelude.Eq'])
    self.assertIs(pred.subpreds[0].parent, pred)
    self.assertIs(pred.subpreds[0].root(), pred)

  def test_no_instance(self):
    with self.assertRaises(errors.NoInstanceError) as cm:
      problem(P('show'), P('id'))
    self.assertEqual(
        str(cm.exception)
      , 'no instance for Show (a -> a) in argument 1 of Prelude.show :: Show a => a -> [Char]'
      )
    self.assertEqual(cm.exception.classname, 'Show')
    self.assertEqual(cm.exception.symbol, 'Prelude.show')
    self.assertIsInstance(cm.exception, curry.CurryTypeError)
    with self.assertRaisesRegex(
        errors.NoInstanceError
      , r'^no instance for Show \(Bool -> Bool\) in argument 1 of Prelude\.Just'
      ):
      problem(P('show'), [P('Just'), P('not')])
    with self.assertRaisesRegex(errors.NoInstanceError, r'^no instance for Num Bool'):
      problem(P('+'), True, False)

  def test_superclasses(self):
    env = InstanceEnv(curry.getInterpreter())
    supers = env.superclasses()
    self.assertEqual(supers['Prelude.Fractional'], {'Prelude.Num'})
    self.assertEqual(
        supers['Prelude.Integral']
      , {'Prelude.Real', 'Prelude.Enum', 'Prelude.Num', 'Prelude.Ord', 'Prelude.Eq'}
      )
    self.assertEqual(supers['Prelude.Monad'], {'Prelude.Applicative', 'Prelude.Functor'})
    for classname in ['Num', 'Integral', 'Fractional', 'Floating', 'Real', 'RealFrac']:
      self.assertTrue(env.is_numeric('Prelude.' + classname), classname)
    for classname in ['Show', 'Eq', 'Ord', 'Enum', 'Data', 'Monad']:
      self.assertFalse(env.is_numeric('Prelude.' + classname), classname)
    self.assertTrue(env.entails('Prelude.Ord', 'Prelude.Eq'))
    self.assertFalse(env.entails('Prelude.Eq', 'Prelude.Ord'))
    # (Num a, Fractional a) is Fractional a, as the front end prints it.
    a = Var()
    preds = [Pred('Prelude.Num', a), Pred('Prelude.Fractional', a), Pred('Prelude.Num', a)]
    self.assertEqual([p.classname for p in env.simplify(preds)], ['Prelude.Fractional'])
    b = Var()
    preds = [Pred('Prelude.Num', a), Pred('Prelude.Fractional', b)]
    self.assertEqual(len(env.simplify(preds)), 2)
    self.assertEqual(problem(P('/'), 3, 2).signature, 'Fractional a => a')

  def test_user_class(self):
    '''The instances of the test module: Pretty [a] through Pretty a.'''
    M = curry.import_(MODULE)
    prob = solved(M.pretty, [True, False])
    self.assertEqual(
        dicts(prob), ['_inst#TypeCheck.Pretty#[] _inst#TypeCheck.Pretty#Prelude.Bool']
      )
    self.assertEqual(values(M.pretty, [True, False]), ['"yesno"'])
    # No instance of Pretty at Int or Float: the variable is ambiguous.
    with self.assertRaises(errors.AmbiguousTypeError) as cm:
      solved(M.pretty, 1)
    self.assertEqual(
        cm.exception.first_line
      , 'ambiguous type in TypeCheck.pretty 1 :: (Num a, TypeCheck.Pretty a) => [Char]'
      )
    with self.assertRaisesRegex(errors.NoInstanceError, r'^no instance for Pretty Char in argument 1'):
      problem(M.pretty, 'a')

  def test_typename(self):
    env = InstanceEnv(curry.getInterpreter())
    self.assertEqual(env.typename(LIST(INT)), '[]')
    self.assertEqual(env.typename(tcons('()')), '()')
    self.assertEqual(env.typename(tcons('(,)', INT, INT)), '(,)')
    self.assertEqual(env.typename(fc.FuncType(INT, INT)), '(->)')
    self.assertEqual(env.typename(fc.TCons(terms.ARROW, [INT])), '(->)')
    self.assertEqual(env.typename(MAYBE(INT)), 'Prelude.Maybe')
    self.assertEqual(env.typename(fc.TCons(('M', 'T'), [])), 'M.T')
    self.assertIsNone(env.typename(A(Var(), INT)))
    self.assertIsNone(env.typename(Var()))


class TestDefaulting(cytest.TestCase):
  '''
  The eight cases of the PAKCS REPL, before and after defaulting.  The
  types before defaulting are compared with the recorded output of :type
  (func_goal_defaulting.py), the values with the recorded values.
  '''

  def check(self, name, before, after, value, *args):
    prob = problem(*args)
    self.assertEqual(prob.signature, before)
    self.assertEqual(squeeze(before), squeeze(oracle(name, 'type')))
    prob.solve()
    self.assertEqual(prob.defaulted_signature, after)
    self.assertEqual(values(*args), [value])
    self.assertEqual(oracle(name), value)
    return prob

  def test_plus(self):
    prob = self.check('plus', 'Num a => a', 'Int', '3', P('+'), 1, 2)
    self.assertEqual(dicts(prob), ['_inst#Prelude.Num#Prelude.Int'])
    self.assertEqual(prob.literal_type(prob.root.args[0]), INT)

  def test_divide(self):
    prob = self.check('divide', 'Fractional a => a', 'Float', '1.5', P('/'), 3, 2)
    self.assertEqual(dicts(prob), ['_inst#Prelude.Fractional#Prelude.Float'])
    self.assertEqual(prob.literal_type(prob.root.args[0]), FLOAT)

  def test_fromintegral(self):
    '''The front end defaults the ambiguous Integral variable to Int first.'''
    prob = self.check('fromintegral', 'Num a => a', 'Int', '3', P('fromIntegral'), 3)
    self.assertEqual(
        dicts(prob)
      , ['_inst#Prelude.Integral#Prelude.Int', '_inst#Prelude.Num#Prelude.Int']
      )

  def test_nil(self):
    prob = self.check('nil', '[a]', '[a]', '[]', [])
    self.assertEqual(prob.typeexpr, LIST(fc.TVar(0)))

  def test_free(self):
    '''
    A marker alone stays polymorphic: the engine route keeps a marker free
    of constraints and lets the consumers add Data where Curry adds it.
    The REPL types the text with ``let x free in x``, so its :type says
    Data a => a; its value is the variable, as here.
    '''
    x = curry.free()
    prob = problem(x)
    self.assertEqual(prob.signature, 'a')
    self.assertEqual(squeeze(oracle('free', 'type')), 'Dataa=>a')
    prob.solve()
    self.assertEqual(prob.defaulted_signature, 'a')
    self.assertEqual(str(prob.free_dictionary(prob.root)), '_inst#Prelude.Data#Prelude.Bool')
    self.assertEqual(values(x), ['_a'])
    self.assertEqual(oracle('free'), '{x=x} x')

  def test_show_nil(self):
    '''show [] is ambiguous in the front end; the engine says so too.'''
    prob = problem(P('show'), [])
    with self.assertRaises(errors.AmbiguousTypeError) as cm:
      prob.signature
    message = str(cm.exception)
    self.assertEqual(
        message.split('\n')
      , [ 'ambiguous type in show [] :: Show a => [Char]'
        , '  Ambiguous type variable a in type Show a => [Char]'
        , '  ' + ORACLE_SENTENCE
        , '  ' + errors.DEFAULTS_HINT
        ]
      )
    self.assertEqual(cm.exception.scheme, 'Show a => [Char]')
    self.assertTrue(oracle('shownil').startswith('!error'))
    self.assertIn('Ambiguous type variable', oracle('shownil'))
    self.assertIn('Ambiguous type variable', message)
    with self.assertRaises(errors.AmbiguousTypeError):
      solved(P('show'), [])

  def test_toenum(self):
    prob = problem(P('toEnum'), 65)
    self.assertEqual(prob.signature, 'Enum a => a')
    self.assertEqual(squeeze(prob.signature), squeeze(oracle('toenum', 'type')))
    with self.assertRaises(DefaultingError) as cm:
      prob.solve()
    self.assertEqual(
        str(cm.exception)
      , "cannot handle the overloaded expression 'toEnum 65' of type Enum a => a\n"
        "  " + ORACLE_SENTENCE + "\n"
        "  add a type annotation (exprtype)"
      )
    self.assertIn(ORACLE_SENTENCE, oracle('toenum'))
    self.assertIn('Overloaded type: Enum a => a', oracle('toenum'))
    self.assertEqual(values(P('toEnum'), 65, exprtype='Char'), ["'A'"])

  def test_maxbound(self):
    prob = problem(P('+'), P('maxBound'), 1)
    self.assertEqual(prob.signature, '(Bounded a, Num a) => a')
    self.assertEqual(squeeze(prob.signature), squeeze(oracle('maxbound', 'type')))
    with self.assertRaisesRegex(
        DefaultingError
      , r"^cannot handle the overloaded expression 'maxBound \+ 1' of type "
        r"\(Bounded a, Num a\) => a\n"
      ):
      prob.solve()
    self.assertIn('Overloaded type: (Bounded a, Num a) => a', oracle('maxbound'))

  def test_more_table_rows(self):
    '''The other goals of the parity suite, through the engine.'''
    cases = [
        ('choice', 'Num a => a', ['1', '2'], (P('?'), 1, 2))
      , ('floats', 'Fractional a => [a]', ['[1.0, 2.5]'], ([1, 2.5],))
      , ('just', 'Num a => Maybe a', ['Just 5'], (P('Just'), 5))
      , ('pair', 'Num a => (a, Char)', ["(1, 'a')"], ((1, 'a'),))
      , ('power', 'Num a => a', ['8'], (P('^'), 2, 3))
      , ('show', '[Char]', ['"3"'], (P('show'), [P('+'), 1, 2]))
      , ('enumfrom', '(Enum a, Num a) => [a]', ['[1, 2, 3]'], (P('take'), 3, [P('enumFrom'), 1]))
      , ('id', 'a -> a', ['id'], (P('id'),))
      ]
    for name, before, expected, args in cases:
      prob = problem(*args)
      self.assertEqual(prob.signature, before, name)
      self.assertEqual(squeeze(before), squeeze(oracle(name, 'type')), name)
      self.assertEqual(values(*args), expected, name)
    # Data alone defaults to Bool; Data with Num follows Num.
    prob = solved(P('=:='), curry.free(), curry.free())
    self.assertEqual(prob.signature, 'Data a => Bool')
    self.assertEqual(dicts(prob), ['_inst#Prelude.Data#Prelude.Bool'])
    self.assertEqual(values(P('=:='), curry.free(), curry.free()), ['True'])
    prob = solved(P('=:='), curry.free(), 1)
    self.assertEqual(prob.signature, '(Data a, Num a) => Bool')
    self.assertEqual(dicts(prob), ['_inst#Prelude.Data#Prelude.Int'])
    self.assertEqual(prob.defaulting[0].substitution, {0: 'Int'})

  def test_what_and_hint(self):
    '''The caller names the expression and the hint of the table's error.'''
    with self.assertRaises(DefaultingError) as cm:
      solved(P('toEnum'), 65, what='goal g', hint='give g a signature')
    self.assertEqual(
        str(cm.exception)
      , 'cannot handle the overloaded goal g of type Enum a => a\n  '
        + ORACLE_SENTENCE + '\n  give g a signature'
      )
    self.assertEqual(str(problem(P('toEnum'), 65).what), "expression 'toEnum 65'")
    self.assertEqual(problem(P('toEnum'), 65, what='goal g').what, 'goal g')
    # A long description is cut.
    prob = problem(P('show'), list(range(40)))
    self.assertEqual(len(str(prob.what)), engine.WHAT_WIDTH + len("expression ''"))
    self.assertTrue(str(prob.what).endswith("...'"))

  def test_read(self):
    '''read "5" is Read a => a; the table rejects it, as the oracle does.'''
    with self.assertRaisesRegex(
        DefaultingError, r"^cannot handle the overloaded expression 'read \"5\"' of type Read a => a\n"
      ):
      solved(P('read'), '5')
    self.assertEqual(values(P('read'), '5', exprtype='Int'), ['5'])
    self.assertEqual(dicts(solved(P('read'), '5', exprtype='Int')), ['_inst#Prelude.Read#Prelude.Int'])

  def test_show_return(self):
    '''show (return 1): the monad is ambiguous, as in the front end.'''
    with self.assertRaises(errors.AmbiguousTypeError) as cm:
      solved(P('show'), [P('return'), 1])
    self.assertEqual(
        cm.exception.first_line
      , 'ambiguous type in show (return 1) :: (Monad a, Show (a Int)) => [Char]'
      )
    # Through a free marker the monad is in the environment: the table binds
    # it to IO, and Show (IO Int) has no instance.
    x = curry.free()
    with self.assertRaisesRegex(errors.NoInstanceError, r'^no instance for Show \(IO Int\)'):
      solved(P('show'), [P('>>='), x, P('return')], exprtype='[Char]') if False else \
          solved(P('show'), [P('>>'), x, [P('return'), 1]])


class TestConversionRules(cytest.TestCase):
  '''The rows of the conversion table that the engine decides.'''

  def test_int(self):
    self.assertEqual(solved(P('plusInt'), 1, 2).literal_type(problem(1).root), fc.TVar(0))
    prob = solved(P('+'), 1.5, 1)
    self.assertEqual(prob.literal_type(prob.root.args[1]), FLOAT)
    self.assertEqual(values(P('+'), 1.5, 1), ['2.5'])
    self.assertEqual(values(P('+'), 1, 2), ['3'])
    with self.assertRaises(errors.ConversionError) as cm:
      problem(P('not'), 1)
    self.assertEqual(str(cm.exception), 'cannot convert 1 to Bool at argument 1 of Prelude.not :: Bool -> Bool')
    self.assertEqual(cm.exception.value, 1)
    self.assertEqual(cm.exception.expected, BOOL)
    with self.assertRaisesRegex(errors.ConversionError, r"^cannot convert 1 to Char at argument 1 of Prelude.ord"):
      problem(P('ord'), 1)
    # The C++ Int has 64 bits.
    self.assertEqual(values(P('+'), 2**40, 1), [str(2**40 + 1)])

  def test_int_at_user_type(self):
    '''An int at a type with a Num instance of its own goes through fromInt.'''
    M = curry.import_(MODULE)
    prob = solved(M.toInt, 3)
    lit = prob.root.args[0]
    self.assertEqual(prob.show_type_of(lit), 'TypeCheck.Nat')
    self.assertEqual(str(prob.literal_dictionary(lit)), '_inst#Prelude.Num#TypeCheck.Nat')
    self.assertEqual(values(M.toInt, 3), ['3'])
    self.assertEqual(values(P('+'), [M.S, M.Z], 2), ['S (S (S Z))'])
    self.assertEqual(values(M.twice, [M.S, M.Z]), ['S (S Z)'])
    self.assertEqual(values(M.twice, 2.5), ['5.0'])
    self.assertIsNone(solved(True).literal_dictionary(problem(True).root))

  def test_float(self):
    with self.assertRaises(errors.ConversionError) as cm:
      problem(P('plusInt'), 1, 2.5)
    self.assertEqual(
        str(cm.exception)
      , 'cannot convert 2.5 to Int at argument 2 of Prelude.plusInt :: Int -> Int -> Int'
      )
    self.assertEqual(cm.exception.where, 'argument 2 of Prelude.plusInt :: Int -> Int -> Int')
    self.assertEqual(cm.exception.symbol, 'Prelude.plusInt')
    self.assertEqual(values(P('show'), 1.5), ['"1.5"'])
    self.assertEqual(solved(1.5).signature, 'Fractional a => a')
    self.assertEqual(solved(1.5).defaulted_signature, 'Float')

  def test_bool(self):
    self.assertEqual(solved(True).signature, 'Bool')
    self.assertEqual(values(P('not'), False), ['True'])
    with self.assertRaisesRegex(errors.MismatchError, r'argument 2 has type Bool \(from True\)'):
      problem(P('+'), 1, True)
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert True to Int'):
      problem(P('plusInt'), 1, True)

  def test_str(self):
    '''A one-character string is Char unless a list is expected.'''
    self.assertEqual(solved('a').signature, 'Char')
    self.assertEqual(solved('ab').signature, '[Char]')
    self.assertEqual(solved('').signature, '[Char]')
    self.assertEqual(values(P('length'), 'a'), ['1'])
    self.assertEqual(values(P('ord'), 'a'), ['97'])
    self.assertEqual(values(P('head'), 'a'), ["'a'"])
    self.assertEqual(values(P('length'), b'ab'), ['2'])
    self.assertEqual(values(''), ['[]'])
    self.assertEqual(values(P('++'), 'a', 'bc'), ['"abc"'])
    self.assertEqual(values(['ab', 'c']), ['["ab", "c"]'])
    # A one-character string under an open type is a weak mark for Char: a
    # string beside it makes the list [[Char]] in either order, a type that
    # only a list can fill makes it a string, and a type that is neither
    # Char nor a list is an error that names the part that fixed it.
    self.assertEqual(values(['a', 'bc']), ['["a", "bc"]'])
    self.assertEqual(values(P('?'), 'a', 'bc'), ['"a"', '"bc"'])
    self.assertEqual(values(P('fmap'), P('ord'), 'a'), ['[97]'])
    self.assertEqual(solved(('a', 'bc')).signature, '(Char, [Char])')
    self.assertEqual(solved(P('Just'), 'a').signature, 'Maybe Char')
    with self.assertRaisesRegex(
        errors.ConversionError
      , r"^cannot convert 'a' to Bool at element 1 of the list in the expression\n"
        r"  element 2 of the list has type Bool \(from True\)$"
      ):
      problem(['a', True])
    with self.assertRaisesRegex(
        errors.ConversionError
      , r"^cannot convert 'a' to Bool at argument 1 of Prelude\.\+ :: Num a => a -> a -> a\n"
        r"  argument 2 has type Bool \(from True\)$"
      ):
      problem(P('+'), 'a', True)
    DM = curry.module('Data.Maybe')
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert "a" to Maybe a at argument 1'):
      problem(DM.fromJust, 'a')
    with self.assertRaisesRegex(errors.ConversionError, r"^cannot convert 'a' to Int at argument 1 of Prelude.plusInt"):
      problem(P('plusInt'), 'a', 1)
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert "" to \[Int\] at the expression'):
      problem('', exprtype='[Int]')

  def test_none(self):
    with self.assertRaises(errors.ConversionError) as cm:
      problem(P('Just'), None)
    self.assertEqual(
        str(cm.exception)
      , 'cannot convert None at argument 1 of Prelude.Just :: a -> Maybe a; expected a'
      )
    self.assertIsNone(cm.exception.value)
    with self.assertRaises(errors.ConversionError) as cm:
      problem(curry.module('Data.Maybe').fromJust, None)
    self.assertEqual(
        str(cm.exception)
      , 'cannot convert None at argument 1 of Data.Maybe.fromJust :: Maybe a -> a; '
        'expected Maybe a\n  Prelude.Nothing is the empty value of Maybe'
      )
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert None at the expression; expected a Curry value'):
      problem(None)

  def test_list_and_tuple(self):
    prob = problem([1, 2.5])
    self.assertEqual(prob.signature, 'Fractional a => [a]')
    prob.solve()
    self.assertEqual(prob.defaulted_signature, '[Float]')
    self.assertEqual(prob.show_type_of(prob.root.items[0]), 'Float')
    self.assertEqual(values([1, 2.5]), ['[1.0, 2.5]'])
    self.assertEqual(values([1, 2.5], exprtype='[Float]'), ['[1.0, 2.5]'])
    with self.assertRaises(errors.MismatchError) as cm:
      problem([1, 'a'])
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'type mismatch in element 2 of the list in the expression'
        , '  element 1 of the list fixed the type Int (from 1)'
        , "  element 2 of the list has type Char (from 'a')"
        ]
      )
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert 1 to Bool at element 2 of the list'):
      problem([True, 1])
    self.assertEqual(solved((1, 'a')).signature, 'Num a => (a, Char)')
    self.assertEqual(values(()), ['()'])
    self.assertEqual(values(P('fst'), (1, True)), ['1'])
    with self.assertRaisesRegex(errors.ConversionError, r'^Curry has no 1-tuple'):
      problem((1,))
    with self.assertRaises(errors.MismatchError) as cm:
      problem(P('fst'), (1, 2, 3))
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'type mismatch in argument 1 of Prelude.fst :: (a, b) -> a'
        , '  expected (a, b)'
        , '  argument 1 has type (a, b, c) (from (1, 2, 3))'
        ]
      )
    # A list of 300 elements types and builds without recursion.
    self.assertEqual(solved(list(range(300))).defaulted_signature, '[Int]')
    self.assertEqual(values(P('length'), list(range(300))), ['300'])

  def test_iterator(self):
    '''The element type of an iterator is fixed by the context or the table.'''
    DL = curry.module('Data.List')
    prob = solved(DL.sum, iter([1, 2]))
    self.assertEqual(prob.signature, 'Num a => a')
    self.assertEqual(prob.show_type_of(prob.root.args[0]), '[Int]')
    self.assertEqual(values(DL.sum, iter([1, 2])), ['3'])
    prob = solved(P('length'), iter([1, 2, 3]))
    self.assertEqual(prob.show_type_of(prob.root.args[0]), '[a]')
    self.assertEqual(values(P('length'), iter([1, 2, 3])), ['3'])
    prob = solved(P('map'), P('not'), iter([True]))
    self.assertEqual(prob.show_type_of(prob.root.args[1]), '[Bool]')

  def test_known(self):
    '''A value with a type the caller supplies.'''
    DL = curry.module('Data.List')
    node = curry.raw_expr([1.5, 2.5])
    prob = solved(DL.sum, Known('[Float]', node))
    self.assertEqual(prob.signature, 'Float')
    self.assertEqual(dicts(prob), ['_inst#Prelude.Num#Prelude.Float'])
    self.assertEqual(values(DL.sum, Known('[Float]', node)), ['4.0'])
    self.assertEqual(values(P('+'), Known(INT, curry.raw_expr(3)), 4), ['7'])
    # The variables of a known type belong to the environment: no defaulting.
    prob = solved(Known('Maybe a', curry.raw_expr([P('Just'), 1])))
    self.assertEqual(prob.defaulted_signature, 'Maybe a')
    self.assertEqual(values(Known('Maybe a', curry.raw_expr([P('Just'), 1]))), ['Just 1'])
    with self.assertRaisesRegex(
        errors.ConversionError
      , r'^cannot convert 1\.5 to Int at argument 2 of Prelude\.\+ :: Num a => a -> a -> a\n'
        r'  argument 1 fixed a := Int \(from <value>\)$'
      ):
      problem(P('+'), Known(INT, curry.raw_expr(3)), 1.5)
    with self.assertRaisesRegex(curry.CurryTypeError, r'Known\(typeexpr, node\)'):
      engine.spec_of(curry.raw_expr(3))

  def test_typed(self):
    '''A nested annotation.'''
    self.assertEqual(values(P('+'), Typed(1, 'Float'), 2), ['3.0'])
    self.assertEqual(solved(P('+'), Typed(1, 'Float'), 2).defaulted_signature, 'Float')
    self.assertEqual(values(P('length'), Typed('a', 'String')), ['1'])
    with self.assertRaises(errors.ExprTypeMismatchError) as cm:
      problem(P('+'), Typed(1, 'Float'), Typed(2, 'Int'))
    self.assertEqual(str(cm.exception), 'exprtype Int does not match the inferred type Float')
    self.assertEqual(cm.exception.text, 'Int')
    self.assertEqual(describe(Typed(1, 'Float')), '(1 :: Float)')


class TestFreeVariables(cytest.TestCase):
  '''Free markers: one variable per marker, the Data dictionary of its type.'''

  def test_data_dictionaries(self):
    x = curry.free()
    prob = solved(P('=:='), x, [1, 2])
    self.assertEqual(prob.signature, '(Data a, Num a) => Bool')
    free = prob.root.args[0]
    self.assertIsInstance(free, Free)
    self.assertEqual(prob.show_type_of(free), '[Int]')
    self.assertEqual(
        str(prob.free_dictionary(free)), '_inst#Prelude.Data#[] _inst#Prelude.Data#Prelude.Int'
      )
    self.assertEqual(values(P('=:='), x, [1, 2]), ['True'])
    # A type with a polymorphic part gets the placeholder inside.
    y = curry.free()
    prob = solved(P('length'), [y])
    self.assertEqual(prob.show_type_of(prob.root.args[0].items[0]), 'a')
    self.assertEqual(
        str(prob.free_dictionary(prob.root.args[0].items[0])), '_inst#Prelude.Data#Prelude.Bool'
      )
    prob = solved(curry.free(), exprtype='[Int]')
    self.assertEqual(str(prob.free_dictionary(prob.root)), '_inst#Prelude.Data#[] _inst#Prelude.Data#Prelude.Int')
    self.assertEqual(values(curry.free(), exprtype='[Int]'), ['_a'])

  def test_one_variable_per_marker(self):
    x = curry.free()
    prob = solved(P('&&'), [P('=:='), x, 1], [P('=:='), x, 1])
    frees = [spec for spec in prob.specs if isinstance(spec, Free)]
    self.assertEqual(len(frees), 2)
    self.assertIs(frees[0].type.find(), frees[1].type.find())
    node = engine.materialize(prob)
    self.assertEqual([str(v) for v in curry.eval(node)], ['True'])
    self.assertEqual(values(P('&&'), [P('=:='), x, 1], [P('=:='), x, 2]), [])
    # The marker keeps its node across materializations.
    z = curry.free()
    node1 = build(P('id'), z)
    self.assertIs(z._shared(curry.getInterpreter()), node1.successors[0] if not IS_CXX else z._shared(curry.getInterpreter()))
    node2 = build(P('id'), z)
    self.assertEqual(str(node2), str(node1))
    # An anonymous Free spec is a variable of its own.
    prob = solved(Tuple([Free(), Free()]))
    self.assertEqual(prob.signature, '(a, b)')
    self.assertEqual(values((curry.free(), curry.free())), ['(_a, _b)'])

  def test_function_type(self):
    with self.assertRaises(errors.FreeFunctionError) as cm:
      problem(P('map'), curry.free(), [1, 2])
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'free variable at argument 1 of Prelude.map :: (a -> b) -> [a] -> [b] '
          'would have the function type a -> b'
        , '  Curry free variables must have a Data type'
        ]
      )
    self.assertEqual(cm.exception.actual, fc.FuncType(fc.TVar(0), fc.TVar(1)))
    x = curry.free()
    with self.assertRaisesRegex(errors.FreeFunctionError, r'would have the function type Bool -> Bool'):
      problem(P('?'), x, P('not'))
    with self.assertRaisesRegex(errors.NoInstanceError, r'^no instance for Data \(a -> b\) in the expression'):
      problem(P('unknown'), 1)

  def test_occurs_in_expression(self):
    x = curry.free()
    with self.assertRaises(errors.MismatchError) as cm:
      problem(P('=:='), x, [P('Just'), x])
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'type mismatch in argument 1 of Prelude.Just :: a -> Maybe a'
        , '  the type a would contain itself in Maybe a'
        ]
      )

  def test_unknown_symbol(self):
    '''Prelude.unknown as a symbol is a Data-constrained goal: Bool.'''
    prob = solved(P('unknown'))
    self.assertEqual(prob.signature, 'Data a => a')
    self.assertEqual(prob.defaulted_signature, 'Bool')
    self.assertEqual(values(P('unknown')), ['_a'])
    self.assertEqual(values(P('=:='), [P('unknown')], 'a'), ['True'])


class TestExprType(cytest.TestCase):
  '''The parser of exprtype strings.'''

  def parse(self, text, module=None):
    te, names = exprtype.parse_type(curry.getInterpreter(), text, module)
    return sigtable.show_type(te, names=names), te

  def test_prelude_types(self):
    self.assertEqual(self.parse('String')[1], LIST(CHAR))
    self.assertEqual(self.parse('Int')[1], INT)
    self.assertEqual(self.parse('Maybe Int')[1], MAYBE(INT))
    self.assertEqual(self.parse('[a]')[1], LIST(fc.TVar(0)))
    self.assertEqual(self.parse('(a, b)')[1], tcons('(,)', fc.TVar(0), fc.TVar(1)))
    self.assertEqual(self.parse('()')[1], tcons('()'))
    self.assertEqual(self.parse('Int -> Bool')[1], fc.FuncType(INT, BOOL))
    self.assertEqual(self.parse('(Int -> Bool) -> [Int] -> Int')[0], '(Int -> Bool) -> [Int] -> Int')
    self.assertEqual(self.parse('IO ()')[0], 'IO ()')
    self.assertEqual(self.parse('Maybe (Int -> Int)')[0], 'Maybe (Int -> Int)')
    self.assertEqual(self.parse('Prelude.Maybe Int')[0], 'Maybe Int')
    self.assertEqual(self.parse('m a')[1], A(fc.TVar(0), fc.TVar(1)))
    self.assertEqual(self.parse('m a b')[0], 'm a b')
    self.assertEqual(self.parse('(m a) b')[0], 'm a b')
    self.assertEqual(self.parse('ShowS')[0], '[Char] -> [Char]')
    self.assertEqual(self.parse('ReadS Int')[0], '[Char] -> [(Int, [Char])]')
    self.assertEqual(self.parse('FilePath')[0], '[Char]')
    self.assertEqual(self.parse(' [ Int ] ')[0], '[Int]')
    self.assertEqual(self.parse('Either Int (Maybe a)')[0], 'Either Int (Maybe a)')
    # A higher-kinded argument may be a partial constructor.
    _, te = self.parse('Either Maybe Int')
    self.assertEqual(te, tcons('Either', tcons('Maybe'), INT))
    self.assertEqual(exprtype.parse_type(curry.getInterpreter(), '(a, b) -> a')[1], {0: 'a', 1: 'b'})

  def test_user_synonyms(self):
    '''The synonyms of the test module come from its .icurry interface.'''
    M = curry.import_(MODULE)
    interp = curry.getInterpreter()
    syns = exprtype.synonyms_of(interp, MODULE)
    self.assertEqual(sorted(syns), ['Name', 'Names', 'Pair', 'Table'])
    self.assertEqual(syns['Pair'].params, ('a',))
    self.assertEqual(syns['Pair'].text, '(a, a)')
    self.assertEqual(syns['Table'].arity, 2)
    self.assertEqual(syns['Names'].text, '[[Prelude.Char]]')
    self.assertEqual(self.parse('Pair Int')[0], '(Int, Int)')
    self.assertEqual(self.parse('Table Int Bool')[0], '[(Int, Bool)]')
    self.assertEqual(self.parse('Names')[0], '[[Char]]')
    self.assertEqual(self.parse('Name')[1], LIST(CHAR))
    self.assertEqual(self.parse('TypeCheck.Pair Bool')[0], '(Bool, Bool)')
    self.assertEqual(self.parse('Pair (Pair a)')[0], '((a, a), (a, a))')
    self.assertEqual(self.parse('Wrap (Wrap a)')[0], 'TypeCheck.Wrap (TypeCheck.Wrap a)')
    self.assertEqual(self.parse('Nat', module=MODULE)[1], fc.TCons((MODULE, 'Nat'), []))
    self.assertEqual(
        self.parse('Identity Int')[1]
      , fc.TCons(('Data.Functor.Identity', 'Identity'), [INT])
      )
    self.assertEqual(sorted(exprtype.synonyms_of(interp, 'Prelude')), ['DET', 'FilePath', 'ReadS', 'ShowS', 'String', 'Success'])
    path = interp.sigtable.interface_filename(MODULE)
    self.assertEqual(exprtype.icurry_filename(path), path[:-5] + '.icurry')
    self.assertTrue(os.path.isfile(exprtype.icurry_filename(path)))
    self.assertEqual(exprtype.synonyms_of(interp, 'Data.Maybe'), {})
    # exprtype on an expression, with a synonym.
    self.assertEqual(values((1, 2), exprtype='Pair Int'), ['(1, 2)'])
    self.assertEqual(solved((1, 2), exprtype='Pair Int').signature, '(Int, Int)')
    self.assertEqual(values(M.swap, (1, 2)), ['(2, 1)'])
    self.assertEqual(values(M.lookupName, 1, [(1, 'x')]), ["Just 'x'"])

  def test_context_rejected(self):
    with self.assertRaises(errors.ContextInExprTypeError) as cm:
      self.parse('Num a => a')
    self.assertEqual(
        str(cm.exception)
      , "exprtype takes a type without a context; the context is inferred (exprtype 'Num a => a')"
      )
    self.assertTrue(cm.exception.first_line.startswith('exprtype takes a type without a context'))
    with self.assertRaises(errors.ContextInExprTypeError):
      problem(1, exprtype='(Num a, Show a) => a')
    self.assertIsInstance(cm.exception, curry.CurryTypeError)

  def test_unknown_constructor(self):
    curry.import_(MODULE)
    with self.assertRaises(errors.UnknownTypeConstructorError) as cm:
      self.parse('Foo')
    self.assertRegex(
        str(cm.exception)
      , r'^unknown type constructor Foo; searched the interfaces of Prelude, .*TypeCheck.*; '
        r'curry\.compile\(\.\.\., exprtype=\.\.\.\) accepts any Curry type$'
      )
    self.assertEqual(cm.exception.name, 'Foo')
    self.assertIn('Prelude', cm.exception.searched)
    self.assertIn(MODULE, cm.exception.searched)
    with self.assertRaisesRegex(
        errors.UnknownTypeConstructorError, r'^unknown type constructor Prelude\.Foo; searched the interfaces of Prelude;'
      ):
      self.parse('Prelude.Foo')
    with self.assertRaisesRegex(
        errors.UnknownTypeConstructorError, r'the module NoSuchModule is not loaded'
      ):
      self.parse('NoSuchModule.T')
    with self.assertRaisesRegex(errors.UnknownTypeConstructorError, r'^unknown type constructor Foo'):
      problem(P('Just'), 1, exprtype='Maybe Foo')

  def test_syntax_errors(self):
    cases = [
        ('[Int', "cannot parse exprtype '[Int': expected ']', found end of text at column 5")
      , ('Int ->', "cannot parse exprtype 'Int ->': expected a type, found end of text at column 7")
      , ('(Int,)', "cannot parse exprtype '(Int,)': expected a type, found ')' at column 6")
      , ('a :: Int', "cannot parse exprtype 'a :: Int': unexpected '::' at column 3")
      , ('Int Int', None)
      , ('[] Int', "cannot parse exprtype '[] Int': '[' takes no type argument at column 1")
      , ('Int)', "cannot parse exprtype 'Int)': unexpected ')' at column 4")
      , ('a!', "cannot parse exprtype 'a!': unexpected '!' at column 2")
      , ('', "cannot parse exprtype '': expected a type, found end of text at column 1")
      ]
    for text, expected in cases:
      with self.assertRaises(errors.ExprTypeError) as cm:
        self.parse(text)
      if expected is not None:
        self.assertEqual(str(cm.exception), expected, text)
        self.assertEqual(cm.exception.text, text)
    with self.assertRaises(errors.ExprTypeSyntaxError) as cm:
      self.parse('[Int')
    self.assertEqual(cm.exception.column, 5)

  def test_kind_errors(self):
    curry.import_(MODULE)
    for text, name, arity, ngiven in [
        ('Maybe Int Int', 'Maybe', 1, 2)
      , ('Maybe', 'Maybe', 1, 0)
      , ('Either Int', 'Either', 2, 1)
      , ('Pair', 'Pair', 1, 0)
      , ('Pair Int Int', 'Pair', 1, 2)
      , ('String Int', 'String', 0, 1)
      , ('Int -> Maybe', 'Maybe', 1, 0)
      ]:
      with self.assertRaises(errors.KindError) as cm:
        self.parse(text)
      self.assertEqual(
          str(cm.exception)
        , '%s takes %d type argument%s, %d given in exprtype %r'
              % (name, arity, '' if arity == 1 else 's', ngiven, text)
        )
      self.assertEqual(
          (cm.exception.name, cm.exception.arity, cm.exception.ngiven)
        , (name, arity, ngiven)
        )

  def test_rigid_variables(self):
    '''The variables of exprtype are rigid: [1, 2] under [a] is a mismatch.'''
    with self.assertRaises(errors.ExprTypeMismatchError) as cm:
      problem([1, 2], exprtype='[a]')
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'exprtype [a] does not match the inferred type Num a => [a]'
        , '  the type variable a of exprtype is rigid; the expression needs Num a'
        ]
      )
    self.assertEqual(cm.exception.text, '[a]')
    with self.assertRaises(errors.ExprTypeMismatchError) as cm:
      problem(P('Just'), 5, exprtype='Int')
    self.assertEqual(str(cm.exception), 'exprtype Int does not match the inferred type Maybe a')
    self.assertEqual(cm.exception.inferred, 'Maybe a')
    with self.assertRaisesRegex(errors.ExprTypeMismatchError, r'^exprtype \[a\] does not match the inferred type \[Char\]'):
      problem('ab', exprtype='[a]')
    with self.assertRaisesRegex(errors.ExprTypeMismatchError, r'^exprtype a -> a does not match the inferred type Bool -> Bool'):
      problem(P('not'), exprtype='a -> a')
    # A polymorphic expression fits a rigid variable.
    self.assertEqual(solved(P('id'), exprtype='a -> a').signature, 'a -> a')
    self.assertEqual(solved([], exprtype='[a]').defaulted_signature, '[a]')
    self.assertEqual(values([], exprtype='[Int]'), ['[]'])
    self.assertEqual(values('a', exprtype='String'), ['"a"'])
    self.assertEqual(values('a', exprtype='Char'), ["'a'"])
    self.assertEqual(values(P('Just'), 5, exprtype='Maybe Float'), ['Just 5.0'])
    self.assertEqual(values(5, exprtype='Float'), ['5.0'])
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert 5 to \(Int, Int\) at the expression'):
      problem(5, exprtype='(Int, Int)')


class TestNewtypes(cytest.TestCase):
  '''A newtype constructor is built as its argument, a bare one as id.'''

  def test_identity(self):
    ID = curry.import_('Data.Functor.Identity')
    prob = problem(ID.Identity, 5)
    self.assertTrue(prob.root.erased)
    self.assertEqual(prob.signature, 'Num a => Data.Functor.Identity.Identity a')
    prob.solve()
    self.assertEqual(prob.defaulted_signature, 'Data.Functor.Identity.Identity Int')
    node = engine.materialize(prob)
    self.assertEqual(str(node), '5')
    self.assertEqual([str(v) for v in curry.eval(node)], ['5'])
    self.assertEqual(values(ID.Identity, 5), ['5'])
    self.assertEqual(str(build(ID.Identity)), 'id')
    self.assertEqual(values(ID.runIdentity, [ID.Identity, 5]), ['5'])
    self.assertEqual(values(P('fmap'), [P('+'), 1], [ID.Identity, 5]), ['6'])
    self.assertEqual(values(P('apply'), ID.Identity, True), ['True'])
    M = curry.import_(MODULE)
    self.assertEqual(values(M.runTwice, [ID.Identity, [ID.Identity, 5]]), ['5'])

  def test_user_newtype(self):
    M = curry.import_(MODULE)
    prob = solved(M.Wrap, True)
    self.assertTrue(prob.root.erased)
    self.assertEqual(prob.defaulted_signature, 'TypeCheck.Wrap Bool')
    self.assertEqual(str(build(M.Wrap, True)), 'True')
    self.assertEqual(values(M.unwrap, [M.Wrap, 3]), ['3'])
    self.assertEqual(values(M.wrapTwice, 3), ['3'])
    self.assertEqual(values(M.unwrap, [M.unwrap, [M.wrapTwice, 'a']]), ["'a'"])
    # A data constructor is not erased.
    self.assertFalse(solved(M.S, M.Z).root.erased)
    self.assertFalse(solved(P('Just'), 1).root.erased)
    with self.assertRaisesRegex(errors.ConversionError, r'^cannot convert 1 to Bool at argument 1 of TypeCheck.Wrap'):
      problem(M.Wrap, 1, exprtype='Wrap Bool')


class TestErrors(cytest.TestCase):
  '''The catalogue: the first line and the attributes of each error.'''

  def test_mismatch(self):
    with self.assertRaises(errors.MismatchError) as cm:
      problem(P('+'), 1, 'a')
    err = cm.exception
    self.assertEqual(
        str(err).split('\n')
      , [ 'type mismatch in argument 2 of Prelude.+ :: Num a => a -> a -> a'
        , '  argument 1 fixed a := Int (from 1)'
        , "  argument 2 has type Char (from 'a')"
        ]
      )
    self.assertEqual(err.first_line, 'type mismatch in argument 2 of Prelude.+ :: Num a => a -> a -> a')
    self.assertEqual(err.where, 'argument 2 of Prelude.+ :: Num a => a -> a -> a')
    self.assertEqual(err.symbol, 'Prelude.+')
    self.assertEqual((err.expected, err.actual), (INT, CHAR))
    # A literal under a type an earlier argument fixed: a conversion error
    # that names that argument.
    with self.assertRaises(errors.ConversionError) as cm:
      problem(P('?'), True, 'a')
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ "cannot convert 'a' to Bool at argument 2 of Prelude.? :: a -> a -> a"
        , '  argument 1 fixed a := Bool (from True)'
        ]
      )
    with self.assertRaises(errors.MismatchError) as cm:
      problem(P('?'), True, P('not'))
    self.assertEqual(
        str(cm.exception).split('\n')
      , [ 'type mismatch in argument 2 of Prelude.? :: a -> a -> a'
        , '  argument 1 fixed a := Bool (from True)'
        , '  argument 2 has type Bool -> Bool (from not)'
        ]
      )
    with self.assertRaises(errors.MismatchError) as cm:
      problem(P('+'), 1.5, 'a')
    self.assertIn('argument 1 fixed a := Float (from 1.5)', str(cm.exception))
    # A nested application names the inner symbol.  The expected type flows
    # down before the literals are seen, so the constraint of + fails on
    # Bool first.
    with self.assertRaisesRegex(
        errors.NoInstanceError
      , r'^no instance for Num Bool in argument 1 of Prelude\.not :: Bool -> Bool$'
      ):
      problem(P('&&'), True, [P('not'), [P('+'), 1, 2]])
    with self.assertRaisesRegex(
        errors.MismatchError, r'^type mismatch in argument 1 of Prelude\.not :: Bool -> Bool\n'
      ):
      problem(P('&&'), True, [P('not'), [P('Just'), 1]])

  def test_no_scheme(self):
    '''A symbol without a scheme is the error of the signature table.'''
    with self.assertRaisesRegex(
        sigtable.InterfaceError
      , r"^no type for Prelude\._biGenerator: the FlatCurry interface \S+ has no entry "
        r"'_biGenerator'; use raw_expr$"
      ):
      problem(P('_biGenerator'), 1)

  def test_exception_classes(self):
    '''Every error of the engine is a CurryTypeError.'''
    for cls in [
        errors.MismatchError, errors.ConversionError, errors.AmbiguousTypeError
      , errors.NoInstanceError, errors.FreeFunctionError, errors.ArityError
      , errors.ExprTypeSyntaxError, errors.UnknownTypeConstructorError
      , errors.ExprTypeMismatchError, errors.ContextInExprTypeError
      , errors.KindError, errors.ValueTooLargeError
      ]:
      self.assertTrue(issubclass(cls, errors.TypeCheckError))
      self.assertTrue(issubclass(cls, curry.CurryTypeError))
    self.assertTrue(issubclass(DefaultingError, curry.CurryTypeError))
    err = errors.ValueTooLargeError('argument 1 of M.f', 100000)
    self.assertEqual(
        str(err)
      , "the value at argument 1 of M.f has more than 100000 nodes; pass curry.typed(node, 'T')"
      )
    err = errors.TypeCheckError('one line', where='w', symbol='M.f')
    self.assertEqual((err.lines, err.where, err.symbol), (['one line'], 'w', 'M.f'))

  def test_locations(self):
    prob = solved(P('length'), [(1, [P('Just'), 'a'])])
    app = prob.root
    lst = app.args[0]
    tup = lst.items[0]
    just = tup.items[1]
    self.assertEqual(prob.location(app), 'the expression')
    self.assertEqual(prob.location(lst), 'argument 1 of Prelude.length :: [a] -> Int')
    self.assertEqual(prob.location(tup), 'element 1 of the list in argument 1 of Prelude.length :: [a] -> Int')
    self.assertEqual(
        prob.location(just)
      , 'component 2 of the tuple in element 1 of the list in argument 1 of Prelude.length :: [a] -> Int'
      )
    self.assertEqual(prob.location(just.args[0]), 'argument 1 of Prelude.Just :: a -> Maybe a')
    self.assertEqual(prob.short_location(just), 'component 2 of the tuple')
    self.assertEqual(prob.short_location(app), 'the expression')


class TestAPI(cytest.TestCase):
  '''The API for the typed builder: specs, queries, describe, materialize.'''

  def test_spec_of(self):
    plus = P('+')
    self.assertIsInstance(engine.spec_of(plus, 1, 2), App)
    self.assertIsInstance(engine.spec_of([plus, 1, 2]), App)
    self.assertIsInstance(engine.spec_of(plus), App)
    self.assertIsInstance(engine.spec_of(1), Lit)
    self.assertIsInstance(engine.spec_of(2.5), Lit)
    self.assertIsInstance(engine.spec_of(True), Lit)
    self.assertIsInstance(engine.spec_of('ab'), Lit)
    self.assertIsInstance(engine.spec_of(None), Lit)
    self.assertIsInstance(engine.spec_of([1, 2]), List)
    self.assertIsInstance(engine.spec_of((1, 2)), Tuple)
    self.assertIsInstance(engine.spec_of(curry.free()), Free)
    self.assertIsInstance(engine.spec_of(iter([1])), Iter)
    choice = engine.spec_of(curry.choice(1, 2))
    self.assertIsInstance(choice, App)
    self.assertEqual(choice.symbol, 'Prelude.?')
    spec = Lit(1)
    self.assertIs(engine.spec_of(spec), spec)
    with self.assertRaisesRegex(curry.CurryTypeError, 'invalid arguments after 1'):
      engine.spec_of(1, 2)
    with self.assertRaisesRegex(curry.CurryTypeError, 'no expression'):
      engine.spec_of()
    with self.assertRaisesRegex(curry.CurryTypeError, 'cannot type a object'):
      engine.spec_of(object())

  def test_app_forms(self):
    '''An application takes a symbol, a qualified name, or a scheme.'''
    self.assertEqual(values(App('Prelude.not', False)), ['True'])
    self.assertEqual(values(App(P('+').scheme, 1, 2)), ['3'])
    prob = solved(App('Prelude.+', 1, 2))
    self.assertIs(prob.root.symbol, P('+'))
    self.assertEqual(describe(App(P('+').scheme, 1, 2)), '1 + 2')

  def test_queries(self):
    prob = solved(P('+'), 1, 2.5)
    app = prob.root
    self.assertEqual(prob.type_of(app), FLOAT)
    self.assertEqual(prob.typeexpr, FLOAT)
    self.assertEqual(prob.signature, 'Fractional a => a')
    self.assertEqual(prob.defaulted_signature, 'Float')
    self.assertEqual(str(prob.scheme), 'Fractional a => a')
    self.assertEqual(prob.dictionaries(app), app.dicts)
    self.assertEqual([str(d) for d in prob.dictionaries(app)], ['_inst#Prelude.Num#Prelude.Float'])
    self.assertEqual(prob.literal_type(app.args[0]), FLOAT)
    self.assertEqual(prob.literal_type(app.args[1]), FLOAT)
    self.assertEqual(str(prob.literal_dictionary(app.args[0])), '_inst#Prelude.Num#Prelude.Float')
    self.assertEqual(str(prob.literal_dictionary(app.args[1])), '_inst#Prelude.Fractional#Prelude.Float')
    self.assertEqual(prob.show_type_of(app.args[0]), 'Float')
    self.assertEqual([type(s).__name__ for s in prob.specs], ['App', 'Lit', 'Lit'])
    self.assertEqual(prob.apps, [app])
    self.assertEqual(prob.lits, app.args)
    self.assertIs(app.args[0].parent, app)
    self.assertEqual((app.args[0].index, app.args[1].index), (0, 1))
    self.assertEqual(app.scheme.fullname, 'Prelude.+')
    self.assertEqual(len(app.preds), 1)
    self.assertEqual(app.preds[0].classname, 'Prelude.Num')
    self.assertEqual(app.preds[0].index, 0)
    self.assertIs(prob.solve(), prob)
    self.assertTrue(prob.solved)
    self.assertEqual(engine.infer(curry.getInterpreter(), P('+'), 1, 2).defaulted_signature, 'Int')
    # The scheme of the table's run.
    d, = prob.defaulting
    self.assertEqual(d.substitution, {0: 'Float'})

  def test_describe(self):
    x = curry.free()
    cases = [
        ((P('+'), 1, 2), '1 + 2')
      , ((P('+'), P('maxBound'), 1), 'maxBound + 1')
      , ((P('show'), [P('+'), 1, 2]), 'show (1 + 2)')
      , ((P('fmap'), [P('+'), 1], [P('Just'), 1]), 'fmap ((+) 1) (Just 1)')
      , ((P('read'), '5'), 'read "5"')
      , ((P('ord'), 'a'), "ord 'a'")
      , (([1, 2.5],), '[1, 2.5]')
      , (((1, 'a', True),), "(1, 'a', True)")
      , ((P('=:='), x, x), '_a =:= _a')
      , ((P('=:='), x, curry.free()), '_a =:= _b')
      , ((P('length'), iter([1])), 'length <iterator>')
      , ((P('length'), Known('[Int]', curry.raw_expr([1]))), 'length <value>')
      , ((curry.module('Data.Maybe').fromJust, [P('Just'), 1]), 'Data.Maybe.fromJust (Just 1)')
      , ((P('(,)'), 1, 2), '(1, 2)')
      , ((P('?'), 1, [P('?'), 2, 3]), '1 ? (2 ? 3)')
      , ((P('not'),), 'not')
      , ((P('Just'), None), 'Just None')
      , (('',), '""')
      ]
    for args, expected in cases:
      # A typed spec: a one-character string prints as a Char or a String
      # by its type.
      spec = engine.spec_of(*args)
      try:
        Problem(curry.getInterpreter(), spec)
      except curry.CurryTypeError:
        pass
      self.assertEqual(describe(spec), expected)
    self.assertEqual(describe(engine.spec_of(P('read'), '5')), "read '5'")
    # A deep spec prints with an ellipsis instead of overflowing the stack.
    spec = Lit(0)
    for i in range(2000):
      spec = App(P('+'), spec, Lit(1))
    text = describe(spec)
    self.assertIn('...', text)
    self.assertLess(len(text), 2000)

  def test_deep_tree(self):
    '''A left-deep tree of 10^4 applications types and builds.'''
    plus = P('+')
    spec = Lit(0)
    for i in range(1, 10001):
      spec = App(plus, spec, Lit(i))
    prob = Problem(curry.getInterpreter(), spec)
    self.assertEqual(prob.signature, 'Num a => a')
    prob.solve()
    self.assertEqual(prob.defaulted_signature, 'Int')
    self.assertEqual(len(prob.apps), 10000)
    self.assertEqual(len(prob.lits), 10001)
    node = engine.materialize(prob)
    self.assertIsNotNone(node)
    # A smaller tree evaluates.
    spec = Lit(0)
    for i in range(1, 101):
      spec = App(plus, spec, Lit(i))
    self.assertEqual([str(v) for v in curry.eval(engine.materialize(Problem(curry.getInterpreter(), spec)))], ['5050'])

  def test_materialize_shapes(self):
    '''The shapes of the reference materializer.'''
    self.assertEqual(str(build(P('+'), 1, 2)), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2')
    self.assertEqual(str(build(P('=:='), 1, 2)), '(=:=) _inst#Prelude.Data#Prelude.Int 1 2')
    # The Python runtime prints a partial application in parentheses of
    # its own; the C++ runtime does not.
    self.assertIn(
        str(build(P('show'), [1]))
      , [ 'apply (show ((_inst#Prelude.Show#[] _inst#Prelude.Show#Prelude.Int))) [1]'
        , 'apply (show (_inst#Prelude.Show#[] _inst#Prelude.Show#Prelude.Int)) [1]'
        ]
      )
    # A method takes its dictionary alone; the value goes through apply.
    self.assertEqual(str(build(P('+'), 1)), 'apply ((+) _inst#Prelude.Num#Prelude.Int) 1')
    self.assertEqual(str(build(P('not'))), 'not')
    self.assertEqual(values(P('apply'), [P('not')], True), ['False'])
    self.assertEqual(str(build(P('fromIntegral'), 3)), 'apply (fromIntegral _inst#Prelude.Integral#Prelude.Int _inst#Prelude.Num#Prelude.Int) 3')
    self.assertEqual(
        floats(str(build(P('round'), 2.5)))
      , 'apply (apply (round _inst#Prelude.RealFrac#Prelude.Float) '
        '_inst#Prelude.Integral#Prelude.Int) 2.5'
      )
    # The backends round a half differently; 2.7 rounds alike.
    self.assertEqual(values(P('round'), 2.7), ['3'])
    self.assertEqual(str(build((1, 'a'))), "(1, 'a')")
    self.assertEqual(str(build([1, 2])), '[1, 2]')
    self.assertEqual(str(build('ab')), '"ab"')
    self.assertEqual(str(build(curry.free())), 'unknown _inst#Prelude.Data#Prelude.Bool')
    self.assertEqual(values(P('negate'), 5), ['(-5)'])
    self.assertEqual(values(P('Just'), [P('Just'), 'a']), ["Just (Just 'a')"])
    self.assertEqual(values(P('length'), [P('map'), P('not'), [True, False]]), ['2'])

  def test_package_exports(self):
    import curry.typecheck as tc
    self.assertIs(tc.Problem, Problem)
    self.assertIs(tc.infer, engine.infer)
    self.assertIs(tc.DictTerm, DictTerm)
    self.assertIs(tc.TypeCheckError, errors.TypeCheckError)
    self.assertIs(tc.parse_type, exprtype.parse_type)
    with self.assertRaises(AttributeError):
      tc.no_such_name
