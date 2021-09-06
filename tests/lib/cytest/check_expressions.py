'''Defines decorator check_expressions.'''
import curry

def check_expressions(gen):
  '''
  The wrapped function should generate a sequence of tuples with up to five
  elements.  This function builds the specified expression, e, and checks any
  of the supplied properties.  Any property passed as None will be skipped.  If
  the tuple has fewer than 5 elements, missing properties will be skipped.
  The tuple elements are as follows:

      [1] A sequence of arguments to curry.expr.
      [2] The expected str(e).
      [3] The expected repr(e).
      [4] The expected result of topython(e).
      [5] The expected result of list(curry.eval(e))
  '''
  def impl(self):
    for spec in gen(self):
      args, str_, repr_, python, evaluated = (spec + 5 * (None,))[:5]
      e = curry.expr(*args)
      if str_ is not None:
        self.assertEqual(str(e), str_)
      if repr_ is not None:
        self.assertEqual(repr(e), repr_)
      if python is not None:
        self.assertEqual(curry.topython(e), python)
      if evaluated is not None:
        self.assertEqual(list(curry.eval(e)), evaluated)
  return impl

