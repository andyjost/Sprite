# Named variables cross the boundary as values of curry.free; solve returns
# every answer with its bindings; a rigid operation on an unbound variable
# suspends until another conjunct binds it.
import os
import curry
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Vars as V
P = curry.import_('Prelude')

print(curry.eval(V.last([1, 2, 3])).one())
for xs, ys in curry.eval(V.split([1, 2, 3])):
  print(xs, ys)

# The same relation stated in Python: two named variables, all the answers.
xs, ys = curry.free('xs'), curry.free('ys')
for answer in curry.solve(P['=:='](P['++'](xs, ys), [1, 2, 3])):
  print(answer, '   xs =', answer.bindings['xs'], '  ys =', answer.bindings[ys])

# An unbound variable prints as itself; the equation leaves it in the answer.
z = curry.free('z')
print(curry.solve(P['=:='](P['++']([1], z), P['++']([1], z))).one())

# Rigid arithmetic waits.  Alone, the wait never ends: a suspension.
x = curry.free('x')
try:
  list(curry.eval(P['=:='](x + 1, 3)))
except curry.SuspensionError as error:
  print('suspended:', error)

# With a generator beside it, the arithmetic resumes once x is bound.
# & is the concurrent conjunction; the dunders build the Prelude's terms.
print(curry.solve(P['=:='](x, 2) & P['=:='](x + 1, 3)).one())
