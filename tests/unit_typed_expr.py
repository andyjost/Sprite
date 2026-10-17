'''
The typed ``curry.term``, item Y7 of the typed boundary (#56, epic #48).

``curry.term`` describes its arguments as a tree of specs, types the tree
with the engine (``curry.typecheck.engine``), defaults the constraints,
resolves the class dictionaries, and builds the nodes through ``make_node``
(``curry.typecheck.builder``).  Python values convert by the expected type,
a Curry node that fills a parameter is typed by a walk of its content, the
items of an iterator convert when the list is demanded, a method call takes
the selector route through ``apply``, and the result type of every node is
recorded, so ``curry.typeof`` answers for it and ``curry.eval`` converts an
empty ``[Char]`` to ``''``.  The tests run on both backends; the modules
UnsignedGoals and TypeCheck come from unit_goals.py and unit_typecheck.py.
'''
import cytest # from ./lib; must be first
from curry import inspect
from curry.typecheck import builder, engine, errors
from curry.typecheck.defaulting import DefaultingError, ORACLE_SENTENCE
from curry.typecheck.errors import DEFAULTS_HINT
import curry, gc, itertools, re, unittest

IS_CXX = curry.flags['backend'] == 'cxx'

def prelude():
  return curry.import_('Prelude')

def symbol(name):
  return curry.import_('Prelude')[name]

def goal(first, *args, type=None, **bindings):
  value = first(*args) if args else curry.term(first)
  if bindings:
    value = curry.let(value, **bindings)
  return curry.term(value, type=type)


def values(*args, type=None, **bindings):
  return list(curry.eval(goal(*args, type=type, **bindings)))

def floats(text):
  '''
  A value text with the floats in the format of the Python backend.  The
  C++ backend prints 1.5 as 1.5000000000000000 (issue #34).
  '''
  return re.sub(
      r'(\d\.\d*?)0+(?!\d)'
    , lambda m: m.group(1) if not m.group(1).endswith('.') else m.group(1) + '0'
    , text
    )

def texts(*args, type=None, **bindings):
  return [floats(curry.show(value))
      for value in curry.eval(goal(*args, type=type, **bindings))]

def deep(n, plus=None):
  '''A deep application tree, typed in one recursive binding group.'''
  plus = symbol('+') if plus is None else plus
  bindings = {'x0': 1}
  for i in range(n):
    bindings['x%d' % (i + 1)] = plus(curry.ref('x%d' % i), 1)
  return curry.let(curry.ref('x%d' % n), **bindings)

def biglist(n):
  '''A Curry list of ``n`` integers made node by node: no record of its type.'''
  P = prelude()
  make = cytest.raw.interp().backend.make_node
  node = make(P.Nil)
  for i in reversed(range(n)):
    node = make(P.Cons, make(P.Int, i), node)
  return node

class TestAcceptance(cytest.TestCase):
  '''The acceptance list of the issue.'''

  def test_method_call(self):
    '''
    A class method is a selector of arity 1 whose parameter is the
    dictionary: the builder supplies the dictionary of the instance and
    routes the value arguments through apply.
    '''
    plus = symbol('+')
    e = (plus)(1, 2)
    self.assertEqual(str(cytest.raw.expr(e)), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2')
    self.assertEqual(curry.typeof(e), 'Num a => a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Int')
    # Evaluation preserves the held term.
    self.assertEqual(values(e), [3])
    self.assertEqual(str(e), '1 + 2')
    self.assertEqual(values(plus, 1, 2), [3])
    e = (plus)(1.5, 1)
    self.assertIn('_inst#Prelude.Num#Prelude.Float', str(cytest.raw.expr(e)))
    self.assertEqual(curry.typeof(e), 'Float')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Float')
    self.assertEqual(values(e), [2.5])

  def test_show_just(self):
    '''show over Maybe Int: the dictionary of Maybe takes the dictionary of Int.'''
    P = prelude()
    e = (P.show)(P.Just(1))
    self.assertIn('_inst#Prelude.Show#Prelude.Maybe', str(cytest.raw.expr(e)))
    self.assertIn('_inst#Prelude.Show#Prelude.Int', str(cytest.raw.expr(e)))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Char]')
    self.assertEqual(values(e), ['Just 1'])
    self.assertEqual(values(P.show, P.Just(1)), ['Just 1'])

  def test_exprtype(self):
    '''exprtype fixes the type of the expression; the literal follows it.'''
    P = prelude()
    e = curry.term((P.Just)(5), type='Maybe Float')
    self.assertEqual(texts(e), ['Just 5.0'])
    self.assertEqual(curry.typeof(e, defaulted=True), 'Maybe Float')
    e = curry.term((P.read)('5'), type='Int')
    self.assertEqual(values(e), [5])
    self.assertEqual(texts(curry.term(curry.term(1), type='Float')), ['1.0'])

  def test_errors_at_construction(self):
    '''The three ill-typed calls of the issue raise on both backends.'''
    P = prelude()
    calls = [
        (getattr(P, 'not'), 1)
      , (symbol('plusInt'), 1, 2.5)
      , (P.Just, 1, 2)
      ]
    for args in calls:
      with self.assertRaises(curry.CurryTypeError):
        (args[0](*args[1:]) if len(args) > 1 else curry.term(args[0]))
      with self.assertRaises(curry.CurryTypeError):
        curry.eval(args[0](*args[1:]) if len(args) > 1 else args[0])
    # The error is a TypeError too, as every CurryTypeError is.
    with self.assertRaises(TypeError):
      (getattr(P, 'not'))(1)

  def test_read_ambiguity(self):
    P = prelude()
    goal = P.read('5')
    self.assertEqual(curry.typeof(goal), 'Read a => a')
    with self.assertRaises(curry.DefaultingError) as cm:
      curry.eval(goal)
    self.assertIn('cannot handle the overloaded goal read "5"', str(cm.exception))
    self.assertIn(ORACLE_SENTENCE, str(cm.exception))
    self.assertEqual(values(curry.term(goal, type='Int')), [5])
    self.assertEqual(values(curry.parse('read "5" :: Int')), [5])

  def test_free_at_function_type(self):
    P = prelude()
    x = curry.free('x')
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^free variable at argument 1 of Prelude\.map :: \(a -> b\) -> \[a\] -> \[b\] '
        r'would have the function type a -> b\n'
        r'  Curry free variables must have a Data type$'
      ):
      (P.map)(x, [1, 2])

  def test_large_descriptions(self):
    '''
    A list of 10000 values and a left-deep tree of 10^4 applications build:
    the conversion, the typing and the materialization walk with explicit
    stacks.  The Python backend evaluates the small forms only.
    '''
    P = prelude()
    big = curry.term(list(range(10000)))
    self.assertEqual(curry.typeof(big, defaulted=True), '[Int]')
    self.assertEqual(len(curry.eval(big).one()), 10000)
    self.assertEqual(values(P.take, 3, big), [[0, 1, 2]])
    tree = curry.term(deep(10000))
    self.assertEqual(curry.typeof(tree), 'Num a => a')
    self.assertEqual(curry.typeof(tree, defaulted=True), 'Int')
    self.assertEqual(values(curry.term(deep(100))), [101])
    if IS_CXX:
      self.assertEqual(values(P.length, big), [10000])
      self.assertEqual(values(tree), [10001])
    # The depth of a type is bounded by the recursion limit: the engine
    # walks a type recursively.  A list nested 500 deep is fine.
    nested = 1
    for _ in range(500):
      nested = [nested]
    e = curry.term(nested)
    self.assertEqual(curry.typeof(e, defaulted=True)[:20], '[' * 20)

  def test_value_of_an_evaluation(self):
    '''
    A value of curry.eval is a copy; a later call types it by its content.
    A list of floats fed to sum gives a Float, and an Int value under a
    Float operand is a mismatch at construction.
    '''
    P = prelude()
    DL = curry.import_('Data.List')
    DM = curry.import_('Data.Maybe')
    plus = symbol('+')
    v = next(curry.eval(curry.term([1.5, 2.5])))
    self.assertEqual(curry.typeof(v), '[Float]')
    total, = values(DL.sum, v)
    self.assertIsInstance(total, float)
    self.assertEqual(total, 4.0)
    r = next(curry.eval((P.Just)(1)))
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 1\.5 to Int at argument 2 of Prelude\.\+ :: Num a => a -> a -> a: '
        r'a float is a Float; write an int for an Int slot$'
      ):
      (plus)(DM.fromJust(r), 1.5)
    # The other order: the value meets the type the literal fixed, inside
    # fromJust, where the expected type arrived from above.
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^type mismatch in argument 1 of Data\.Maybe\.fromJust :: Maybe a -> a: expected Maybe Float, got Maybe Int$'
      ):
      (plus)(1.5, DM.fromJust(r))
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^type mismatch in argument 2 of Prelude\.\+ :: Num a => a -> a -> a: expected Float, got Maybe Int$'
      ):
      (plus)(1.5, r)
    # A node curry.term returned is typed by its record, also after its
    # evaluation rewrote it.
    e = curry.term([1.5, 2.5])
    self.assertEqual(values(DL.sum, e), [4.0])
    self.assertEqual(values(DL.sum, e), [4.0])
    self.assertEqual(curry.typeof((DL.sum)(e), defaulted=True), 'Float')

  def test_iterator_item_mismatch(self):
    P = prelude()
    DL = curry.import_('Data.List')
    SF = curry.import_('Control.SetFunctions')
    pattern = r'cannot convert item 2\.5.*to Int'
    for make in (lambda: DL.sum(iter([1, 2.5])),
        lambda: P['?'](DL.sum(iter([1, 2.5])), 7),
        lambda: SF.values2list(SF.set1(DL.sum, iter([1, 2.5])))):
      with self.subTest(make=make), self.assertRaisesRegex(curry.ConversionError, pattern):
        values(make())
    self.assertEqual(values(DL.sum(iter([1, 2]))), [3])
    self.assertEqual(values(P.take(3, itertools.count())), [[0, 1, 2]])
    with self.assertRaises(curry.ConversionError):
      values(P.take(2, iter([1, 'a'])))
    self.assertEqual(values(curry.term(P.take(2, iter([1, 2.5])), type='[Float]')), [[1.0, 2.5]])
    self.assertEqual(values(P.unlines(iter(['a', 'bc']))), ['a\nbc\n'])
    self.assertEqual(values(P.concat(iter(['ab', 'c']))), ['abc'])
    self.assertEqual(values(P.unwords(iter([curry.term('xy'), 'z']))), ['xy z'])
    self.assertEqual(values(P.length(iter([(1, 'a'), (2, 'b')]))), [2])
    self.assertEqual(values(P.length(iter([curry.anonymous, curry.anonymous]))), [2])
    with self.assertRaises(curry.ConversionError):
      values(P.ord(P.head(P.reverse(iter([curry.Char('a'), 'ab'])))))

  def test_rewritten_tests_hold(self):
    '''
    The two tests the item rewrote, in short: a method applied from Python
    and the empty string that converts to ''.
    '''
    P = prelude()
    apply_ = P.apply
    plus = symbol('+')
    incr = (plus)(1)
    self.assertEqual(curry.typeof(incr, defaulted=True), 'Int -> Int')
    self.assertEqual(values(apply_, incr, 6), [7])
    y, = curry.eval(curry.term(''))
    self.assertEqual(y, '')

class TestConversion(cytest.TestCase):
  '''The conversion of Python values by the expected type.'''

  def test_numbers(self):
    P = prelude()
    DM = curry.import_('Data.Maybe')
    self.assertEqual(texts(DM.fromJust, P.Just(1), type='Float'), ['1.0'])
    e = curry.term([1, 2.5])
    self.assertEqual(curry.typeof(e), '[Float]')
    self.assertEqual(curry.typeof(e, defaulted=True), '[Float]')
    self.assertEqual(values(e), [[1.0, 2.5]])
    self.assertEqual(curry.typeof(curry.term(1)), 'Num a => a')
    self.assertEqual(curry.typeof(curry.term(1), defaulted=True), 'Int')
    self.assertEqual(values(symbol('/'), 3, 2), [1.5])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 2\.5 to Int at argument 2 of Prelude\.plusInt :: Int -> Int -> Int: a float is a Float; write an int for an Int slot$'
      ):
      (symbol('plusInt'))(1, 2.5)

  def test_literal_at_a_user_type(self):
    '''An int under a type with its own Num instance goes through fromInt.'''
    M = curry.import_('TypeCheck')
    e = (M.toInt)(3)
    self.assertEqual(curry.typeof(e, defaulted=True), 'Int')
    self.assertIn('fromInt', str(cytest.raw.expr(e)))
    self.assertEqual(values(e), [3])
    e = curry.term((M.twice)(2), type='Nat')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Nat')
    self.assertEqual(texts(e), ['S (S (S (S Z)))'])
    self.assertEqual(texts(M.twice, 2, type='Nat'), ['S (S (S (S Z)))'])
    self.assertEqual(texts(M.twice, 2), ['4'])

  def test_strings(self):
    P = prelude()
    for text in ('hello', 'a', 'ab', '', 'ä\U0001f600'):
      with self.subTest(text=text):
        s = curry.term(text)
        self.assertEqual(curry.typeof(s), '[Char]')
        self.assertEqual(values(s), [text])
        self.assertEqual(values(P.length(s)), [len(text)])
    c = curry.term(curry.Char('a'))
    self.assertEqual(curry.typeof(c), 'Char')
    self.assertEqual(curry.typeof(P.id(c)), 'Char')
    self.assertEqual(values(P.ord(c)), [97])
    self.assertEqual(values(P.reverse('ab')), ['ba'])
    self.assertEqual(values(P.id('ab')), ['ab'])
    self.assertEqual(curry.typeof(P.id('ab')), '[Char]')
    self.assertEqual(values(['ab', 'c']), [['ab', 'c']])
    self.assertEqual(values(['c', 'ab']), [['c', 'ab']])
    self.assertEqual(values(curry.choice('c', 'ab')), ['c', 'ab'])
    self.assertEqual(values(curry.choice('ab', 'c')), ['ab', 'c'])
    self.assertEqual(values(P.fmap(P.ord, 'a')), [[97]])
    self.assertEqual(texts(curry.term(P.Just('a'), type='Maybe String')), ['Just "a"'])
    self.assertEqual(curry.typeof(curry.term(('a', 'bc'))), '([Char], [Char])')
    self.assertEqual(curry.typeof(P.Just(curry.Char('a'))), 'Maybe Char')
    for bad in (['a', True], ['a', 1]):
      with self.subTest(value=bad), self.assertRaises(curry.CurryTypeError):
        curry.term(bad)
    with self.assertRaises(curry.CurryTypeError):
      curry.term('a', type='a')
    with self.assertRaisesRegex(curry.ConversionError, 'decode'):
      curry.term(b'bytes')
    with self.assertRaisesRegex(curry.EvaluationError, 'oops'):
      values(P.error('oops'))

  def test_empty_string(self):
    '''
    The static type makes '' of an empty [Char]: through eval, which hands
    the type of the goal to the converter, and through topython(type=).
    '''
    P = prelude()
    e = curry.term('')
    self.assertTrue(inspect.isa_nil(e))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Char]')
    self.assertEqual(values(e), [''])
    self.assertEqual(values(P.reverse, curry.term([], type='[Char]')), [''])
    self.assertEqual(values(P.filter, P.isUpper, 'abc'), [''])
    self.assertEqual(values(P.reverse, []), [[]])
    self.assertEqual(values(P.show, 5), ['5'])
    self.assertEqual(values(P.id, ([], 'x')), [([], 'x')])
    self.assertEqual(values(P.id, curry.term(([], 'x'), type='([Char], [Char])')), [('', 'x')])
    self.assertEqual(curry.eval(curry.term([], type='[Char]')).one(), '')
    self.assertEqual(values(curry.term([], type='[Int]')), [[]])

  def test_bool_and_none(self):
    P = prelude()
    self.assertEqual(values(getattr(P, 'not'), True), [False])
    self.assertEqual(values(getattr(P, '&&'), True, False), [False])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert True to Int at argument 1 of Prelude\.plusInt'
      ):
      (symbol('plusInt'))(True, 1)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert None at argument 1 of Prelude\.Just :: a -> Maybe a: cannot convert NoneType: write P\.Nothing or P\.Just\(x\)$'
      ):
      (P.Just)(None)

  def test_lists_and_tuples(self):
    P = prelude()
    self.assertEqual(values(P.length, []), [0])
    self.assertEqual(curry.typeof(curry.term([[1, 2], [3]]), defaulted=True), '[[Int]]')
    self.assertEqual(values(curry.term(([1, 2], ('a', 2.5), True))), [([1, 2], ('a', 2.5), True)])
    self.assertEqual(curry.typeof(curry.term(())), '()')
    self.assertEqual(values(P.fst, (1, 'a')), [1])
    self.assertEqual(values(P.snd, (1, 'a')), ['a'])
    with self.assertRaisesRegex(curry.CurryTypeError, 'zero or 2 to 15 components'):
      curry.term((1,))
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^type mismatch in element 2 of the list in argument 1 of "
        r"Prelude\.length :: \[a\] -> Int\n"
        r"  element 1 of the list fixed the type Int \(from 1\)\n"
        r"  element 2 of the list has type \[Char\] \(from \('a' :: \[Char\]\)\)$"
      ):
      (P.length)([1, 'a'])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^exprtype Float does not match the inferred type Int$'
      ):
      (P.length)(curry.term([1, 2.5], type='[Int]'))
    # Lists are values; the Prelude constructors build their cells.
    self.assertEqual(values(P.length([1, 2])), [2])
    self.assertEqual(values(P.Cons(1, P.Cons(2, P.Nil))), [[1, 2]])
    self.assertEqual(curry.typeof(curry.term([])), '[a]')

  def test_iterator_element_constraint(self):
    P = prelude()
    with self.assertRaisesRegex(curry.DefaultingError, re.escape(ORACLE_SENTENCE)):
      curry.eval(P.map(P.show, iter([1, 2, 3])))
    typed = curry.term(iter([1, 2, 3]), type='[Int]')
    self.assertEqual(values(P.map(P.show, typed)), [['1', '2', '3']])
    with self.assertRaisesRegex(curry.DefaultingError, re.escape(ORACLE_SENTENCE)):
      curry.eval(P.read('5'))

  def test_free_variables(self):
    P = prelude()
    x = curry.free('x')
    self.assertIs(curry.term(x), x)
    self.assertEqual(str(x), 'x')
    self.assertEqual(curry.typeof(x), 'Data a => a')
    self.assertEqual(values(P['=:='](x, 1)), [True])
    y = curry.free('ys', type='[Int]')
    self.assertEqual(curry.typeof(y), '[Int]')
    self.assertIs(P.id(y).free_vars['ys'], y)
    z = curry.free('z')
    self.assertEqual(values(P.constrEq((z, 2), (1, 2))), [True])
    w = curry.free('w')
    e = P.constrEq(w, [1, 2])
    self.assertEqual(curry.typeof(e), 'Bool')
    self.assertIn('_inst#Prelude.Data#[]', str(cytest.raw.expr(e)))
    self.assertEqual(values(e), [True])

class TestForms(cytest.TestCase):
  '''The forms of the untyped builder on the typed path.'''

  def test_choice(self):
    P = prelude()
    self.assertEqual(sorted(values(getattr(P, 'not'), curry.choice(True, False))), [False, True])
    e = curry.term(curry.choice(1, 2.5))
    self.assertEqual(curry.typeof(e, defaulted=True), 'Float')
    self.assertEqual(sorted(values(e)), [1.0, 2.5])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^type mismatch in argument 2 of Prelude\.\? :: a -> a -> a\n"
        r"  argument 1 fixed a := Int \(from 1\)\n"
        r"  argument 2 has type \[Char\] \(from \('a' :: \[Char\]\)\)$"
      ):
      curry.term(curry.choice(1, 'a'))

  def test_anchors_and_references(self):
    P = prelude()
    ref = curry.ref
    ones = curry.let(ref('xs'), xs=P.Cons(1, ref('xs')))
    self.assertEqual(values(P.take(2, ones)), [[1, 1]])
    sevens = curry.let(P.take(3, ref('xs')), xs=P.Cons(7, ref('xs')))
    self.assertEqual(curry.typeof(sevens, defaulted=True), '[Int]')
    self.assertEqual(values(sevens), [[7, 7, 7]])
    with self.assertRaises(curry.CurryTypeError):
      curry.let(P.take('a', ref('xs')), xs=P.Cons(7, ref('xs')))
    with self.assertRaisesRegex(curry.CurryTypeError, 'need bindings'):
      curry.term(ref('nowhere'))
    alternating = curry.let(P.take(3, ref('a')),
        a=P.Cons(1, ref('b')), b=P.Cons(2, ref('a')))
    self.assertEqual(values(alternating), [[1, 2, 1]])
    self.assertEqual(curry.typeof(alternating, defaulted=True), '[Int]')

  def test_terms_pass_through(self):
    P = prelude()
    n = curry.term(1)
    self.assertIs(curry.term(n), n)
    self.assertIsNot(curry.term([n]), n)
    self.assertEqual(values(curry.term([n])), [[1]])
    self.assertEqual(values(P.length(P.reverse([1, 2, 3]))), [3])
    value = curry.eval(P.Just(1)).one()
    with self.assertRaises(curry.MismatchError):
      P['not'](value)




  def test_unsigned_goal(self):
    '''curry.term of a goal without a signature supplies its dictionaries.'''
    M = curry.import_('UnsignedGoals')
    e = curry.term(M.main14)
    self.assertEqual(str(cytest.raw.expr(e)), 'main14')
    self.assertEqual(texts(e), ['Just 5'])
    self.assertEqual(curry.typeof(e), 'Num a => Maybe a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Maybe Int')
    self.assertEqual(values(M.addOne, 1), [2])
    self.assertEqual(values(M.addOne, 1.5), [2.5])
    self.assertEqual(texts(curry.term(M.main21)), ['[1.0,2.5]'])
    with self.assertRaisesRegex(curry.CurryTypeError, ORACLE_SENTENCE):
      curry.eval(M.main17)

  def test_arity_forms(self):
    '''Fewer arguments give a partial application; more go through apply.'''
    P = prelude()
    plus = symbol('+')
    e = (P.map)(getattr(P, 'not'))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Bool] -> [Bool]')
    self.assertEqual(values(P.apply, e, [True]), [[False]])
    self.assertEqual(values(P.id, P.id, 5), [5])
    self.assertEqual(values(P.id, plus, 1, 2), [3])
    incr = (plus)(1)
    self.assertEqual(values(P.apply, incr, 6), [7])
    # A partial application fed back is typed by its head: an ill-typed one
    # of raw_expr is reported where it fails to unify.
    self.assertEqual(curry.typeof(cytest.raw.expr(P.apply, P.id)), 'a -> a')
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in the expression'):
      curry.typeof(cytest.raw.expr(P.apply, 1))
    with self.assertRaisesRegex(
        curry.CurryTypeError, r'^Prelude\.Just :: a -> Maybe a takes 1 argument, 2 given$'
      ):
      (P.Just)(1, 2)

  def test_newtype(self):
    '''A newtype constructor is erased, as the ICurry translation erases it.'''
    ID = curry.import_('Data.Functor.Identity')
    e = (ID.Identity)(5)
    # The printer qualifies the names outside the Prelude.
    self.assertEqual(curry.typeof(e, defaulted=True), 'Identity Int')
    self.assertEqual(str(cytest.raw.expr(e)), '5')
    self.assertEqual(values(e), [5])
    self.assertEqual(values(ID.runIdentity, ID.Identity(5)), [5])
    self.assertEqual(
        curry.typeof(curry.term(ID.Identity)), 'a -> Identity a'
      )
    P = prelude()
    self.assertEqual(values(ID.runIdentity, (P.apply)(ID.Identity, 5)), [5])

  def test_argument_errors(self):
    with self.assertRaises(TypeError):
      curry.term(1)(2)
    with self.assertRaises(TypeError):
      curry.term()
    with self.assertRaisesRegex(curry.ConversionError, 'cannot convert object'):
      curry.term(object())

class TestValueWalk(cytest.TestCase):
  '''A Curry node that fills a parameter is typed by a walk of its content.'''

  def test_shared_and_cyclic(self):
    P = prelude()
    shared = curry.choice(1, 2)
    self.assertEqual(values((shared, shared)), [(1, 1), (2, 2)])
    cycle = curry.let(curry.ref('xs'), xs=P.Cons(1, curry.ref('xs')))
    self.assertEqual(curry.typeof(cycle, defaulted=True), '[Int]')
    self.assertEqual(values(P.take(2, cycle)), [[1, 1]])


  def test_partial_application(self):
    '''
    A partial application is typed by the scheme of its head and the
    arguments it holds, so an ill-typed application of it is refused at
    construction instead of crashing the runtime.
    '''
    P = prelude()
    plus = symbol('+')
    v = next(curry.eval((P.map)(getattr(P, 'not'))))
    self.assertIsInstance(v, curry.Function)
    self.assertEqual(curry.typeof(v), '[Bool] -> [Bool]')
    self.assertEqual(values(P.apply, v, [True, False]), [[False, True]])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 1 to \[Bool\] at argument 2 of Prelude\.apply :: \(a -> b\) -> a -> b: an int is a numeric literal$'
      ):
      (P.apply)(v, 1)
    # A method with its dictionary: the dictionary is skipped and the value
    # argument fixes the type.
    incr = next(curry.eval((plus)(1)))
    self.assertIsInstance(incr, curry.Function)
    self.assertEqual(curry.typeof(incr), 'Int -> Int')
    self.assertEqual(values(P.apply, incr, 2), [3])
    with self.assertRaises(curry.CurryTypeError):
      (P.apply)(incr, 2.5)
    # A constructor with a missing argument.
    j = next(curry.eval(curry.term(P.Just)))
    self.assertEqual(curry.typeof(j), 'a -> Maybe a')
    self.assertEqual(texts(P.apply, j, curry.Char('x')), ["Just 'x'"])
    # A method without its dictionary stays an opaque leaf.
    self.assertEqual(curry.typeof(cytest.raw.expr(plus)), 'a')



class TestAPI(cytest.TestCase):
  '''typeof, describe, the record, the converter and the flag.'''

  def test_typeof(self):
    P = prelude()
    plus = symbol('+')
    self.assertEqual(curry.typeof(plus), 'Num a => a -> a -> a')
    self.assertEqual(curry.typeof(plus, defaulted=True), 'Int -> Int -> Int')
    self.assertEqual(curry.typeof(P.Just), 'a -> Maybe a')
    self.assertEqual(curry.typeof(P.show), 'Show a => a -> [Char]')
    self.assertEqual(curry.typeof(1), 'Num a => a')
    self.assertEqual(curry.typeof([1, 2.5]), '[Float]')
    self.assertEqual(curry.typeof([1, 2.5], defaulted=True), '[Float]')
    self.assertEqual(curry.typeof(('a', True)), '([Char], Bool)')
    self.assertEqual(curry.typeof(P.length, defaulted=True), '[a] -> Int')
    # A lone symbol is defaulted as a goal: Show alone is not defaultable.
    with self.assertRaisesRegex(curry.CurryTypeError, ORACLE_SENTENCE):
      curry.typeof(P.show, defaulted=True)
    self.assertEqual(symbol('+').signature, 'Num a => a -> a -> a')
    with self.assertRaises(curry.CurryTypeError):
      curry.typeof(P.show([]), defaulted=True)
    # The context in the order of the front end: by the first type variable
    # of the constraint, then by the class.
    from curry.interpreter.compile import expression_scheme
    interp = cytest.raw.interp()
    for args, text in [((1, 2.5), '(1, 2.5 :: Float)'),
        ((1, 'a', 2.5), '(1, "a", 2.5 :: Float)')]:
      self.assertEqual(curry.typeof(args), str(expression_scheme(interp, text)))
    self.assertEqual(curry.typeof(curry.term((1, 2.5))), 'Num a => (a, Float)')
    self.assertEqual(curry.typeof((1, 'a', 2.5)), 'Num a => (a, [Char], Float)')
    self.assertEqual(
        curry.typeof(P.show(plus(curry.free('x'), 1))), '[Char]'
      )
    # A lone symbol without a scheme has no type, though expr builds it.
    with self.assertRaisesRegex(
        curry.CurryTypeError, r'^no type for Prelude\._biGenerator: .*; use raw_expr$'
      ):
      curry.typeof(P._biGenerator)
    self.assertTrue(cytest.raw.expr(P._biGenerator, typed=True).info.is_partial)

  def test_term_text(self):
    P = prelude()
    plus = symbol('+')
    inner = plus(1, 1)
    outer = plus(inner, 2.5)
    self.assertEqual(str(inner), '1 + 1')
    self.assertEqual(curry.typeof(inner), 'Num a => a')
    self.assertEqual(curry.typeof(outer, defaulted=True), 'Float')
    self.assertEqual(values(outer), [4.5])
    self.assertEqual(values(curry.term(inner, type='Float')), [2.0])
    pair = curry.term((inner, inner))
    self.assertEqual(values(pair), [(2, 2)])
    self.assertEqual(curry.typeof(pair), 'Num a => (a, a)')
    x = curry.free('x')
    self.assertIs(P.id(x).free_vars['x'], x)
    ones = curry.let(curry.ref('xs'), xs=P.Cons(7, curry.ref('xs')))
    self.assertEqual(values(P.take(3, ones)), [[7, 7, 7]])


  def test_conversion_by_term_type(self):
    self.assertEqual(values(curry.term([], type='[Char]')), [''])
    self.assertEqual(values(curry.term([], type='[Int]')), [[]])
    self.assertEqual(values(curry.term([], type='[a]')), [[]])
    chars = curry.term([curry.Char('a'), curry.Char('b')])
    self.assertEqual(values(chars), ['ab'])
    pair = curry.term(('', ['a', '']))
    self.assertEqual(values(pair), [('', ['a', ''])])
    with self.assertRaises(curry.CurryTypeError):
      curry.term([], type='Foo')
    P = prelude()
    self.assertEqual(values(P.map(P.fst, iter([('ab', 1), ('cd', 2)]))), [['ab', 'cd']])
    self.assertEqual(values(P.map(P.fst, [('ab', 1), ('cd', 2)])), [['ab', 'cd']])

  def test_eval_static_type(self):
    P = prelude()
    self.assertEqual(values(curry.term('')), [''])
    self.assertEqual(values(P.reverse('')), [''])
    self.assertEqual(values(curry.parse('reverse "ab" :: String')), ['ba'])
    ret = P['return']
    self.assertEqual(values(ret(curry.term('', type='String'))), [''])
    self.assertEqual(values(ret('ab')), ['ab'])
    self.assertEqual(values(ret([])), [[]])
    ones = curry.let(P.take(2, curry.ref('xs')), xs=P.Cons(1, curry.ref('xs')))
    self.assertEqual(values(ones), [[1, 1]])




class TestCatalogue(cytest.TestCase):
  '''Every line of the error catalogue of the design, through curry.term.'''

  def check(self, pattern, *args, type=None):
    with self.assertRaisesRegex(curry.CurryTypeError, pattern) as cm:
      curry.eval(goal(*args, type=type))
    return cm.exception

  def test_mismatch_between_arguments(self):
    plus = symbol('+')
    err = self.check(
        r'^type mismatch in argument 2 of Prelude\.\+ :: Num a => a -> a -> a\n'
        r'  argument 1 fixed a := Int \(from 1\)\n'
        r"  argument 2 has type \[Char\] \(from \('a' :: \[Char\]\)\)$"
      , plus, 1, 'a'
      )
    self.assertIsInstance(err, errors.MismatchError)
    self.assertEqual(err.symbol, 'Prelude.+')

  def test_value_under_a_wrong_type(self):
    P = prelude()
    plusInt = symbol('plusInt')
    self.check(r'^cannot convert 2\.5 to Int at argument 2 of Prelude\.plusInt :: Int -> Int -> Int: a float is a Float; write an int for an Int slot$', plusInt, 1, 2.5)
    self.check(r"^cannot convert 'a' to Int at argument 1 of Prelude\.plusInt :: Int -> Int -> Int: a str is a String$", plusInt, 'a', 1)
    self.check(r'^cannot convert 1 to Bool at argument 1 of Prelude\.not :: Bool -> Bool: an int is a numeric literal; write True or False$', getattr(P, 'not'), 1)

  def test_ambiguity_after_defaulting(self):
    P = prelude()
    err = self.check(
        r'^ambiguous type in show \[\] :: Show a => \[Char\]\n'
        r'  Ambiguous type variable a in type Show a => \[Char\]\n'
        r'  ' + re.escape(ORACLE_SENTENCE) + r'\n'
        r'  ' + re.escape(DEFAULTS_HINT) + '$'
      , P.show, []
      )
    self.assertIsInstance(err, errors.AmbiguousTypeError)

  def test_undefaultable_expression(self):
    P = prelude()
    err = self.check(
        r'^cannot handle the overloaded goal read "5" of type Read a => a\n'
        + re.escape(ORACLE_SENTENCE) + r'\n'
        + re.escape("state the type: curry.term(P.read('5'), type='Int')") + '$'
      , P.read, '5'
      )
    self.assertIsInstance(err, DefaultingError)
    self.check(r"^cannot handle the overloaded goal toEnum 65 of type Enum a => a\n", P.toEnum, 65)

  def test_no_instance(self):
    P = prelude()
    err = self.check(
        r'^no instance for Show \(a -> a\) in argument 1 of Prelude\.show$'
      , P.show, P.id
      )
    self.assertIsInstance(err, errors.NoInstanceError)

  def test_no_scheme(self):
    P = prelude()
    self.check(
        r'^no type for Prelude\._biGenerator: .*; use raw_expr$'
      , P._biGenerator, iter([])
      )

  def test_free_variable_at_a_function_type(self):
    P = prelude()
    err = self.check(
        r'^free variable at argument 1 of Prelude\.map :: \(a -> b\) -> \[a\] -> \[b\] '
        r'would have the function type a -> b\n  Curry free variables must have a Data type$'
      , P.map, curry.free('x1'), [1, 2]
      )
    self.assertIsInstance(err, errors.FreeFunctionError)

  def test_none(self):
    P = prelude()
    DM = curry.import_('Data.Maybe')
    self.check(r'^cannot convert None at argument 1 of Prelude\.Just :: a -> Maybe a: cannot convert NoneType: write P\.Nothing or P\.Just\(x\)$', P.Just, None)
    self.check(
        r'^cannot convert None at argument 1 of Data\.Maybe\.fromJust :: Maybe a -> a: '
        r'cannot convert NoneType: write P\.Nothing or P\.Just\(x\)$'
      , DM.fromJust, None
      )
    self.check(r'^cannot convert NoneType: write P\.Nothing or P\.Just\(x\)$', None)

  def test_one_tuple(self):
    self.check(r'zero or 2 to 15 components', (1,))

  def test_too_many_arguments(self):
    P = prelude()
    err = self.check(r'^Prelude\.Just :: a -> Maybe a takes 1 argument, 2 given$', P.Just, 1, 2)
    self.assertIsInstance(err, errors.ArityError)
    self.check(r'^Prelude\.not :: Bool -> Bool takes 1 argument, 3 given$', getattr(P, 'not'), True, 1, 2)

  def test_exprtype_errors(self):
    err = self.check(
        r"^cannot parse exprtype 'Int ->': expected a type, found end of text at column 7$"
      , 1, type='Int ->'
      )
    self.assertIsInstance(err, errors.ExprTypeSyntaxError)
    err = self.check(
        r'^unknown type constructor Foo; searched the interfaces of Prelude(, [A-Za-z.]+)*; '
      , 1, type='Foo'
      )
    self.assertIsInstance(err, errors.UnknownTypeConstructorError)
    self.assertIn("curry.parse('expression :: T')", str(err))
    P = prelude()
    err = self.check(r'^exprtype Int does not match the inferred type Maybe a$', P.Just, 1, type='Int')
    self.assertIsInstance(err, errors.ExprTypeMismatchError)
    self.check(r'^exprtype \[Int\] does not match the inferred type \[Char\]$', P.show, 1, type='[Int]')
    self.check(r'^exprtype \[Char\] does not match the inferred type Int$', 'a', type='Int')
    err = self.check(
        r"^exprtype takes a type without a context; the context is inferred \(exprtype 'Num a => a'\)$"
      , 1, type='Num a => a'
      )
    self.assertIsInstance(err, errors.ContextInExprTypeError)
    self.check(r'^Maybe takes 1 type argument, 2 given in exprtype', 1, type='Maybe Int Int')
    self.check(r'^exprtype a does not match the inferred type \[b\]', [1], type='a')

  def test_iterator_item(self):
    DL = curry.import_('Data.List')
    with self.assertRaisesRegex(
        curry.ConversionError
      , r'^cannot convert item 2\.5 of the iterator at argument 1 of Data\.List\.sum :: '
        r'Num a => \[a\] -> a to Int$'
      ):
      values(DL.sum, iter([1, 2.5]))

  def test_deep_location(self):
    '''The location of a deeply nested value is elided in the middle.'''
    bad = [1, 'a']
    for _ in range(1500):
      bad = [bad]
    with self.assertRaises(curry.CurryTypeError) as cm:
      curry.term(bad)
    message = str(cm.exception)
    self.assertLess(len(message), 600)
    self.assertEqual(engine.LOCATION_DEPTH, 8)
    self.assertRegex(
        message
      , r'^type mismatch in element 2 of the list in (element 1 of the list in ){7}'
        r'\.\.\. in the expression\n'
      )
    self.assertIn("  element 1 of the list fixed the type Int (from 1)", message)
    self.assertIn("  element 2 of the list has type [Char] (from ('a' :: [Char]))", message)


def plus_one(e):
  return (symbol('+'))(e, 1)


def node_expr(*args, **kwds):
  return cytest.raw.expr(*args, typed=True, **kwds)

def node_values(*args):
  return [cytest.raw.interp().topython(v) for v in
      cytest.raw.values(node_expr(*args))]

def node_texts(*args):
  return [floats(str(v)) for v in cytest.raw.values(node_expr(*args))]

class TestNodeBuilder(cytest.TestCase):
  """Internal graph typing, dictionary arguments and the node-walk cap."""

  def check(self, pattern, *args):
    with self.assertRaisesRegex(curry.CurryTypeError, pattern) as caught:
      node_expr(*args)
    return caught.exception

  def test_target(self):
    P = prelude()
    plus = symbol('+')
    target = node_expr(P.id, 0)
    e = node_expr(plus, 1, 2, target=target)
    self.assertIs(e, target)
    self.assertEqual(str(target), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2')
    self.assertEqual(node_values(target), [3])
    target = node_expr(P.id, 0)
    node_expr([1, 2], target=target)
    # The C++ backend forwards the target to the new node; the Python
    # backend rewrites it in place.
    self.assertEqual(cytest.raw.interp().topython(inspect.fwd_chain_target(target)), [1, 2])
    self.assertEqual(curry.typeof(target, defaulted=True), '[Int]')
    target = node_expr(P.id, 0)
    node_expr(P.Just, 1, exprtype='Maybe Float', target=target)
    self.assertEqual(node_texts(target), ['Just 1.0'])

  def test_unboxed_and_fundamental(self):
    P = prelude()
    e = node_expr([P.Int, cytest.raw.unboxed(3)])
    self.assertEqual(str(e), '3')
    self.assertEqual(curry.typeof(e), 'Int')
    self.assertEqual(node_values(symbol('+'), e, 1), [4])
    # The marker outside a primitive is an error (issue #107; the four
    # placements are in unit_expr.py).
    with self.assertRaisesRegex(curry.CurryTypeError, 'stands alone'):
      node_expr(cytest.raw.unboxed(3))
    with self.assertRaisesRegex(curry.CurryTypeError, 'stands alone'):
      node_expr(cytest.raw.unboxed(3), target=node_expr(P.id, 0))
    e = node_expr(curry.expressions.fwd(1))
    self.assertTrue(inspect.isa_fwd(e))
    self.assertEqual(curry.typeof(e), 'Num a => a')
    self.assertEqual(node_values(e), [1])
    fsyms = cytest.raw.interp().backend.fundamental_symbols
    e = node_expr([fsyms.Fwd, 1])
    self.assertTrue(inspect.isa_fwd(e))
    self.assertEqual(curry.typeof(e), 'a')
    self.assertEqual(node_values(P.id, cytest.raw.fail), [])

  def test_explicit_dictionaries(self):
    '''
    Dictionaries passed before the value arguments fill the dictionary
    parameters; the scheme is then taken without its context.
    '''
    P = prelude()
    num_int = symbol('_inst#Prelude.Num#Prelude.Int')
    plus = symbol('+')
    self.assertEqual(node_values(P.apply, [P.apply, [plus, num_int], 1], 2), [3])
    data_int = symbol('_inst#Prelude.Data#Prelude.Int')
    x = cytest.raw.free()
    self.assertEqual(node_values(getattr(P, '=:='), data_int, x, 1), [True])
    self.assertEqual(node_values(getattr(P, '=:='), node_expr(data_int), x, 1), [True])
    self.assertEqual(node_values(getattr(P, '=:='), [data_int], x, 1), [True])
    e = node_expr(num_int)
    self.assertTrue(builder.TypedBuilder.is_dictionary(e))
    self.assertFalse(builder.TypedBuilder.is_dictionary(node_expr(1)))
    with self.assertRaisesRegex(curry.CurryTypeError, 'pass all of them or none'):
      node_expr(P.fromIntegral, num_int, 3)

  def test_kinds_of_nodes(self):
    P = prelude()
    x = cytest.raw.free()
    v, = cytest.raw.values(node_expr(P.id, x))
    self.assertTrue(inspect.isa_freevar(v))
    self.assertEqual(curry.typeof(v), 'a')
    self.assertEqual(curry.typeof(cytest.raw.expr(curry.choice(1, 2))), 'Num a => a')
    self.assertEqual(curry.typeof(cytest.raw.expr(cytest.raw.fail)), 'a')
    g = cytest.raw.expr(itertools.count())
    self.assertEqual(curry.typeof(g), '[a]')
    self.assertEqual(node_values(P.take, 2, g), [[0, 1]])
    s = cytest.raw.expr('ab')
    self.assertEqual(curry.typeof(s), '[Char]')
    self.assertEqual(node_values(P.length, s), [2])
    self.assertEqual(curry.typeof(cytest.raw.expr(True)), 'Bool')
    self.assertEqual(curry.typeof(cytest.raw.expr(2.5)), 'Float')
    # A function node without a scheme is an opaque leaf.
    self.assertEqual(curry.typeof(cytest.raw.expr(P._biGenerator, iter([]))), '[a]')
    # An ill-typed raw graph is reported where it fails to unify.
    bad = cytest.raw.expr(symbol('plusInt'), 1, 2.5)
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in argument 1 of Prelude.id'):
      node_expr(P.id, bad)
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in the expression'):
      curry.typeof(bad)

  def test_exponential_type(self):
    '''
    A value that shares a node between the components of a pair at every
    level has a type exponential in its size; the walk refuses it with the
    error of the cap instead of expanding the type.
    '''
    P = prelude()
    make = cytest.raw.interp().backend.make_node
    pair = P['(,)']
    node = make(P.Int, 0)
    for _ in range(25):
      node = make(pair, node, node)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^the type of the value at the expression has more than 100000 nodes; "
        r".*$"
      ):
      curry.typeof(node)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^the type of the value at argument 1 of Prelude\.fst :: \(a, b\) -> a has more than'
      ):
      node_expr(P.fst, node)
    small = make(P.Int, 0)
    for _ in range(5):
      small = make(pair, small, small)
    self.assertEqual(len(curry.typeof(small)), 220)

  def test_cap(self):
    '''The node walk stops at its cap; an internal annotation bypasses it.'''
    P = prelude()
    self.assertEqual(builder.VALUE_WALK_CAP, 100000)
    big = biglist(100001)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^the value at argument 2 of Prelude\.take :: Int -> \[a\] -> \[a\] has more "
        r"than 100000 nodes; .*$"
      ):
      node_expr(P.take, 2, big)
    self.assertEqual(node_values(P.take, 2, cytest.raw.typed(big, '[Int]')), [[0, 1]])
    # A node the internal builder returned is typed by its record, without a walk.
    recorded = node_expr(list(range(100001)))
    self.assertEqual(node_values(P.take, 2, recorded), [[0, 1]])

  def test_record(self):
    '''The result type is recorded weakly, by the identity of the node.'''
    interp = cytest.raw.interp()
    P = prelude()
    record = builder.record_of(interp)
    e = node_expr(P.Just, 1)
    scheme, typeexpr = builder.recorded(interp, e)
    self.assertEqual(str(scheme), 'Num a => Maybe a')
    self.assertEqual(curry.typecheck.show_type(typeexpr), 'Maybe Int')
    self.assertEqual(builder.result_type(interp, e), typeexpr)
    self.assertIsNone(builder.recorded(interp, cytest.raw.expr(P.Just, 1)))
    self.assertIsNone(builder.result_type(interp, 1))
    before = len(record)
    del e, scheme, typeexpr
    gc.collect()
    self.assertEqual(len(record), before - 1)
    # A value of an evaluation is a copy: no record, the walk types it.
    v = next(cytest.raw.values(node_expr([1.5])))
    self.assertIsNone(builder.recorded(interp, v))
    self.assertEqual(curry.typeof(v), '[Float]')

  def test_raw_expr_unchanged(self):
    P = prelude()
    self.assertEqual(str(cytest.raw.expr(cytest.raw.typed(5, 'Float'))), '5')
    self.assertEqual(str(cytest.raw.expr(cytest.raw.free(exprtype='Int'))), '_a')
    self.assertEqual(str(cytest.raw.expr(getattr(P, 'not'), 1)), 'not 1')
    self.assertEqual(str(cytest.raw.expr('ab')), '"ab"')

  def test_value_above_the_cap(self):
    P = prelude()
    big = biglist(100001)
    err = self.check(
        r"^the value at argument 2 of Prelude\.take :: Int -> \[a\] -> \[a\] has more than "
        r"100000 nodes; .*$"
      , P.take, 1, big
      )
    self.assertIsInstance(err, errors.ValueTooLargeError)
