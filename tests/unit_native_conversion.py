'''Parity between the binding conversion and the Python reference path.'''
import cytest # from ./lib; must be first
import curry
import math
from unittest import mock
from curry.interpreter import conversions, eval as evaluation
from curry import expressions
from curry.typecheck import goals


class TestNativeConversion(cytest.TestCase):
  def parity(self, term, ground=False):
    interp = cytest.raw.interp()
    node = cytest.raw.values(term).one()
    typeexpr = expressions.result_type(interp, goals.make_goal(interp, (term,)).expr)
    native = conversions.ToPython(interp=interp)
    python = conversions.ToPython(interp=interp, native=False)
    for strings in (False, True):
      if ground:
        with mock.patch.object(native, '_python', side_effect=AssertionError('fallback')):
          actual = native(node, strings, typeexpr)
      else:
        actual = native(node, strings, typeexpr)
      expected = python(node, strings, typeexpr)
      self.same(actual, expected)

  def same(self, actual, expected):
    self.assertIs(type(actual), type(expected))
    self.assertEqual(repr(actual), repr(expected))
    if isinstance(expected, float) and math.isnan(expected):
      self.assertTrue(math.isnan(actual))
    elif isinstance(expected, (list, tuple)):
      self.assertEqual(len(actual), len(expected))
      for a, b in zip(actual, expected):
        self.same(a, b)
    else:
      self.assertEqual(actual, expected)

  def test_ground_corpus(self):
    values = [0, -1, 2**63 - 1, 2**64, -(2**200),
        0.0, -0.0, 1e308, float('inf'), float('nan'),
        curry.Char('\u03bb'), curry.Char('\U0001f642'), '', 'a\n"b\'c',
        [], [1, 2, -3], [[1], [], [2, 3]], ['', 'hello'], (), True, False]
    values += [tuple(range(n)) for n in range(2, 8)]
    values += [(1, '', ['a', 'b']), [curry.Char('a'), curry.Char('b')]]
    for value in values:
      with self.subTest(value=repr(value)):
        self.parity(curry.term(value), ground=True)

  def test_data_and_function_fallback(self):
    P = curry.import_('Prelude')
    M = curry.compile('data Item = Item Int String\nf :: Int -> Int\nf x = x')
    for term in (P.Just(1), M.Item(2, 'text'), curry.term([M.Item(3, '')]),
                 M.f, P.Just(curry.Char('\U0001f642'))):
      with self.subTest(term=str(term)):
        self.parity(term)

  def test_results_and_bindings_use_native_path(self):
    from curry.backends.cxx import curryrtbindings as rt
    original = rt.convert_value
    with mock.patch.object(rt, 'convert_value', wraps=original) as convert:
      self.assertEqual(curry.eval(curry.term([1, 2])).one(), [1, 2])
      x = curry.free('x', type='Int')
      self.assertEqual(curry.solve(curry.import_('Prelude').id(x)).one().value, x)
      self.assertGreaterEqual(convert.call_count, 2)

  def test_partial_list_and_free_variable(self):
    interp = cytest.raw.interp()
    from curry.interpreter.eval import _Variables
    term = curry.parse('(1:xs :: [Int]) where xs free')
    node = cytest.raw.values(term).one()
    converter = conversions.ToPython(interp=interp, variable=_Variables(interp, ()))
    reference = conversions.ToPython(interp=interp, variable=converter.variable, native=False)
    self.same(converter(node), reference(node))

  def test_symbol_cache_lifecycle(self):
    interp = cytest.raw.interp()
    first = conversions.ToPython(interp=interp).expression_symbols
    self.assertIs(conversions.ToPython(interp=interp).expression_symbols, first)
    curry.parse('1 :: Int')
    second = conversions.ToPython(interp=interp).expression_symbols
    self.assertIsNot(first, second)
    self.assertTrue(second)
    self.assertIs(conversions.ToPython(interp=interp).expression_symbols, second)
    module = curry.compile('data Item = Item')
    third = conversions.ToPython(interp=interp).expression_symbols
    self.assertIsNot(second, third)
    curry.reload(module, text='data Item = Other')
    self.assertIsNot(third, conversions.ToPython(interp=interp).expression_symbols)
    curry.reset()
    self.assertEqual(conversions.ToPython(interp=interp).expression_symbols, {})

  def test_untyped_string_rule(self):
    for description, expected in [('ab', 'ab'), ([], []), (['a', 'b'], ['a', 'b'])]:
      node = cytest.raw.values(curry.term(description)).one()
      for native in (False, True):
        convert = conversions.ToPython(native=native)
        self.same(convert(node), expected)

  def test_unchecked_char_code_points(self):
    P = curry.import_('Prelude')
    for cp in (0xd800, 0x10ffff, 0x110000, 0xffffffff):
      node = cytest.raw.values(cytest.raw.expr(P['prim_chr'], cp, typed=True)).one()
      for value in (node, cytest.raw.expr([node])):
        for strings in (False, True):
          self.same(conversions.ToPython()(value, strings),
              conversions.ToPython(native=False)(value, strings))

  def test_nonvalues_are_left_to_python(self):
    P = curry.import_('Prelude')
    for description in (cytest.raw.free(), cytest.raw.fail,
                        cytest.raw.choice(1, 2), [P.id, 1],
                        [1, cytest.raw.fail], (1, cytest.raw.choice(2, 3))):
      node = cytest.raw.expr(description)
      actual = conversions.ToPython()(node)
      expected = conversions.ToPython(native=False)(node)
      self.same(actual, expected)

  def test_deep_native_containers(self):
    node = cytest.raw.expr(1)
    for _ in range(1500):
      node = cytest.raw.expr((node, 0))
    convert = conversions.ToPython()
    with mock.patch.object(convert, '_python', side_effect=AssertionError('fallback')):
      value = convert(node)
    for _ in range(1500):
      self.assertIs(type(value), tuple)
      value, zero = value
      self.assertEqual(zero, 0)
    self.assertEqual(value, 1)


if __name__ == '__main__':
  import unittest
  unittest.main()
