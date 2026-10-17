'''
A module of the same name after reset or reload, and stale objects (#114).

A reset stales the old module. Reload replaces its code in place and stales
its earlier terms. Each incarnation runs its own code.
'''
import curry

def vals(*goal):
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

def compile_same(n):
  '''Compiles a module named Same whose f is n.'''
  return curry.compile('f :: Int\nf = %d' % n, name='Same')

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

# Reload replaces this module in place and refuses its earlier term.
old = second.f
third = curry.reload(second, text='f :: Int\nf = 3')
print('reload is second ->', third is second)
print('sorted(curry.modules) after reload ->', sorted(curry.modules))
print('third.f ->', vals(third.f))
print("curry.import_('Same') is third ->", curry.import_('Same') is third)
try:
  vals(old)
except curry.StaleError as error:
  print('old term after reload !!', type(error).__name__)

# The two old modules again: both are stale.
for label, module in [('first', first)]:
  try:
    module.f
  except curry.StaleError as error:
    print(label + '.f after the reload !!', type(error).__name__)
