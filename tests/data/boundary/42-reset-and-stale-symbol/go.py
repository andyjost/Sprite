'''
A module of the same name after curry.reset and curry.reload, and a symbol
that outlives the reset (#114, open).

A reset makes the held module and its symbols stale.  A new module with
that name runs its own code.  The landed reload still replaces the whole
interpreter; the session lane will change its signature.
'''
import curry

def vals(*goal):
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

def compile_same(n):
  '''Compiles a module named Same whose f is n.'''
  return curry.compile('f :: Int\nf = %d' % n, modulename='Same')

first = compile_same(1)
print('first.f ->', vals(first.f))

# A soft reset: the modules go, the Prelude stays.
curry.reset()
print('sorted(curry.modules) after reset ->', sorted(curry.modules))
second = compile_same(2)
print('second.f ->', vals(second.f))
print('first is second ->', first is second)

# The old module refuses access after the reset.
try:
  first.f
except curry.StaleError as error:
  print('first.f after the reset !!', type(error).__name__)

# A hard reset: curry.reload builds a new interpreter and takes flags.
curry.reload()
print('sorted(curry.modules) after reload ->', sorted(curry.modules))
third = compile_same(3)
print('third.f ->', vals(third.f))
print("curry.import_('Same') is third ->", curry.import_('Same') is third)
print('sorted(curry.modules) ->', sorted(curry.modules))

# The two old modules again: both are stale.
for label, module in [('second', second), ('first', first)]:
  try:
    module.f
  except curry.StaleError as error:
    print(label + '.f after the reload !!', type(error).__name__)
