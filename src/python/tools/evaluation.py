'''Answer lines and process statuses shared by the evaluation tools.'''

from .. import exceptions
from .utility import message_text
import importlib, sys

curry = importlib.import_module(__package__.split('.')[0])


def report_error(error):
  '''Print a public error without a traceback and return its status.'''
  try:
    sys.stdout.flush()
  except (OSError, ValueError):
    pass
  if isinstance(error, exceptions.SuspensionError):
    print('*** Evaluation suspended!', file=sys.stderr)
  else:
    print('ERROR: %s' % message_text(error), file=sys.stderr)
  return 1


def evaluate(goal, action=None, quiet=False):
  '''Print each answer; a successful IO () action has no answer line.'''
  answers = curry.solve(goal)
  silent = curry.typeof(goal, defaulted=True) == 'IO ()'
  # A reference to the graph retains the history of a long search.
  del goal
  found = False
  with answers:
    for answer in answers:
      found = True
      if not silent:
        if action is None:
          print(curry.show(answer))
        else:
          action(answer)
  if not found:
    if not quiet:
      print('*** No value found!')
    return 2
  return 0
