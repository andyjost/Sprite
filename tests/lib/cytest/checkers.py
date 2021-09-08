'''
Defines decorators for writing test methods that yield a series of test
specification.  To use these, one decorates some method of cytest.TestCase.
That method should yield a sequence of tuples to be checked.  Each of the
checkers accepts a continuation to be passed the generated values.
'''
import contextlib, curry, inspect, traceback

# @contextlib.contextmanager
# def capture_generator(generator):
#   '''
#   Context manager that traps errors and appends the stack of a generator.
#   '''
#   assert inspect.isgenerator(generator)
#   try:
#     yield generator
#   except Exception as e:
#     generator_frame = dict(inspect.getmembers(generator))['gi_frame']
#     message = '%s\nObtained from:\n%s' % (
#         str(e)
#       , ''.join(traceback.format_stack(generator_frame))
#       )
#     raise type(e)(message)

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
  def decorator(testmethod):
    def checker(self, spec):
      # specs = testmethod(self)
      # for spec in specs:
      #   with capture_generator(specs):
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
    # testmethod.continuation = checker
    # return checker
    return _makechecker(testmethod, checker)
  return decorator

def check_indexing(testmethod):
  '''
  Checks functions that index into a Curry expression.

  The wrapped method should generate triples comprising an expression
  specifier, path, and expected result.  The expression specifier will be
  passed to ``curry.expr``.  The expression returned is indexed by calling
  self.INDEXER.  If the expected result is an exception instance or class, the
  indexing step must raise that exception.  If it is an instance, then the
  string value should be a regular expression to check the raised exception
  against.  Otherwise, the value is compared equal to the expected result.
  '''
  def checker(self, spec):
    # specs = testmethod(self)
    # for exprspec, path, expected in specs:
    #   with capture_generator(specs):
    exprspec, path, expected = spec
    if isinstance(expected, Exception):
      regex = str(expected)
      excty = type(expected)
    elif isinstance(expected, type) and issubclass(expected, Exception):
      regex = None
      excty = expected
    else:
      regex = None
      excty = None
    e = curry.expr(exprspec)
    if excty is None:
      d = self.INDEXER(e, path)
      self.assertEqual(d, expected)
    elif regex:
      self.assertRaisesRegexp(excty, regex, lambda: self.INDEXER(e, path))
    else:
      self.assertRaises(excty, lambda: self.INDEXER(e, path))
  # testmethod.continuation = checker
  # return checker
  return _makechecker(testmethod, checker)

def check_predicate(predicate=None, mapper=None):
  '''
  Checks a predicate.

  The test method should generate tuples of arguments.  These arguments will
  be passed to the predicate, which is expected to evaluate to True.

  If no predicate is supplied, then the first argument of each tuple produced
  by the generator is used.  If a mapper is supplied, it is applied to all
  arguments (except the predicate) before testing the predicate.
  '''
  def decorator(testmethod):
    def checker(self, spec):
      if predicate is None:
        pred = spec[0]
        args = spec[1:]
      else:
        pred = predicate
        args = spec
      if mapper is not None:
        args = map(mapper, args)
      self.assertTrue(pred(*args))
    return _makechecker(testmethod, checker)
  return decorator

def _makechecker(testmethod, checker):
  if inspect.isgeneratorfunction(testmethod):
    def consumer(self):
      specs = testmethod(self)
      for spec in specs:
        try:
          checker(self, spec)
          if hasattr(testmethod, 'continuation'):
            test.method.continuation(self, spec)
        except Exception as e:
          generator_frame = dict(inspect.getmembers(specs))['gi_frame']
          message = '%s\nObtained from:\n%s' % (
              str(e)
            , ''.join(traceback.format_stack(generator_frame))
            )
          raise type(e)(message)
    return consumer
  else:
    testmethod.continuation = checker
    return testmethod

