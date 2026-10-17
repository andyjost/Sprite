'''
The Results of curry.eval under the public API.  Nothing runs at
the call; each next() runs the search to the next value; the state is kept
across a break; close() ends it; a failure yields no value; an error or a
suspension is raised at its turn and ends the stream, so the values behind
it never come.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Stream')
P = curry.import_('Prelude')
eq = P['=:=']

def collect(values, limit=6):
  '''The values of a Results as text, then the error or the end.'''
  out = []
  for _ in range(limit):
    try:
      out.append(str(next(values)))
    except StopIteration:
      out.append('StopIteration')
      break
    except Exception as error:
      out.append(type(error).__name__ + ': ' + str(error))
  return out

# The call makes a Results and runs nothing.
values = curry.eval(M.three)
print('type ->', type(values).__name__)
print('next ->', next(values))

# A for loop that breaks keeps the state of the search: the next value
# after the break is the third.
for value in values:
  print('loop ->', value)
  break
print('next after break ->', next(values))
print('next at the end ->', next(values, 'StopIteration'))

# close() ends the search; nothing more comes.
values = curry.eval(M.three)
print('first ->', next(values))
values.close()
print('after close ->', list(values))

# A failed goal is no value: next() with a default gives the default, and
# the list is empty.
print('nothing ->', next(curry.eval(M.nothing), None), list(curry.eval(M.nothing)))

# An error among the values is raised at its turn and ends the stream: the
# 2 of "1 ? error "boom" ? 2" never comes.
print('mixed ->', collect(curry.eval(M.mixed)))

# A suspension: x + 1 =:= 3 with x free blocks on the rigid +, and next()
# raises SuspensionError, a subclass of EvaluationError.
print('x + 1 =:= 3 ->', collect(curry.eval(eq(curry.free('x') + 1, 3))))

# A choice between a value and a suspension: the value comes first, then
# the suspension, in either order of the operands.
print('(x =:= 1) ? (y + 1 =:= 3) ->',
      collect(curry.eval(curry.choice(eq(curry.free('x'), 1), eq(curry.free('y') + 1, 3)))))
print('(y + 1 =:= 3) ? (x =:= 1) ->',
      collect(curry.eval(curry.choice(eq(curry.free('y') + 1, 3), eq(curry.free('x'), 1)))))

# one() checks uniqueness; the context manager closes even after a break.
for label, goal in [('one', 7), ('none', M.nothing), ('many', M.three)]:
  try:
    print(label + '.one() ->', curry.eval(goal).one())
  except (curry.NoValueError, curry.ManyValuesError) as error:
    print(label + '.one() !!', type(error).__name__)
with curry.eval(M.three) as values:
  print('context first ->', next(values))
print('after context ->', list(values))
