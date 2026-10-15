'''
The goals of Tools.curry through the API, after sprite-exec and the REPL
ran them (see the run script): the same values in the same words.

The module crosses the boundary by import.  curry.eval yields the values
of a goal one by one; a goal without a value yields none, and a goal that
raises raises EvaluationError at the first value.  The text goal with
where ins free goes through curry.compile(mode='expr'), and its values
carry the bindings, printed as the REPL prints them.  curry.typeof answers
:type.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Tools

def lines(goal):
  '''Prints the values of goal one per line, as the tools do.'''
  for value in curry.eval(goal):
    print(value)

print('coin:')
lines(Tools.coin)

# The text goal of the REPL: the bindings of ins come with each value.
print('rule "a" ins where ins free:')
lines(curry.compile('rule "a" ins where ins free', mode='expr', imports=[Tools]))

print(':type coin ->', 'coin ::', curry.typeof(Tools.coin))

# A goal without a value: the generator ends at once.
print('nothing:')
lines(Tools.nothing)

# A goal that raises: the class of the exception and the message of error.
print('boom:')
try:
  lines(Tools.boom)
except curry.exceptions.EvaluationError as exc:
  print('EvaluationError:', exc)

print('three:')
lines(Tools.three)
print('main:')
lines(Tools.main)
