'''
Implements Interpreter.eval.
'''

from . import conversions
from . import runtime

def eval(interp, *args, **kwds):
  '''
  Evaluate a Curry goal.

  Parameters:
  -----------
  ``*args``
      Positional arguments that specify the goal.  These are passed to
      ``Interpreter.expr``.
  ``converter``
      Keyword-only argument specifying the converter to use when returning
      results.  The default is 'default'.  See ``conversions.getconverter``.

  Returns:
  --------
  A generator producing the values of the specified Curry program.
  '''
  converter = kwds.pop('converter', 'default')
  convert = conversions.getconverter(
      converter if converter != 'default' else interp.flags['defaultconverter']
    )
  goal = interp.expr(*args)
  results = runtime.Evaluator(interp, goal).D()
  if convert is None:
    return results
  else:
    return (convert(interp, result) for result in results)
