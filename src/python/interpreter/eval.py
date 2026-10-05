'''
Implements Interpreter.eval.
'''

from . import conversions
from ..utility.binding import binding
from ..backends.generic.eval import evaluator
from ..typecheck import goals

def eval(interp, *args, **kwds):
  '''
  Evaluate a Curry goal.

  Args:
    *args:
        Positional arguments that specify the goal.  These are passed to
        ``Interpreter.expr``.  One function symbol whose scheme has class
        constraints and no value parameter, a goal without a signature such
        as ``main = Just 5``, is applied to its dictionaries first: the
        constraints are defaulted with the table of the PAKCS REPL (see
        :mod:`curry.typecheck.defaulting`), so the goal evaluates to a value
        and not to a partial application.  An expression of
        ``curry.compile(mode='expr')`` whose text declared ``where x free``
        variables absent from its result type yields its values with the
        bindings of those variables
        (:class:`curry.typecheck.goals.Bindings`).
    converter:
        Keyword-only argument specifying the converter to use when returning
        results.  The default is 'default'.  See
        :func:``curry.interpreter.conversions.getconverter``.

  Raises:
    EvaluationError:
        A Curry error occurred during evaluation.
    CurryTypeError:
        The table cannot default a class constraint of the goal.

  Returns:
    A generator producing the values of the specified Curry program.
  '''
  converter = kwds.pop('converter', 'default')
  convert = conversions.getconverter(
      converter if converter != 'default' else interp.flags['defaultconverter']
    )
  goal = goals.make_goal(interp, args)
  results = evaluator.evaluate(interp, goal.raw_expr)
  return goal.values(interp, results, convert)
