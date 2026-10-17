'''
The goals of Tools.curry through the API, after sprite-exec and the REPL
ran them (see the run script of the driver): the same values in the same
words.

The port of 51-tools-parity to the public API.  The module crosses
the boundary by import.  curry.eval yields the values of a goal one by one
as Python data; a goal without a value yields none, and a goal that raises
raises EvaluationError at the first value.  The text goal with where ins
free goes through curry.parse and curry.solve, whose answers print as the
REPL prints them.  curry.typeof answers :type.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Tools

def lines(results):
  '''Prints the results one per line, as the tools do.'''
  for value in results:
    print(curry.show(value))

print('coin:')
lines(curry.eval(Tools.coin))

# The text goal of the REPL: the bindings of ins come with each answer.
print('rule "a" ins where ins free:')
lines(curry.solve(curry.parse('rule "a" ins where ins free', imports=[Tools])))

print(':type coin ->', 'coin ::', curry.typeof(Tools.coin))

# A goal without a value: the iterator ends at once.
print('nothing:')
lines(curry.eval(Tools.nothing))

# A goal that raises: the class of the exception and the message of error.
print('boom:')
try:
  lines(curry.eval(Tools.boom))
except curry.EvaluationError as exc:
  print('EvaluationError:', exc)

print('three:')
lines(curry.eval(Tools.three))
print('main:')
lines(curry.eval(Tools.main))
