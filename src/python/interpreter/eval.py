'''
Implements Interpreter.eval.
'''

from . import conversions
from ..utility.binding import binding

def eval(interp, *args, **kwds):
  '''
  Evaluate a Curry goal.

  Args:
    *args:
        Positional arguments that specify the goal.  These are passed to
        ``Interpreter.expr``.
    converter:
        Keyword-only argument specifying the converter to use when returning
        results.  The default is 'default'.  See
        :func:``curry.interpreter.conversions.getconverter``.

  Raises:
    EvaluationError:
        A Curry error occurred during evaluation.

  Returns:
    A generator producing the values of the specified Curry program.
  '''
  converter = kwds.pop('converter', 'default')
  convert = conversions.getconverter(
      converter if converter != 'default' else interp.flags['defaultconverter']
    )
  results = interp.context.runtime.evaluate(interp, interp.expr(*args))
  if convert is None:
    return results
  else:
    return (convert(interp, result) for result in results)

