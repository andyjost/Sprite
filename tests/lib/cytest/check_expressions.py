'''Defines decorator check_expressions.'''
import curry

def check_expressions(converter=curry.topython, postprocessor=sorted):
  '''
  A decorator for unit tests that check Curry expressions.

  The wrapped function should generate a sequence of tuples describing a Curry
  expression and its expected properties.  This function will build each
  expression and check the given properties.

  The first tuple element is passed to curry.expr to build an expression,
  ``e``.  Up to four additional elements are accepted, and for each that is
  not None, the corresponding property is checked:

      - The expected str(e).
      - The expected repr(e).
      - The expected result of curry.topython(e).
      - The expected result of curry.eval(e) after applying postprocessing and
        ``curry.topython``.

  Parameters:
  -----------
    ``converter`` [default: ``curry.topython``]
      The conversion to apply to values before comparing with the expected
      results.

    ``postprocessor`` [default: ``sorted``]
      Indicates how to process the results of curry.eval before comparing.  By
      default, the values are sorted.

  Examples:
  ---------
  This decorator can be used with boilerplate similar to the following:

      class MyTestCase(cytest.TestCase):
        @check_expressions()
        def test_go(self):
          # more code

  Within the test function, yield an expression along with its expected
  properties.  For example:

      yield 1, '1', '<Int 1>', 1, [1]

  Trailing arguments can be omitted when no checks are desired.  This is useful
  when the value cannot be translated to anything in Python:

      yield [prelude.Just 1], 'Just 1', '<Just <Int 1>>'

  It is also possible to skip a check by supplying ``None``.  In the following
  example, the representation of a failure both as a string and a Python value
  are ignored.  The fifth argument ensures this expression produced no values:

      yield curry.expr.fail, 'failed', None, None, []  # no results

  For non-deterministic computations, the results should be put in a
  deterministic order.  By default, values are sorted:

      yield curry.choice(2, 1), None, None, None, [1, 2]

  '''
  def decorator(gen):
    def checker(self):
      for spec in gen(self):
        expr, str_, repr_, python, evaluated = (spec + 5 * (None,))[:5]
        e = curry.expr(expr)
        if str_ is not None:
          self.assertEqual(str(e), str_)
        if repr_ is not None:
          self.assertEqual(repr(e), repr_)
        if python is not None:
          self.assertEqual(curry.topython(e), python)
        if evaluated is not None:
          values = curry.eval(e)
          if converter is not None:
            values = map(converter, values)
          if postprocessor is not None:
            values = postprocessor(values)
          self.assertEqual(values, evaluated)
    return checker
  return decorator

