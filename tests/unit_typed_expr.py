'''
The typed ``curry.expr``, item Y7 of the typed boundary (#56, epic #48).

``curry.expr`` describes its arguments as a tree of specs, types the tree
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
  return curry.symbol('Prelude.' + name)

def values(*args, **kwds):
  '''The values of a goal, converted to Python.'''
  return list(curry.eval(*args, converter='topython', **kwds))

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

def texts(*args, **kwds):
  '''The values of a goal as Curry text.'''
  return [floats(str(value)) for value in curry.eval(*args, converter=None, **kwds)]

def deep(n, plus=None):
  '''A left-deep description of ``n`` applications of Prelude.+ to 1.'''
  plus = symbol('+') if plus is None else plus
  e = 1
  for _ in range(n):
    e = [plus, e, 1]
  return e

def biglist(n):
  '''A Curry list of ``n`` integers made node by node: no record of its type.'''
  P = prelude()
  make = curry.getInterpreter().backend.make_node
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
    e = curry.expr(plus, 1, 2)
    self.assertEqual(str(e), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2')
    self.assertEqual(curry.typeof(e), 'Num a => a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Int')
    # The evaluation rewrites the expression in place.
    self.assertEqual(values(e), [3])
    self.assertEqual(str(e), '3')
    self.assertEqual(values(plus, 1, 2), [3])
    e = curry.expr(plus, 1.5, 1)
    self.assertIn('_inst#Prelude.Num#Prelude.Float', str(e))
    self.assertEqual(curry.typeof(e), 'Fractional a => a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Float')
    self.assertEqual(values(e), [2.5])

  def test_show_just(self):
    '''show over Maybe Int: the dictionary of Maybe takes the dictionary of Int.'''
    P = prelude()
    e = curry.expr(P.show, [P.Just, 1])
    self.assertIn('_inst#Prelude.Show#Prelude.Maybe', str(e))
    self.assertIn('_inst#Prelude.Show#Prelude.Int', str(e))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Char]')
    self.assertEqual(values(e), ['Just 1'])
    self.assertEqual(values(P.show, [P.Just, 1]), ['Just 1'])

  def test_exprtype(self):
    '''exprtype fixes the type of the expression; the literal follows it.'''
    P = prelude()
    e = curry.expr(P.Just, 5, exprtype='Maybe Float')
    self.assertEqual(texts(e), ['Just 5.0'])
    self.assertEqual(curry.typeof(e, defaulted=True), 'Maybe Float')
    e = curry.expr(P.read, '5', exprtype='Int')
    self.assertEqual(values(e), [5])
    self.assertEqual(texts(curry.expr(1, exprtype='Float')), ['1.0'])

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
        curry.expr(*args)
      with self.assertRaises(curry.CurryTypeError):
        curry.eval(*args)
    # The error is a TypeError too, as every CurryTypeError is.
    with self.assertRaises(TypeError):
      curry.expr(getattr(P, 'not'), 1)

  def test_read_ambiguity(self):
    '''read "5" is ambiguous: the table rejects Read a with the oracle's words.'''
    P = prelude()
    with self.assertRaises(curry.CurryTypeError) as cm:
      curry.expr(P.read, '5')
    message = str(cm.exception)
    self.assertRegex(message, r'^cannot handle the overloaded expression \'read "5"\' of type Read a => a\n')
    self.assertIn(ORACLE_SENTENCE, message)
    self.assertEqual(values(P.read, curry.typed('5', 'String'), exprtype='Int'), [5])
    self.assertEqual(values(curry.expr(P.read, '5', exprtype='Int')), [5])

  def test_free_at_function_type(self):
    P = prelude()
    x = curry.free()
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^free variable at argument 1 of Prelude\.map :: \(a -> b\) -> \[a\] -> \[b\] '
        r'would have the function type a -> b\n'
        r'  Curry free variables must have a Data type$'
      ):
      curry.expr(P.map, x, [1, 2])

  def test_large_descriptions(self):
    '''
    A list of 10000 values and a left-deep tree of 10^4 applications build:
    the conversion, the typing and the materialization walk with explicit
    stacks.  The Python backend evaluates the small forms only.
    '''
    P = prelude()
    big = curry.expr(list(range(10000)))
    self.assertEqual(curry.typeof(big, defaulted=True), '[Int]')
    self.assertEqual(len(curry.topython(big)), 10000)
    self.assertEqual(values(P.take, 3, big), [[0, 1, 2]])
    tree = curry.expr(deep(10000))
    self.assertEqual(curry.typeof(tree), 'Num a => a')
    self.assertEqual(curry.typeof(tree, defaulted=True), 'Int')
    self.assertEqual(values(curry.expr(deep(100))), [101])
    if IS_CXX:
      self.assertEqual(values(P.length, big), [10000])
      self.assertEqual(values(tree), [10001])
    # The depth of a type is bounded by the recursion limit: the engine
    # walks a type recursively.  A list nested 500 deep is fine.
    nested = 1
    for _ in range(500):
      nested = [nested]
    e = curry.expr(nested)
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
    v = next(curry.eval(curry.expr([1.5, 2.5])))
    self.assertEqual(curry.typeof(v), '[Float]')
    total, = values(DL.sum, v)
    self.assertIsInstance(total, float)
    self.assertEqual(total, 4.0)
    r = next(curry.eval(P.Just, 1))
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 1\.5 to Int at argument 2 of Prelude\.\+ :: Num a => a -> a -> a\n'
        r'  argument 1 fixed a := Int \(from Data\.Maybe\.fromJust <value>\)$'
      ):
      curry.expr(plus, [DM.fromJust, r], 1.5)
    # The other order: the value meets the type the literal fixed, inside
    # fromJust, where the expected type arrived from above.
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^type mismatch in argument 1 of Data\.Maybe\.fromJust :: Maybe a -> a\n'
        r'  argument 1 fixed a := Float \(from 1\.5\)\n'
        r'  argument 1 has type Int \(from <value>\)$'
      ):
      curry.expr(plus, 1.5, [DM.fromJust, r])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'  argument 2 has type Maybe Int \(from <value>\)$'
      ):
      curry.expr(plus, 1.5, r)
    # A node curry.expr returned is typed by its record, also after its
    # evaluation rewrote it.
    e = curry.expr([1.5, 2.5])
    self.assertEqual(values(DL.sum, e), [4.0])
    self.assertEqual(values(DL.sum, e), [4.0])
    self.assertEqual(curry.typeof(curry.expr(DL.sum, e), defaulted=True), 'Float')

  def test_iterator_item_mismatch(self):
    '''
    The element type of an iterator is fixed at construction; an item that
    does not convert ends the evaluation with an EvaluationError, inside ?
    and inside a set function too.
    '''
    P = prelude()
    DL = curry.import_('Data.List')
    SF = curry.module('Control.SetFunctions')
    pattern = (
        r'^cannot convert item 2\.5 of the iterator at argument 1 of '
        r'Data\.List\.sum :: Num a => \[a\] -> a to Int$'
      )
    with self.assertRaisesRegex(curry.EvaluationError, pattern) as cm:
      values(DL.sum, iter([1, 2.5]))
    self.assertIsInstance(cm.exception.__cause__, curry.CurryTypeError)
    with self.assertRaisesRegex(curry.EvaluationError, pattern):
      values(getattr(P, '?'), [DL.sum, iter([1, 2.5])], 7)
    with self.assertRaisesRegex(
        curry.EvaluationError
      , r'^cannot convert item 2\.5 of the iterator at argument 2 of '
        r'Control\.SetFunctions\.set1 :: \(a -> b\) -> a -> Values b to Int$'
      ):
      values(SF.values2list, [SF.set1, DL.sum, iter([1, 2.5])])
    # The items that convert are fine, and a polymorphic element type lets
    # each item convert by its Python type.
    self.assertEqual(values(DL.sum, iter([1, 2])), [3])
    self.assertEqual(values(P.take, 3, itertools.count()), [[0, 1, 2]])
    self.assertEqual(values(P.take, 2, iter([1, 'a'])), [[1, 'a']])
    self.assertEqual(values(P.take, 2, iter([1, 2.5]), exprtype='[Float]'), [[1.0, 2.5]])
    self.assertEqual(values(P.unlines, iter(['a', 'bc'])), ['a\nbc\n'])
    self.assertEqual(values(P.concat, iter(['ab', 'c'])), ['abc'])
    self.assertEqual(values(P.unwords, iter([curry.expr('xy'), 'z'])), ['xy z'])
    self.assertEqual(values(P.length, iter([(1, 'a'), (2, 'b')])), [2])
    self.assertEqual(values(P.length, iter([curry.free(), curry.free()])), [2])
    with self.assertRaisesRegex(
        curry.EvaluationError
      , r"^cannot convert item 'ab' of the iterator at argument 1 of Prelude\.reverse :: \[a\] -> \[a\] to Char$"
      ):
      values(P.ord, [P.head, [P.reverse, iter(['a', 'ab'])]])

  def test_rewritten_tests_hold(self):
    '''
    The two tests the item rewrote, in short: a method applied from Python
    and the empty string that converts to ''.
    '''
    P = prelude()
    apply_ = P.apply
    plus = symbol('+')
    incr = curry.expr(plus, 1)
    self.assertEqual(curry.typeof(incr, defaulted=True), 'Int -> Int')
    self.assertEqual(values(apply_, incr, 6), [7])
    y, = curry.eval(curry.expr(''), converter='topython')
    self.assertEqual(y, '')

class TestConversion(cytest.TestCase):
  '''The conversion of Python values by the expected type.'''

  def test_numbers(self):
    P = prelude()
    DM = curry.import_('Data.Maybe')
    self.assertEqual(texts(DM.fromJust, [P.Just, 1], exprtype='Float'), ['1.0'])
    e = curry.expr([1, 2.5])
    self.assertEqual(curry.typeof(e), 'Fractional a => [a]')
    self.assertEqual(curry.typeof(e, defaulted=True), '[Float]')
    self.assertEqual(values(e), [[1.0, 2.5]])
    self.assertEqual(curry.typeof(curry.expr(1)), 'Num a => a')
    self.assertEqual(curry.typeof(curry.expr(1), defaulted=True), 'Int')
    self.assertEqual(values(symbol('/'), 3, 2), [1.5])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 2\.5 to Int at argument 2 of Prelude\.plusInt :: Int -> Int -> Int$'
      ):
      curry.expr(symbol('plusInt'), 1, 2.5)

  def test_literal_at_a_user_type(self):
    '''An int under a type with its own Num instance goes through fromInt.'''
    M = curry.import_('TypeCheck')
    e = curry.expr(M.toInt, 3)
    self.assertEqual(curry.typeof(e, defaulted=True), 'Int')
    self.assertIn('fromInt', str(e))
    self.assertEqual(values(e), [3])
    e = curry.expr(M.twice, 2, exprtype='Nat')
    self.assertEqual(curry.typeof(e, defaulted=True), 'TypeCheck.Nat')
    self.assertEqual(texts(e), ['S (S (S (S Z)))'])
    self.assertEqual(texts(M.twice, 2, exprtype='Nat'), ['S (S (S (S Z)))'])
    self.assertEqual(texts(M.twice, 2), ['4'])

  def test_strings(self):
    '''
    A str under [Char] is one string, whatever its length; a one-character
    str under a bare type variable stays Char.
    '''
    P = prelude()
    s = curry.expr('hello')
    if IS_CXX:
      # The binding builds the list the step of _biString would build.
      self.assertTrue(inspect.isa_cons(s))
    else:
      self.assertEqual(s.info.name, '_biString')
    self.assertEqual(curry.topython(s), 'hello')
    self.assertEqual(values(s), ['hello'])
    self.assertEqual(curry.typeof(s, defaulted=True), '[Char]')
    self.assertEqual(values(P.length, 'a'), [1])
    self.assertEqual(values(P.length, 'hello'), [5])
    self.assertEqual(values(P.length, curry.typed('a', 'String')), [1])
    self.assertEqual(values(P.reverse, 'ab'), ['ba'])
    c = curry.expr('a')
    self.assertTrue(inspect.isa_boxed_char(c))
    self.assertEqual(curry.typeof(c), 'Char')
    self.assertEqual(curry.typeof(curry.expr(P.id, 'a'), defaulted=True), 'Char')
    self.assertEqual(values(P.ord, 'a'), [97])
    self.assertEqual(values(P.id, 'ab'), ['ab'])
    self.assertEqual(curry.typeof(curry.expr(P.id, 'ab'), defaulted=True), '[Char]')
    # Under an open type a one-character str is a weak mark for Char: a
    # string beside it makes the list [String] in either order, and a type
    # that only a list can fill makes it a string.
    self.assertEqual(values(['ab', 'c']), [['ab', 'c']])
    self.assertEqual(values(['c', 'ab']), [['c', 'ab']])
    self.assertEqual(values(curry.choice('c', 'ab')), ['c', 'ab'])
    self.assertEqual(values(curry.choice('ab', 'c')), ['ab', 'c'])
    self.assertEqual(values(P.fmap, P.ord, 'a'), [[97]])
    self.assertEqual(texts(P.Just, 'a', exprtype='Maybe String'), ['Just "a"'])
    self.assertEqual(curry.typeof(('a', 'bc')), '(Char, [Char])')
    self.assertEqual(curry.typeof(curry.expr(P.Just, 'a'), defaulted=True), 'Maybe Char')
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^cannot convert 'a' to Bool at element 1 of the list in the expression\n"
        r"  element 2 of the list has type Bool \(from True\)$"
      ):
      curry.expr(['a', True])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^type mismatch in element 1 of the list in the expression\n"
        r"  element 2 of the list fixed the type Int \(from 1\)\n"
        r"  element 1 of the list has type Char \(from 'a'\)$"
      ):
      curry.expr(['a', 1])
    with self.assertRaisesRegex(
        curry.CurryTypeError, r'^exprtype a does not match the inferred type Char'
      ):
      curry.expr('a', exprtype='a')
    self.assertEqual(values(curry.expr('ä\U0001f600')), ['ä\U0001f600'])
    self.assertEqual(values(P.length, 'ä\U0001f600'), [2])
    self.assertEqual(values(curry.expr(b'bytes')), ['bytes'])
    with self.assertRaisesRegex(curry.EvaluationError, 'oops'):
      values(P.error, 'oops')

  def test_empty_string(self):
    '''
    The static type makes '' of an empty [Char]: through eval, which hands
    the type of the goal to the converter, and through topython(exprtype=).
    '''
    P = prelude()
    e = curry.expr('')
    self.assertTrue(inspect.isa_nil(e))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Char]')
    self.assertEqual(values(e), [''])
    self.assertEqual(values(P.reverse, curry.typed([], '[Char]')), [''])
    self.assertEqual(values(P.filter, P.isUpper, 'abc'), [''])
    self.assertEqual(values(P.reverse, []), [[]])
    self.assertEqual(values(P.show, 5), ['5'])
    self.assertEqual(values(P.id, ([], 'x')), [([], 'x')])
    self.assertEqual(values(P.id, curry.typed(([], 'x'), '([Char], [Char])')), [('', 'x')])
    self.assertEqual(curry.topython(curry.raw_expr([]), exprtype='[Char]'), '')
    self.assertEqual(curry.topython(curry.raw_expr([])), [])

  def test_bool_and_none(self):
    P = prelude()
    self.assertEqual(values(getattr(P, 'not'), True), [False])
    self.assertEqual(values(getattr(P, '&&'), True, False), [False])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert True to Int at argument 1 of Prelude\.plusInt'
      ):
      curry.expr(symbol('plusInt'), True, 1)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert None at argument 1 of Prelude\.Just :: a -> Maybe a; expected a$'
      ):
      curry.expr(P.Just, None)

  def test_lists_and_tuples(self):
    P = prelude()
    self.assertEqual(values(P.length, []), [0])
    self.assertEqual(curry.typeof(curry.expr([[1, 2], [3]]), defaulted=True), '[[Int]]')
    self.assertEqual(values(curry.expr(([1, 2], ('a', 2.5), True))), [([1, 2], ('a', 2.5), True)])
    self.assertEqual(curry.typeof(curry.expr(())), '()')
    self.assertEqual(values(P.fst, (1, 'a')), [1])
    self.assertEqual(values(P.snd, (1, 'a')), ['a'])
    with self.assertRaisesRegex(curry.CurryTypeError, 'Curry has no 1-tuple'):
      curry.expr((1,))
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^type mismatch in element 2 of the list in argument 1 of "
        r"Prelude\.length :: \[a\] -> Int\n"
        r"  element 1 of the list fixed the type Int \(from 1\)\n"
        r"  element 2 of the list has type Char \(from 'a'\)$"
      ):
      curry.expr(P.length, [1, 'a'])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^cannot convert 2\.5 to Int at element 2 of the list in argument 1 of "
        r"Prelude\.length :: \[a\] -> Int$"
      ):
      curry.expr(P.length, curry.typed([1, 2.5], '[Int]'))
    # A list headed by a symbol is an application; cons and nil build cells.
    self.assertEqual(values([P.length, [1, 2]]), [2])
    self.assertEqual(values(curry.cons(1, 2, curry.nil)), [[1, 2]])
    self.assertEqual(curry.typeof(curry.expr(curry.nil)), '[a]')

  def test_iterator_element_constraint(self):
    '''
    A class constraint on the element type of an iterator, which no item
    fixes, is the error of the table with a line that names curry.typed.
    '''
    P = prelude()
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^cannot handle the overloaded expression 'map show <iterator>' of type "
        r"Show a => \[\[Char\]\]\n"
        r'  ' + re.escape(ORACLE_SENTENCE) + r'\n'
        r'  add a type annotation \(exprtype\)\n'
        r'  ' + re.escape(engine.ITERATOR_HINT) + '$'
      ):
      curry.expr(P.map, P.show, iter([1, 2, 3]))
    self.assertEqual(
        values(P.map, P.show, curry.typed(iter([1, 2, 3]), '[Int]')), [['1', '2', '3']]
      )
    # The line is absent when the constraint sits elsewhere.
    with self.assertRaisesRegex(curry.CurryTypeError, r'add a type annotation \(exprtype\)$'):
      curry.expr(P.read, '5')

  def test_free_markers(self):
    '''
    A marker is one node, a call of unknown with the Data dictionary of
    its type: the dictionary of Bool for a polymorphic type, a real one
    for a ground type.  =:= takes its dictionary from the builder.
    '''
    P = prelude()
    x = curry.free()
    e = curry.expr(x)
    self.assertIs(curry.expr(x), e)
    self.assertEqual(str(e), 'unknown _inst#Prelude.Data#Prelude.Bool')
    self.assertEqual(curry.typeof(e), 'a')
    self.assertEqual(values(getattr(P, '=:='), x, 1), [True])
    y = curry.free(exprtype='[Int]')
    node = curry.expr(y)
    self.assertRegex(
        str(node), r'^unknown \(+_inst#Prelude\.Data#\[\] _inst#Prelude\.Data#Prelude\.Int\)+$'
      )
    self.assertEqual(curry.typeof(node, defaulted=True), '[Int]')
    z = curry.free()
    self.assertEqual(values(P.constrEq, (z, 2), (1, 2)), [True])
    w = curry.free()
    e = curry.expr(P.constrEq, w, [1, 2])
    self.assertEqual(curry.typeof(e, defaulted=True), 'Bool')
    self.assertIn('_inst#Prelude.Data#[]', str(e))
    self.assertEqual(values(e), [True])
    # A marker under a rigid exprtype variable stays polymorphic.
    v = curry.free()
    self.assertEqual(curry.typeof(curry.expr(P.id, v, exprtype='a')), 'a')

class TestForms(cytest.TestCase):
  '''The forms of the untyped builder on the typed path.'''

  def test_choice(self):
    P = prelude()
    self.assertEqual(sorted(values(getattr(P, 'not'), curry.choice(True, False))), [False, True])
    e = curry.expr(curry.choice(1, 2.5))
    self.assertEqual(curry.typeof(e, defaulted=True), 'Float')
    self.assertEqual(sorted(values(e)), [1.0, 2.5])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^type mismatch in argument 2 of Prelude\.\? :: a -> a -> a\n"
        r"  argument 1 fixed a := Int \(from 1\)\n"
        r"  argument 2 has type Char \(from 'a'\)$"
      ):
      curry.expr(curry.choice(1, 'a'))

  def test_anchors_and_references(self):
    P = prelude()
    anchor, ref = curry.expressions.anchor, curry.ref
    e = curry.expr(P.take, 2, anchor(curry.cons(1, ref())))
    self.assertEqual(values(e), [[1, 1]])
    e = curry.expr(P.take, 3, ref('xs'), xs=curry.cons(7, ref('xs')))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Int]')
    self.assertEqual(values(e), [[7, 7, 7]])
    # The reference shares the type of its anchor.
    with self.assertRaises(curry.CurryTypeError):
      curry.expr(P.take, 'a', ref('xs'), xs=curry.cons(7, ref('xs')))
    with self.assertRaisesRegex(ValueError, 'undefined anchor'):
      curry.expr(ref('nowhere'))
    # The trivial cycle a = a.
    e = curry.expr(anchor(ref()))
    self.assertTrue(inspect.isa_fwd(e))
    # A keyword anchor may refer to one that comes later, as with raw_expr.
    e = curry.expr(
        P.take, 3, ref('a'), a=curry.cons(1, ref('b')), b=curry.cons(2, ref('a'))
      )
    self.assertEqual(values(e), [[1, 2, 1]])
    self.assertEqual(curry.typeof(e, defaulted=True), '[Int]')
    with self.assertRaisesRegex(ValueError, 'multiple definitions'):
      curry.expr(
          P.take, 3, anchor(curry.cons(1, ref('a')), name='a'), a=curry.cons(2, ref('a'))
        )

  def test_nodes_pass_through(self):
    '''A bare node alone passes through untouched; a nested one is typed.'''
    P = prelude()
    n = curry.expr(1)
    self.assertIs(curry.expr(n), n)
    self.assertIsNot(curry.expr([n]), n)
    self.assertEqual(curry.topython(curry.expr([n])), [1])
    e = curry.expr(P.length, curry.expr(P.reverse, [1, 2, 3]))
    self.assertEqual(values(e), [3])
    raw = curry.raw_expr(P.take, 2, [1, 2, 3])
    self.assertEqual(curry.typeof(raw), '[Int]')
    self.assertEqual(values(P.length, raw), [2])
    self.assertEqual(curry.typeof(curry.raw_expr(getattr(P, 'not'), True)), 'Bool')
    # A node whose type disagrees with its position.
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^type mismatch in argument 1 of Prelude\.not :: Bool -> Bool\n'
        r'  expected Bool\n'
        r'  argument 1 has type Maybe Int \(from <value>\)$'
      ):
      curry.expr(getattr(P, 'not'), curry.expr(P.Just, 1))

  def test_target(self):
    P = prelude()
    plus = symbol('+')
    target = curry.expr(P.id, 0)
    e = curry.expr(plus, 1, 2, target=target)
    self.assertIs(e, target)
    self.assertEqual(str(target), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2')
    self.assertEqual(values(target), [3])
    target = curry.expr(P.id, 0)
    curry.expr([1, 2], target=target)
    # The C++ backend forwards the target to the new node; the Python
    # backend rewrites it in place.
    self.assertEqual(curry.topython(inspect.fwd_chain_target(target)), [1, 2])
    self.assertEqual(curry.typeof(target, defaulted=True), '[Int]')
    target = curry.expr(P.id, 0)
    curry.expr(P.Just, 1, exprtype='Maybe Float', target=target)
    self.assertEqual(texts(target), ['Just 1.0'])

  def test_unboxed_and_fundamental(self):
    P = prelude()
    e = curry.expr([P.Int, curry.unboxed(3)])
    self.assertEqual(str(e), '3')
    self.assertEqual(curry.typeof(e), 'Int')
    self.assertEqual(values(plus_one(e)), [4])
    self.assertEqual(curry.expr(curry.unboxed(3)), 3)
    self.assertEqual(curry.expr(curry.unboxed('a')), 'a')
    with self.assertRaises(ValueError):
      curry.expr(curry.unboxed(3), target=curry.expr(P.id, 0))
    e = curry.expr(curry.expressions.fwd(1))
    self.assertTrue(inspect.isa_fwd(e))
    self.assertEqual(curry.typeof(e), 'Num a => a')
    self.assertEqual(values(e), [1])
    fsyms = curry.getInterpreter().backend.fundamental_symbols
    e = curry.expr([fsyms.Fwd, 1])
    self.assertTrue(inspect.isa_fwd(e))
    self.assertEqual(curry.typeof(e), 'a')
    self.assertEqual(values(P.id, curry.fail), [])

  def test_explicit_dictionaries(self):
    '''
    Dictionaries passed before the value arguments fill the dictionary
    parameters; the scheme is then taken without its context.
    '''
    P = prelude()
    num_int = symbol('_inst#Prelude.Num#Prelude.Int')
    plus = symbol('+')
    self.assertEqual(values(P.apply, [P.apply, [plus, num_int], 1], 2), [3])
    data_int = symbol('_inst#Prelude.Data#Prelude.Int')
    x = curry.free()
    self.assertEqual(values(getattr(P, '=:='), data_int, x, 1), [True])
    self.assertEqual(values(getattr(P, '=:='), curry.expr(data_int), x, 1), [True])
    self.assertEqual(values(getattr(P, '=:='), [data_int], x, 1), [True])
    e = curry.expr(num_int)
    self.assertTrue(builder.TypedBuilder.is_dictionary(e))
    self.assertFalse(builder.TypedBuilder.is_dictionary(curry.expr(1)))
    with self.assertRaisesRegex(curry.CurryTypeError, 'pass all of them or none'):
      curry.expr(P.fromIntegral, num_int, 3)

  def test_unsigned_goal(self):
    '''curry.expr of a goal without a signature supplies its dictionaries.'''
    M = curry.import_('UnsignedGoals')
    e = curry.expr(M.main14)
    self.assertEqual(str(e), 'main14 _inst#Prelude.Num#Prelude.Int')
    self.assertEqual(texts(e), ['Just 5'])
    self.assertEqual(curry.typeof(e), 'Num a => Maybe a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Maybe Int')
    self.assertEqual(values(M.addOne, 1), [2])
    self.assertEqual(values(M.addOne, 1.5), [2.5])
    self.assertEqual(texts(curry.expr(M.main21)), ['[1.0, 2.5]'])
    with self.assertRaisesRegex(curry.CurryTypeError, ORACLE_SENTENCE):
      curry.expr(M.main17)

  def test_arity_forms(self):
    '''Fewer arguments give a partial application; more go through apply.'''
    P = prelude()
    plus = symbol('+')
    e = curry.expr(P.map, getattr(P, 'not'))
    self.assertEqual(curry.typeof(e, defaulted=True), '[Bool] -> [Bool]')
    self.assertEqual(values(P.apply, e, [True]), [[False]])
    self.assertEqual(values(P.id, P.id, 5), [5])
    self.assertEqual(values(P.id, plus, 1, 2), [3])
    incr = curry.expr(plus, 1)
    self.assertEqual(values(P.apply, incr, 6), [7])
    # A partial application fed back is typed by its head: an ill-typed one
    # of raw_expr is reported where it fails to unify.
    self.assertEqual(curry.typeof(curry.raw_expr(P.apply, P.id)), 'a -> a')
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in the expression'):
      curry.typeof(curry.raw_expr(P.apply, 1))
    with self.assertRaisesRegex(
        curry.CurryTypeError, r'^Prelude\.Just :: a -> Maybe a takes 1 argument, 2 given$'
      ):
      curry.expr(P.Just, 1, 2)

  def test_newtype(self):
    '''A newtype constructor is erased, as the ICurry translation erases it.'''
    ID = curry.import_('Data.Functor.Identity')
    e = curry.expr(ID.Identity, 5)
    # The printer qualifies the names outside the Prelude.
    self.assertEqual(curry.typeof(e, defaulted=True), 'Data.Functor.Identity.Identity Int')
    self.assertEqual(str(e), '5')
    self.assertEqual(values(e), [5])
    self.assertEqual(values(ID.runIdentity, [ID.Identity, 5]), [5])
    self.assertEqual(
        curry.typeof(curry.expr(ID.Identity)), 'a -> Data.Functor.Identity.Identity a'
      )
    P = prelude()
    self.assertEqual(values(ID.runIdentity, curry.expr(P.apply, ID.Identity, 5)), [5])

  def test_argument_errors(self):
    P = prelude()
    with self.assertRaisesRegex(curry.CurryTypeError, 'invalid arguments after 1'):
      curry.expr(1, 2)
    with self.assertRaisesRegex(curry.CurryTypeError, 'takes an expression'):
      curry.expr()
    with self.assertRaisesRegex(curry.CurryTypeError, "cannot build a Curry expression from type 'object'"):
      curry.expr(object())

class TestValueWalk(cytest.TestCase):
  '''A Curry node that fills a parameter is typed by a walk of its content.'''

  def test_shared_and_cyclic(self):
    node = curry.expr(0)
    for _ in range(16):
      node = curry.expr((node, node))
    text = curry.typeof(node)
    self.assertTrue(text.startswith('(' * 16 + 'Int, Int)'))
    P = prelude()
    anchor, ref = curry.expressions.anchor, curry.ref
    cyclic = curry.raw_expr(anchor(curry.cons(1, ref())))
    self.assertEqual(curry.typeof(cyclic), '[Int]')
    self.assertEqual(values(P.take, 2, cyclic), [[1, 1]])

  def test_kinds_of_nodes(self):
    P = prelude()
    x = curry.free()
    v, = curry.eval(P.id, x)
    self.assertTrue(inspect.isa_freevar(v))
    self.assertEqual(curry.typeof(v), 'a')
    self.assertEqual(curry.typeof(curry.raw_expr(curry.choice(1, 2))), 'Int')
    self.assertEqual(curry.typeof(curry.raw_expr(curry.fail)), 'a')
    g = curry.raw_expr(itertools.count())
    self.assertEqual(curry.typeof(g), '[a]')
    self.assertEqual(values(P.take, 2, g), [[0, 1]])
    s = curry.raw_expr('ab')
    self.assertEqual(curry.typeof(s), '[Char]')
    self.assertEqual(values(P.length, s), [2])
    self.assertEqual(curry.typeof(curry.raw_expr(True)), 'Bool')
    self.assertEqual(curry.typeof(curry.raw_expr(2.5)), 'Float')
    # A function node without a scheme is an opaque leaf.
    self.assertEqual(curry.typeof(curry.raw_expr(P._biGenerator, iter([]))), '[a]')
    # An ill-typed raw graph is reported where it fails to unify.
    bad = curry.raw_expr(symbol('plusInt'), 1, 2.5)
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in argument 1 of Prelude.id'):
      curry.expr(P.id, bad)
    with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in the expression'):
      curry.typeof(bad)

  def test_partial_application(self):
    '''
    A partial application is typed by the scheme of its head and the
    arguments it holds, so an ill-typed application of it is refused at
    construction instead of crashing the runtime.
    '''
    P = prelude()
    plus = symbol('+')
    v = next(curry.eval(P.map, getattr(P, 'not')))
    self.assertTrue(v.info.is_partial)
    self.assertEqual(curry.typeof(v), '[Bool] -> [Bool]')
    self.assertEqual(values(P.apply, v, [True, False]), [[False, True]])
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^cannot convert 1 to \[Bool\] at argument 2 of Prelude\.apply :: \(a -> b\) -> a -> b$'
      ):
      curry.expr(P.apply, v, 1)
    # A method with its dictionary: the dictionary is skipped and the value
    # argument fixes the type.
    incr = next(curry.eval(curry.expr(plus, 1)))
    self.assertTrue(incr.info.is_partial)
    self.assertEqual(curry.typeof(incr), 'Int -> Int')
    self.assertEqual(values(P.apply, incr, 2), [3])
    with self.assertRaises(curry.CurryTypeError):
      curry.expr(P.apply, incr, 2.5)
    # A constructor with a missing argument.
    j = next(curry.eval(curry.expr(P.Just)))
    self.assertEqual(curry.typeof(j), 'a -> Maybe a')
    self.assertEqual(texts(P.apply, j, 'x'), ["Just 'x'"])
    # A method without its dictionary stays an opaque leaf.
    self.assertEqual(curry.typeof(curry.raw_expr(plus)), 'a')

  def test_exponential_type(self):
    '''
    A value that shares a node between the components of a pair at every
    level has a type exponential in its size; the walk refuses it with the
    error of the cap instead of expanding the type.
    '''
    P = prelude()
    make = curry.getInterpreter().backend.make_node
    pair = curry.symbol('Prelude.(,)')
    node = make(P.Int, 0)
    for _ in range(25):
      node = make(pair, node, node)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^the type of the value at the expression has more than 100000 nodes; "
        r"pass curry\.typed\(node, 'T'\)$"
      ):
      curry.typeof(node)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r'^the type of the value at argument 1 of Prelude\.fst :: \(a, b\) -> a has more than'
      ):
      curry.expr(P.fst, node)
    small = make(P.Int, 0)
    for _ in range(5):
      small = make(pair, small, small)
    self.assertEqual(len(curry.typeof(small)), 220)

  def test_cap(self):
    '''The walk stops at the cap; curry.typed states the type instead.'''
    P = prelude()
    self.assertEqual(builder.VALUE_WALK_CAP, 100000)
    big = biglist(100001)
    with self.assertRaisesRegex(
        curry.CurryTypeError
      , r"^the value at argument 2 of Prelude\.take :: Int -> \[a\] -> \[a\] has more "
        r"than 100000 nodes; pass curry\.typed\(node, 'T'\)$"
      ):
      curry.expr(P.take, 2, big)
    self.assertEqual(values(P.take, 2, curry.typed(big, '[Int]')), [[0, 1]])
    # A node curry.expr returned is typed by its record, without a walk.
    recorded = curry.expr(list(range(100001)))
    self.assertEqual(values(P.take, 2, recorded), [[0, 1]])

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
    self.assertEqual(curry.typeof([1, 2.5]), 'Fractional a => [a]')
    self.assertEqual(curry.typeof([1, 2.5], defaulted=True), '[Float]')
    self.assertEqual(curry.typeof(('a', True)), '(Char, Bool)')
    self.assertEqual(curry.typeof(P.length, defaulted=True), '[a] -> Int')
    # A lone symbol is defaulted as a goal: Show alone is not defaultable.
    with self.assertRaisesRegex(curry.CurryTypeError, ORACLE_SENTENCE):
      curry.typeof(P.show, defaulted=True)
    self.assertEqual(symbol('+').signature, 'Num a => a -> a -> a')
    with self.assertRaises(curry.CurryTypeError):
      curry.typeof([P.show, []], defaulted=True)
    # The context in the order of the front end: by the first type variable
    # of the constraint, then by the class.
    from curry.interpreter.compile import expression_scheme
    interp = curry.getInterpreter()
    for args, text in [((1, 2.5), '(1, 2.5)'), ((1, 'a', 2.5), "(1, 'a', 2.5)")]:
      self.assertEqual(curry.typeof(args), str(expression_scheme(interp, text)))
    self.assertEqual(curry.typeof(curry.expr((1, 2.5))), '(Num a, Fractional b) => (a, b)')
    self.assertEqual(curry.typeof((1, 'a', 2.5)), '(Num a, Fractional b) => (a, Char, b)')
    self.assertEqual(
        curry.typeof([P.show, [plus, curry.free(), 1]]), '(Num a, Show a) => [Char]'
      )
    # A lone symbol without a scheme has no type, though expr builds it.
    with self.assertRaisesRegex(
        curry.CurryTypeError, r'^no type for Prelude\._biGenerator: .*; use raw_expr$'
      ):
      curry.typeof(P._biGenerator)
    self.assertTrue(curry.expr(P._biGenerator).info.is_partial)

  def test_describe(self):
    P = prelude()
    plus = symbol('+')
    d = curry.describe(plus, 1, 2)
    self.assertEqual(str(d), '1 + 2')
    self.assertEqual(d.typeof(), 'Num a => a')
    self.assertEqual(d.typeof(defaulted=True), 'Int')
    self.assertEqual(values(d), [3])
    self.assertEqual(values(curry.expr(d)), [3])
    self.assertEqual(values(d.build()), [3])
    self.assertEqual(texts(d.build(exprtype='Float')), ['3.0'])
    # A description inside a description: the outer context fixes the
    # types of the inner parts, so x + 1 under a Float context is Float.
    inner = curry.describe(plus, 1, 1)
    outer = curry.describe(plus, inner, 2.5)
    self.assertEqual(str(outer), '(1 + 1) + 2.5')
    self.assertEqual(outer.typeof(defaulted=True), 'Float')
    self.assertEqual(values(outer), [4.5])
    # The same description twice in one expression is one node.
    pair = curry.describe((inner, inner))
    node = curry.expr(pair)
    self.assertEqual(node[0].id(), node[1].id())
    self.assertEqual(values(node), [(2, 2)])
    self.assertEqual(repr(d), '<curry description 1 + 2>')
    # A marker inside a description is the shared node of the marker.
    x = curry.free()
    e = curry.expr(curry.describe(P.id, x))
    self.assertEqual(e[0].id(), curry.expr(x).id())
    # A description with anchors, inline and keyword, alone and inside a
    # larger expression; every typing of it starts afresh.
    anchor, ref = curry.expressions.anchor, curry.ref
    d = curry.describe(P.take, 2, anchor(curry.cons(1, ref())))
    self.assertEqual(values(d), [[1, 1]])
    self.assertEqual(values(curry.expr(d)), [[1, 1]])
    self.assertEqual(values(P.id, d), [[1, 1]])
    k = curry.describe(P.take, 3, ref('xs'), xs=curry.cons(7, ref('xs')))
    self.assertEqual(k.typeof(defaulted=True), '[Int]')
    self.assertEqual(values(P.id, k, exprtype='[Float]'), [[7.0, 7.0, 7.0]])
    self.assertEqual(values(k), [[7, 7, 7]])
    self.assertEqual(values(P.id, k), [[7, 7, 7]])
    self.assertEqual(values(curry.describe(P.id, k)), [[7, 7, 7]])
    # The keyword exprtype is the type of the description; build may
    # override it; a target is refused.
    f = curry.describe(plus, 1, 2, exprtype='Float')
    self.assertEqual(f.typeof(), 'Float')
    self.assertEqual(f.typeof(defaulted=True), 'Float')
    self.assertEqual(values(f), [3.0])
    self.assertEqual(values(P.id, f), [3.0])
    self.assertEqual(values(f.build(exprtype='Int')), [3])
    self.assertEqual(f.builder.anchor_vars, {})
    with self.assertRaisesRegex(TypeError, 'takes no target'):
      curry.describe(plus, 1, 2, target=curry.expr(0))

  def test_record(self):
    '''The result type is recorded weakly, by the identity of the node.'''
    interp = curry.getInterpreter()
    P = prelude()
    record = builder.record_of(interp)
    e = curry.expr(P.Just, 1)
    scheme, typeexpr = builder.recorded(interp, e)
    self.assertEqual(str(scheme), 'Num a => Maybe a')
    self.assertEqual(curry.typecheck.show_type(typeexpr), 'Maybe Int')
    self.assertEqual(builder.result_type(interp, e), typeexpr)
    self.assertIsNone(builder.recorded(interp, curry.raw_expr(P.Just, 1)))
    self.assertIsNone(builder.result_type(interp, 1))
    before = len(record)
    del e, scheme, typeexpr
    gc.collect()
    self.assertEqual(len(record), before - 1)
    # A value of an evaluation is a copy: no record, the walk types it.
    v = next(curry.eval(curry.expr([1.5])))
    self.assertIsNone(builder.recorded(interp, v))
    self.assertEqual(curry.typeof(v), '[Float]')

  def test_topython_exprtype(self):
    interp = curry.getInterpreter()
    nil = curry.raw_expr([])
    self.assertEqual(curry.topython(nil), [])
    self.assertEqual(curry.topython(nil, exprtype='[Char]'), '')
    self.assertEqual(curry.topython(nil, exprtype='[Int]'), [])
    self.assertEqual(curry.topython(nil, exprtype='[a]'), [])
    chars = curry.raw_expr(['a', 'b'])
    self.assertEqual(curry.topython(chars), 'ab')
    self.assertEqual(curry.topython(chars, exprtype='[Char]'), 'ab')
    self.assertEqual(curry.topython(chars, exprtype='[a]'), 'ab')
    self.assertEqual(curry.topython(chars, convert_strings=False), ['a', 'b'])
    pair = curry.raw_expr(([], [['a'], []]))
    self.assertEqual(curry.topython(pair), ([], ['a', []]))
    self.assertEqual(
        curry.topython(pair, exprtype='([Char], [[Char]])'), ('', ['a', ''])
      )
    from curry.toolchain.flat2icurry import flatcurry as fc
    typeexpr = fc.TCons(fc.prelude('[]'), [fc.TCons(fc.prelude('Char'), [])])
    self.assertEqual(curry.topython(nil, exprtype=typeexpr), '')
    with self.assertRaises(curry.CurryTypeError):
      curry.topython(nil, exprtype='Foo')
    # Without a type, a list is a string when its elements are characters,
    # not when they convert to str: a list of strings stays a list.
    P = prelude()
    strs = curry.raw_expr([['a', 'b'], ['c']])
    self.assertEqual(curry.topython(strs), ['ab', 'c'])
    self.assertEqual(values(P.map, P.fst, iter([('ab', 1), ('cd', 2)])), [['ab', 'cd']])
    self.assertEqual(values(P.map, P.fst, [('ab', 1), ('cd', 2)]), [['ab', 'cd']])

  def test_eval_static_type(self):
    '''eval converts by the type of the goal it built; a converter of the user is left alone.'''
    P = prelude()
    self.assertEqual(list(curry.eval(curry.expr(''), converter='topython')), [''])
    self.assertEqual(list(curry.eval(P.reverse, '', converter='topython')), [''])
    self.assertEqual(list(curry.eval(P.reverse, '', converter=None))[0].info.name, '[]')
    seen = []
    def converter(interp, value):
      seen.append(str(value))
      return value
    list(curry.eval(P.reverse, 'ab', converter=converter))
    self.assertEqual(seen, ['"ba"'])
    # A goal of compile(mode='expr') carries no record; the rule applies.
    goal = curry.compile('reverse "ab"', mode='expr', exprtype='String')
    self.assertEqual(list(curry.eval(goal, converter='topython')), ['ba'])
    # An IO goal yields its payload, so the type handed to the converter is
    # the type under IO.
    ret = getattr(P, 'return')
    self.assertEqual(values(ret, curry.typed('', 'String')), [''])
    self.assertEqual(values(ret, 'ab'), ['ab'])
    self.assertEqual(values(ret, []), [[]])
    # The keyword arguments of eval are anchors, as in expr.
    self.assertEqual(
        values(P.take, 2, curry.ref('xs'), xs=curry.cons(1, curry.ref('xs'))), [[1, 1]]
      )

  def test_flag_off(self):
    '''With typed_expr off, curry.expr is the untyped builder.'''
    P = prelude()
    flags = curry.getInterpreter().flags
    self.assertTrue(flags['typed_expr'])
    flags['typed_expr'] = False
    try:
      e = curry.expr(getattr(P, 'not'), 1)
      self.assertEqual(str(e), 'not 1')
      self.assertEqual(str(curry.expr(curry.typed(5, 'Float'))), '5')
      self.assertEqual(str(curry.expr(1, exprtype='Float')), '1')
      self.assertEqual(str(curry.expr(curry.free())), 'unknown _inst#Prelude.Data#Prelude.Bool')
      self.assertIsNone(builder.result_type(curry.getInterpreter(), e))
      # typeof walks the ill-typed node and reports it.
      with self.assertRaisesRegex(curry.CurryTypeError, 'type mismatch in the expression'):
        curry.typeof(e)
      self.assertEqual(curry.typeof(curry.expr(getattr(P, 'not'), True)), 'Bool')
    finally:
      flags['typed_expr'] = True

  @cytest.with_flags(typed_expr=False)
  def test_flag_from_environment(self):
    P = curry.import_('Prelude')
    self.assertFalse(curry.flags['typed_expr'])
    self.assertEqual(str(curry.expr(getattr(P, 'not'), 1)), 'not 1')

  def test_raw_expr_unchanged(self):
    P = prelude()
    self.assertEqual(str(curry.raw_expr(curry.typed(5, 'Float'))), '5')
    self.assertEqual(str(curry.raw_expr(curry.free(exprtype='Int'))), '_a')
    self.assertEqual(str(curry.raw_expr(getattr(P, 'not'), 1)), 'not 1')
    self.assertEqual(str(curry.raw_expr('ab')), '"ab"')

class TestCatalogue(cytest.TestCase):
  '''Every line of the error catalogue of the design, through curry.expr.'''

  def check(self, pattern, *args, **kwds):
    with self.assertRaisesRegex(curry.CurryTypeError, pattern) as cm:
      curry.expr(*args, **kwds)
    return cm.exception

  def test_mismatch_between_arguments(self):
    plus = symbol('+')
    err = self.check(
        r'^type mismatch in argument 2 of Prelude\.\+ :: Num a => a -> a -> a\n'
        r'  argument 1 fixed a := Int \(from 1\)\n'
        r"  argument 2 has type Char \(from 'a'\)$"
      , plus, 1, 'a'
      )
    self.assertIsInstance(err, errors.MismatchError)
    self.assertEqual(err.symbol, 'Prelude.+')

  def test_value_under_a_wrong_type(self):
    P = prelude()
    plusInt = symbol('plusInt')
    self.check(r'^cannot convert 2\.5 to Int at argument 2 of Prelude\.plusInt :: Int -> Int -> Int$', plusInt, 1, 2.5)
    self.check(r"^cannot convert 'a' to Int at argument 1 of Prelude\.plusInt :: Int -> Int -> Int$", plusInt, 'a', 1)
    self.check(r'^cannot convert 1 to Bool at argument 1 of Prelude\.not :: Bool -> Bool$', getattr(P, 'not'), 1)

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
        r'^cannot handle the overloaded expression \'read "5"\' of type Read a => a\n'
        r'  ' + re.escape(ORACLE_SENTENCE) + r'\n'
        r'  add a type annotation \(exprtype\)$'
      , P.read, '5'
      )
    self.assertIsInstance(err, DefaultingError)
    self.check(r"^cannot handle the overloaded expression 'toEnum 65' of type Enum a => a\n", P.toEnum, 65)

  def test_no_instance(self):
    P = prelude()
    err = self.check(
        r'^no instance for Show \(a -> a\) in argument 1 of Prelude\.show :: Show a => a -> \[Char\]$'
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
      , P.map, curry.free(), [1, 2]
      )
    self.assertIsInstance(err, errors.FreeFunctionError)

  def test_none(self):
    P = prelude()
    DM = curry.import_('Data.Maybe')
    self.check(r'^cannot convert None at argument 1 of Prelude\.Just :: a -> Maybe a; expected a$', P.Just, None)
    self.check(
        r'^cannot convert None at argument 1 of Data\.Maybe\.fromJust :: Maybe a -> a; expected Maybe a\n'
        r'  Prelude\.Nothing is the empty value of Maybe$'
      , DM.fromJust, None
      )
    self.check(r'^cannot convert None at the expression; expected a Curry value$', None)

  def test_one_tuple(self):
    self.check(r'^Curry has no 1-tuple', (1,))

  def test_too_many_arguments(self):
    P = prelude()
    err = self.check(r'^Prelude\.Just :: a -> Maybe a takes 1 argument, 2 given$', P.Just, 1, 2)
    self.assertIsInstance(err, errors.ArityError)
    self.check(r'^Prelude\.not :: Bool -> Bool takes 1 argument, 3 given$', getattr(P, 'not'), True, 1, 2)

  def test_exprtype_errors(self):
    err = self.check(
        r"^cannot parse exprtype 'Int ->': expected a type, found end of text at column 7$"
      , 1, exprtype='Int ->'
      )
    self.assertIsInstance(err, errors.ExprTypeSyntaxError)
    err = self.check(
        r'^unknown type constructor Foo; searched the interfaces of Prelude(, [A-Za-z.]+)*; '
        r'curry\.compile\(\.\.\., exprtype=\.\.\.\) accepts any Curry type$'
      , 1, exprtype='Foo'
      )
    self.assertIsInstance(err, errors.UnknownTypeConstructorError)
    P = prelude()
    err = self.check(r'^exprtype Int does not match the inferred type Maybe a$', P.Just, 1, exprtype='Int')
    self.assertIsInstance(err, errors.ExprTypeMismatchError)
    self.check(r'^exprtype \[Int\] does not match the inferred type \[Char\]$', P.show, 1, exprtype='[Int]')
    self.check(r"^cannot convert 'a' to Int at the expression$", 'a', exprtype='Int')
    err = self.check(
        r"^exprtype takes a type without a context; the context is inferred \(exprtype 'Num a => a'\)$"
      , 1, exprtype='Num a => a'
      )
    self.assertIsInstance(err, errors.ContextInExprTypeError)
    self.check(r'^Maybe takes 1 type argument, 2 given in exprtype', 1, exprtype='Maybe Int Int')
    self.check(r'^exprtype a does not match the inferred type \[b\]', [1], exprtype='a')

  def test_iterator_item(self):
    DL = curry.import_('Data.List')
    with self.assertRaisesRegex(
        curry.EvaluationError
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
      curry.expr(bad)
    message = str(cm.exception)
    self.assertLess(len(message), 600)
    self.assertEqual(engine.LOCATION_DEPTH, 8)
    self.assertRegex(
        message
      , r'^type mismatch in element 2 of the list in (element 1 of the list in ){7}'
        r'\.\.\. in the expression\n'
      )
    self.assertIn("  element 1 of the list fixed the type Int (from 1)", message)
    self.assertIn("  element 2 of the list has type Char (from 'a')", message)

  def test_value_above_the_cap(self):
    P = prelude()
    big = biglist(100001)
    err = self.check(
        r"^the value at argument 2 of Prelude\.take :: Int -> \[a\] -> \[a\] has more than "
        r"100000 nodes; pass curry\.typed\(node, 'T'\)$"
      , P.take, 1, big
      )
    self.assertIsInstance(err, errors.ValueTooLargeError)

def plus_one(e):
  return curry.expr(symbol('+'), e, 1)
