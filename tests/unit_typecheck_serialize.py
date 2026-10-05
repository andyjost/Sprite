'''
The serializer of the typed boundary, item Y8 (#57, epic #48).

``curry.typecheck.serialize`` prints the description of a Python-built
expression as Curry text: Python values as Curry literals, operands without
text (Curry nodes, iterators) as parameters, free markers as ``let x1 free
in`` or as parameters, anchors as a recursive ``let``.  The text is the
input of the oracles of func_typed_expr.py: the front end for the types and
the PAKCS REPL for the values.  These tests pin the text of every kind of
spec without a front end; they run on both backends.
'''
import cytest # from ./lib; must be first
from curry.toolchain.flat2icurry import flatcurry as fc
from curry.typecheck import builder, engine, serialize
from curry.typecheck.serialize import (
    SerializeError, Serialized, curry_literal, float_text, is_identifier
  , serialize_call, serialize_description
  )
import curry, itertools, math, unittest

def prelude():
  return curry.import_('Prelude')

def symbol(name):
  return curry.symbol('Prelude.' + name)

def text(*args, **kwds):
  '''The Curry text of the arguments of curry.expr.'''
  return str(ser(*args, **kwds))

def ser(*args, **kwds):
  exprtype = kwds.pop('exprtype', None)
  module = kwds.pop('module', None)
  typed = kwds.pop('typed', True)
  return serialize_call(
      curry.getInterpreter(), args, kwds, exprtype=exprtype, module=module
    , typed=typed
    )

class TestLiterals(cytest.TestCase):
  '''Python values as Curry literals.'''

  def test_integers(self):
    self.assertEqual(curry_literal(0), '0')
    self.assertEqual(curry_literal(5), '5')
    self.assertEqual(curry_literal(-5), '(-5)')
    self.assertEqual(curry_literal(12345678901234567890), '12345678901234567890')
    self.assertEqual(text(-1), '(-1)')
    self.assertEqual(text(prelude().negate, -1), 'negate (-1)')

  def test_floats(self):
    self.assertEqual(float_text(2.5), '2.5')
    self.assertEqual(float_text(100.0), '100.0')
    self.assertEqual(float_text(-2.5), '(-2.5)')
    self.assertEqual(float_text(1e20), '1.0e20')
    self.assertEqual(float_text(1e-5), '1.0e-05')
    self.assertEqual(float_text(1.5e300), '1.5e300')
    self.assertEqual(float_text(-1e20), '(-1.0e20)')
    self.assertEqual(curry_literal(0.1), '0.1')
    for bad in (math.nan, math.inf, -math.inf):
      with self.assertRaisesRegex(SerializeError, 'has no Curry literal'):
        float_text(bad)
    self.assertEqual(text(2.5), '2.5')
    self.assertEqual(text([1, 2.5]), '[1, 2.5]')

  def test_bools(self):
    self.assertEqual(curry_literal(True), 'True')
    self.assertEqual(curry_literal(False), 'False')
    self.assertEqual(text(getattr(prelude(), 'not'), True), 'not True')

  def test_chars_and_strings(self):
    self.assertEqual(curry_literal('a'), "'a'")
    self.assertEqual(curry_literal('\n'), r"'\n'")
    self.assertEqual(curry_literal("'"), r"'\''")
    self.assertEqual(curry_literal('ä'), r"'\228'")
    self.assertEqual(curry_literal('a', as_char=False), '"a"')
    self.assertEqual(curry_literal('ab', as_char=True), '"ab"')
    self.assertEqual(curry_literal(''), '""')
    self.assertEqual(curry_literal('ab\n"q" \\ ä\U0001f600'), r'"ab\n\"q\" \\ \228\128512"')
    self.assertEqual(curry_literal(b'bytes'), '"bytes"')
    self.assertEqual(curry_literal(b'a'), "'a'")

  def test_no_literal(self):
    with self.assertRaisesRegex(SerializeError, 'None has no Curry literal'):
      curry_literal(None)
    with self.assertRaisesRegex(SerializeError, 'has no Curry literal'):
      curry_literal(object())
    with self.assertRaisesRegex(SerializeError, 'None has no Curry text'):
      text(prelude().Just, None)
    self.assertIsInstance(SerializeError('x'), ValueError)

  def test_identifiers(self):
    for name in ('x', 'xs', "x'", 'a1', 'camelCase'):
      self.assertTrue(is_identifier(name), name)
    for name in ('', 'X', '_1', '_', 'let', 'free', 'where', '1a', 'a-b'):
      self.assertFalse(is_identifier(name), name)

class TestApplications(cytest.TestCase):
  '''Symbols applied to arguments.'''

  def test_prefix_and_infix(self):
    P = prelude()
    plus = symbol('+')
    self.assertEqual(text(plus, 1, 2), '1 + 2')
    self.assertEqual(text(plus, [plus, 1, 2], 3), '(1 + 2) + 3')
    self.assertEqual(text(plus, 1, [plus, 2, 3]), '1 + (2 + 3)')
    self.assertEqual(text(P.show, [plus, 1, 2]), 'show (1 + 2)')
    self.assertEqual(text(P.fmap, [plus, 1], [P.Just, 1]), 'fmap ((+) 1) (Just 1)')
    self.assertEqual(text(plus), '(+)')
    self.assertEqual(text(plus, 1), '(+) 1')
    self.assertEqual(text(P.foldr, plus, 0, [1, 2]), 'foldr (+) 0 [1, 2]')
    self.assertEqual(text(getattr(P, 'not')), 'not')
    self.assertEqual(text(P.id, P.id, 5), 'id id 5')
    self.assertEqual(text(P.map, getattr(P, 'not')), 'map not')
    self.assertEqual(text(P.apply, [plus, 1], 6), 'apply ((+) 1) 6')
    self.assertEqual(text(P.id, [P.Just, [P.Just, 1]]), 'id (Just (Just 1))')

  def test_special_constructors(self):
    P = prelude()
    pair = getattr(P, '(,)')
    self.assertEqual(text(pair, 1, 2), '(1, 2)')
    self.assertEqual(text(pair, 1), '(,) 1')
    self.assertEqual(text(pair), '(,)')
    self.assertEqual(text(getattr(P, '(,,)'), 1, 2, 3), '(1, 2, 3)')
    self.assertEqual(text(P.Nil), '[]')
    self.assertEqual(text(curry.nil), '[]')
    self.assertEqual(text(getattr(P, '()')), '()')
    self.assertEqual(text(P.Cons, 1, [P.Cons, 2, P.Nil]), '1 : (2 : [])')
    self.assertEqual(text(curry.cons(1, 2, curry.nil)), '1 : (2 : [])')
    self.assertEqual(text(P.Cons, 1), '(:) 1')
    self.assertEqual(text(P.length, [P.Cons, 1, P.Nil]), 'length (1 : [])')
    self.assertEqual(text(curry.choice(1, 2)), '1 ? 2')
    self.assertEqual(text(getattr(P, 'not'), curry.choice(True, False)), 'not (True ? False)')
    self.assertEqual(text(P.Just, curry.choice(1, 2)), 'Just (1 ? 2)')

  def test_qualification(self):
    DL = curry.import_('Data.List')
    ID = curry.import_('Data.Functor.Identity')
    s = ser(DL.sum, [1, 2, 3])
    self.assertEqual(s.text, 'Data.List.sum [1, 2, 3]')
    self.assertEqual(s.modules, ['Data.List'])
    self.assertEqual(text(DL.sum, [1, 2, 3], module='Data.List'), 'sum [1, 2, 3]')
    s = ser(ID.runIdentity, [ID.Identity, 5])
    self.assertEqual(
        s.text
      , 'Data.Functor.Identity.runIdentity (Data.Functor.Identity.Identity 5)'
      )
    self.assertEqual(s.modules, ['Data.Functor.Identity'])
    s = ser(DL.sum, [[ID.runIdentity, [ID.Identity, 5]]])
    self.assertEqual(s.modules, ['Data.Functor.Identity', 'Data.List'])
    # The names of the Prelude never qualify.
    self.assertEqual(ser(prelude().show, 1).modules, [])

  def test_explicit_dictionaries(self):
    '''Dictionaries passed before the value arguments have no Curry text.'''
    P = prelude()
    plus = symbol('+')
    num_int = symbol('_inst#Prelude.Num#Prelude.Int')
    self.assertEqual(text(P.apply, [P.apply, [plus, num_int], 1], 2), 'apply (apply (+) 1) 2')
    self.assertEqual(text(P.show, symbol('_inst#Prelude.Show#Prelude.Int'), 1), 'show 1')
    # A dictionary on its own is an operand without text.
    self.assertEqual(text(P.id, num_int), 'id p1')

class TestValues(cytest.TestCase):
  '''Lists, tuples, strings by their type, annotations and the untyped parts.'''

  def test_lists_and_tuples(self):
    P = prelude()
    self.assertEqual(text([1, 2.5]), '[1, 2.5]')
    self.assertEqual(text([[1, 2], [3]]), '[[1, 2], [3]]')
    self.assertEqual(text([]), '[]')
    self.assertEqual(text((1, 'a', True)), "(1, 'a', True)")
    self.assertEqual(text(()), '()')
    self.assertEqual(text(([1, 2], ('a', 2.5), True)), "([1, 2], ('a', 2.5), True)")
    self.assertEqual(text(P.fst, (1, 'a')), "fst (1, 'a')")
    self.assertEqual(text(P.length, list(range(5))), 'length [0, 1, 2, 3, 4]')
    with self.assertRaisesRegex(SerializeError, 'Curry has no 1-tuple'):
      text((1,))

  def test_strings_by_type(self):
    '''A one-character string prints as a Char or a String by its type.'''
    P = prelude()
    self.assertEqual(text('a'), "'a'")
    self.assertEqual(text('ab'), '"ab"')
    self.assertEqual(text(''), '""')
    self.assertEqual(text(b'bytes'), '"bytes"')
    self.assertEqual(text(P.ord, 'a'), "ord 'a'")
    self.assertEqual(text(P.id, 'a'), "id 'a'")
    self.assertEqual(text(P.length, 'a'), 'length "a"')
    self.assertEqual(text(P.length, 'hello'), 'length "hello"')
    self.assertEqual(text(P.reverse, 'ab'), 'reverse "ab"')
    self.assertEqual(text(P.unwords, ['a', 'bc']), 'unwords ["a", "bc"]')
    self.assertEqual(text(curry.typed('a', 'String')), '("a" :: String)')
    self.assertEqual(text('ab\n"q" \\ ä'), r'"ab\n\"q\" \\ \228"')
    # Without the typing the length decides, as the messages print it.
    self.assertEqual(text(P.length, 'a', typed=False), "length 'a'")
    # A tree the engine rejects prints by the Python types.
    self.assertEqual(text(getattr(P, 'not'), 1), 'not 1')
    self.assertEqual(text(P.length, [1, 'a']), "length [1, 'a']")
    self.assertEqual(text(symbol('plusInt'), 1, 2.5), 'plusInt 1 2.5')

  def test_annotations(self):
    P = prelude()
    self.assertEqual(text(P.Just, 5, exprtype='Maybe Float'), '(Just 5 :: Maybe Float)')
    self.assertEqual(text(P.read, '5', exprtype='Int'), '(read "5" :: Int)')
    self.assertEqual(text(1, exprtype='Float'), '(1 :: Float)')
    self.assertEqual(text(symbol('+'), 1, 2, exprtype='Float'), '(1 + 2 :: Float)')
    self.assertEqual(text(P.id, curry.typed(5, 'Float')), 'id (5 :: Float)')
    self.assertEqual(text(curry.typed([], '[Int]')), '([] :: [Int])')
    self.assertEqual(text(curry.free(exprtype='[Int]')), 'let x1 free in (x1 :: [Int])')
    # A type given as a FlatCurry type prints through the printer.
    typeexpr = fc.TCons(fc.prelude('[]'), [fc.TCons(fc.prelude('Char'), [])])
    s = ser(curry.typed([], '[Char]'), exprtype=typeexpr)
    self.assertEqual(s.text, '(([] :: [Char]) :: [Char])')
    self.assertIs(s.exprtype, typeexpr)
    spec = engine.Typed(engine.Lit(1), typeexpr)
    self.assertEqual(serialize.serialize(spec).text, '(1 :: [Char])')

  def test_untyped_parts(self):
    P = prelude()
    self.assertEqual(text([P.Int, curry.unboxed(3)]), '(3 :: Int)')
    self.assertEqual(text([P.Char, curry.unboxed('a')]), "('a' :: Char)")
    self.assertEqual(text([P.Float, curry.unboxed(2.5)]), '(2.5 :: Float)')
    self.assertEqual(text(P.Just, [P.Int, curry.unboxed(3)]), 'Just (3 :: Int)')
    self.assertEqual(text(curry.unboxed(3)), '3')
    self.assertEqual(text(curry.unboxed(2.5)), '2.5')
    self.assertEqual(text(P.id, curry.fail), 'id failed')
    self.assertEqual(text(curry.expressions.fwd(1)), '1')
    self.assertEqual(text(P.id, curry.expressions.fwd([P.Just, 1])), 'id (Just 1)')
    with self.assertRaisesRegex(SerializeError, 'a setgrd node has no Curry text'):
      text(curry.expressions._setgrd(0, 1))
    with self.assertRaisesRegex(SerializeError, 'a strict node has no Curry text'):
      text(curry.expressions._strictconstr(True, (1, 2)))

class TestParameters(cytest.TestCase):
  '''Operands without text become parameters.'''

  def test_nodes_and_iterators(self):
    P = prelude()
    DL = curry.import_('Data.List')
    v = next(curry.eval(curry.expr([1.5, 2.5])))
    s = ser(DL.sum, v)
    self.assertEqual(s.text, 'Data.List.sum p1')
    self.assertEqual(s.params, ['p1'])
    self.assertEqual(s.parameters(), ['p1'])
    self.assertEqual(s.definition(), 'compiled_expression p1 = Data.List.sum p1')
    self.assertEqual(s.definition('goal'), 'goal p1 = Data.List.sum p1')
    with self.assertRaisesRegex(SerializeError, 'operands without Curry text: p1'):
      s.where_text()
    s = ser(P.length, iter([1, 2]))
    self.assertEqual(s.text, 'length p1')
    s = ser(symbol('+'), curry.expr(1), curry.expr(2))
    self.assertEqual(s.text, 'p1 + p2')
    self.assertEqual(s.params, ['p1', 'p2'])
    # The same node twice is one parameter; a raw node is one too.
    n = curry.expr(1)
    self.assertEqual(ser(symbol('+'), n, n).text, 'p1 + p1')
    self.assertEqual(ser(P.id, curry.raw_expr(P.Just, 1)).text, 'id p1')
    # A node alone prints as a parameter too.
    self.assertEqual(ser(n).definition(), 'compiled_expression p1 = p1')
    # The engine's Known spec is an operand without text.
    spec = engine.App(P.length, engine.Known('[Int]', curry.raw_expr([1])))
    self.assertEqual(serialize.serialize(spec).text, 'length p1')
    self.assertEqual(serialize.serialize(engine.Iter(iter([]))).params, ['p1'])

  def test_free_markers(self):
    P = prelude()
    eq = symbol('=:=')
    x, y = curry.free(), curry.free()
    s = ser(P.id, x)
    self.assertEqual(s.text, 'let x1 free in id x1')
    self.assertEqual(s.frees, ['x1'])
    self.assertEqual(s.params, [])
    self.assertEqual(s.body, 'id x1')
    self.assertEqual(s.expression(), 'let x1 free in id x1')
    self.assertEqual(s.expression(lift_frees=True), 'id x1')
    self.assertEqual(s.definition(), 'compiled_expression x1 = id x1')
    self.assertEqual(s.definition(lift_frees=False), 'compiled_expression = let x1 free in id x1')
    self.assertEqual(s.where_text(), 'id x1 where x1 free')
    s = ser(eq, x, y)
    self.assertEqual(s.text, 'let x1, x2 free in x1 =:= x2')
    self.assertEqual(s.where_text(), 'x1 =:= x2 where x1, x2 free')
    # One marker is one name, however often it occurs.
    self.assertEqual(ser(eq, x, x).text, 'let x1 free in x1 =:= x1')
    self.assertEqual(ser(([eq, x, y], x)).text, 'let x1, x2 free in (x1 =:= x2, x1)')
    # The names follow the order of the first occurrence.
    self.assertEqual(ser(eq, y, x).frees, ['x1', 'x2'])
    self.assertEqual(
        ser(getattr(P, '&>'), [eq, [getattr(P, '++'), x, [3]], [1, 2, 3]], x).text
      , 'let x1 free in ((x1 ++ [3]) =:= [1, 2, 3]) &> x1'
      )
    # A marker and a parameter.
    s = ser(eq, x, curry.expr(1))
    self.assertEqual(s.definition(), 'compiled_expression p1 x1 = x1 =:= p1')
    self.assertEqual(s.parameters(lift_frees=False), ['p1'])

  def test_anchors(self):
    P = prelude()
    anchor, ref = curry.expressions.anchor, curry.ref
    s = ser(P.take, 2, anchor(curry.cons(1, ref())))
    self.assertEqual(s.text, 'let a1 = 1 : a1 in take 2 a1')
    self.assertEqual(s.bindings, [('a1', '1 : a1')])
    self.assertEqual(s.body, 'take 2 a1')
    # A keyword anchor keeps its name.
    s = ser(P.take, 3, ref('xs'), xs=curry.cons(7, ref('xs')))
    self.assertEqual(s.text, 'let xs = 7 : xs in take 3 xs')
    self.assertEqual(s.definition(), 'compiled_expression = let xs = 7 : xs in take 3 xs')
    # A keyword anchor may refer to an earlier one.
    s = ser(P.take, 3, ref('b'), a=curry.cons(1, curry.nil), b=curry.cons(2, ref('a')))
    self.assertEqual(s.text, 'let a = 1 : []; b = 2 : a in take 3 b')
    # A name that is a keyword, that starts with an underscore, or that
    # names a symbol of the expression is replaced.
    s = ser(P.take, 2, anchor(curry.cons(1, ref('free')), name='free'))
    self.assertEqual(s.text, 'let a1 = 1 : a1 in take 2 a1')
    s = ser(P.take, 2, anchor(curry.cons(1, ref('_7')), name='_7'))
    self.assertEqual(s.text, 'let a1 = 1 : a1 in take 2 a1')
    s = ser(P.take, 2, anchor(curry.cons(1, ref('take')), name='take'))
    self.assertEqual(s.text, 'let a1 = 1 : a1 in take 2 a1')
    # The free markers come before the anchors; an anchor may hold one.
    x = curry.free()
    s = ser(P.take, 2, anchor(curry.cons(x, ref())))
    self.assertEqual(s.text, 'let x1 free in let a1 = x1 : a1 in take 2 a1')
    self.assertEqual(s.where_text(), 'let a1 = x1 : a1 in take 2 a1 where x1 free')
    self.assertEqual(s.definition(), 'compiled_expression x1 = let a1 = x1 : a1 in take 2 a1')
    # The trivial cycle and an anchor inside an anchor.
    self.assertEqual(ser(anchor(ref())).text, 'let a1 = a1 in a1')
    s = ser(P.take, 3, anchor(curry.cons(1, anchor(curry.cons(2, ref('o')), name='i')), name='o'))
    self.assertEqual(s.text, 'let o = 1 : i; i = 2 : o in take 3 o')

class TestEntryPoints(cytest.TestCase):
  '''serialize, serialize_call, serialize_description and Serialized.'''

  def test_descriptions(self):
    P = prelude()
    plus = symbol('+')
    d = curry.describe(plus, 1, 2)
    self.assertEqual(serialize_description(d).text, '1 + 2')
    self.assertEqual(serialize.serialize(d).text, '1 + 2')
    inner = curry.describe(plus, 1, 1)
    outer = curry.describe(plus, inner, 2.5)
    self.assertEqual(serialize_description(outer).text, '(1 + 1) + 2.5')
    self.assertEqual(text(outer), '(1 + 1) + 2.5')
    self.assertEqual(text(P.show, d), 'show (1 + 2)')
    d = curry.describe(P.take, 3, curry.ref('xs'), xs=curry.cons(7, curry.ref('xs')))
    self.assertEqual(serialize_description(d).text, 'let xs = 7 : xs in take 3 xs')
    # The annotation sits on the body, inside the declarations.
    self.assertEqual(serialize_description(d, exprtype='[Int]').text, 'let xs = 7 : xs in (take 3 xs :: [Int])')
    # A one-character string in a description follows its type.
    self.assertEqual(serialize_description(curry.describe(P.length, 'a')).text, 'length "a"')
    self.assertEqual(serialize_description(curry.describe(P.length, 'a'), typed=False).text, "length 'a'")

  def test_specs(self):
    '''The engine's specs serialize as they are.'''
    P = prelude()
    spec = engine.spec_of(P.show, [symbol('+'), 1, 2])
    self.assertEqual(serialize.serialize(spec).text, 'show (1 + 2)')
    spec = engine.spec_of(getattr(P, '?'), 1, [getattr(P, '?'), 2, 3])
    self.assertEqual(serialize.serialize(spec).text, '1 ? (2 ? 3)')
    spec = engine.App('Prelude.?', 1, 2)
    self.assertEqual(serialize.serialize(spec).text, '1 ? 2')
    spec = engine.App(symbol('+').scheme, 1, 2)
    self.assertEqual(serialize.serialize(spec).text, '1 + 2')
    with self.assertRaises(TypeError):
      serialize.serialize(5)

  def test_serialized(self):
    s = Serialized('f p1', ['p1'], ['x1'], [('a1', 'x1 : a1')], None, ['Data.List', 'Data.Char'])
    self.assertEqual(s.text, 'let x1 free in let a1 = x1 : a1 in f p1')
    self.assertEqual(str(s), s.text)
    self.assertEqual(repr(s), '<Serialized %s>' % s.text)
    self.assertEqual(s.modules, ['Data.Char', 'Data.List'])
    self.assertEqual(s.parameters(), ['p1', 'x1'])
    self.assertEqual(s.definition('g'), 'g p1 x1 = let a1 = x1 : a1 in f p1')
    self.assertEqual(s.definition('g', lift_frees=False), 'g p1 = let x1 free in let a1 = x1 : a1 in f p1')
    self.assertEqual(Serialized('1', [], [], [], None, []).where_text(), '1')

  def test_large_descriptions(self):
    '''A deep tree and a long list serialize without recursion.'''
    plus = symbol('+')
    e = 1
    for _ in range(10000):
      e = [plus, e, 1]
    s = ser(e)
    self.assertTrue(s.text.startswith('(' * 9999 + '1 + 1) + 1) + 1)'))
    self.assertTrue(s.text.endswith('+ 1) + 1'))
    self.assertEqual(s.text.count('+'), 10000)
    s = ser(list(range(10000)))
    self.assertEqual(s.text, '[%s]' % ', '.join(str(i) for i in range(10000)))
    nested = 1
    for _ in range(500):
      nested = [nested]
    self.assertEqual(ser(nested).text, '[' * 500 + '1' + ']' * 500)
