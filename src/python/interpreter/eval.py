'''
Implements Interpreter.eval.
'''

from . import conversions
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
  # The C++ backend applies the objects compiled in the background here
  # (backends.cxx.tiered).
  interp.backend.before_evaluation(interp)
  # The goal object hands its node to the runtime state and keeps no
  # reference to it; see Goal.evaluate.
  return goals.make_goal(interp, args).evaluate(interp, convert)
