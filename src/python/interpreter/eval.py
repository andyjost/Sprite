'''
Implements Interpreter.eval.
'''

from . import conversions
from ..backends.py import runtime as pyruntime
from ..utility.binding import binding

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
  results = pyruntime.Evaluator(interp, interp.expr(*args)).D()
  if convert is None:
    return results
  else:
    return (convert(interp, result) for result in results)

def makegoal(interp, args):
  return interp.expr(
      getattr(interp.prelude, '$!!')
    , interp.prelude.id
    , interp.expr(*args)
    )
