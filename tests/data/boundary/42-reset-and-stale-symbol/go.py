'''
A module of the same name after curry.reset and curry.reload, and a symbol
that outlives the reset (#114, open).

A module object and its symbols are Python objects that stay alive after
curry.reset clears the interpreter's modules.  A new module of the same
name then runs its own code (the first symptom of #114, fixed).  The old
symbol still evaluates: on the C++ backend it runs the code of the newest
module of that name, where the Python backend keeps the old code.  The
driver pins today's output on the C++ backend; a fixed system refuses the
evaluation of the old symbol.
'''
import curry

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

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

# #114: the old symbol evaluates after the reset.  Today's output on the
# C++ backend is 2, the value of the new code; the Python backend gives 1.
print('first.f after the reset ->', vals(first.f))
print('first.f.interpreter is None ->', first.f.interpreter is None)

# A hard reset: curry.reload builds a new interpreter and takes flags.
print('curry.reload ->', curry.reload.__doc__.strip().splitlines()[0])
curry.reload()
print('sorted(curry.modules) after reload ->', sorted(curry.modules))
third = compile_same(3)
print('third.f ->', vals(third.f))
print("curry.import_('Same') is third ->", curry.import_('Same') is third)
print('sorted(curry.modules) ->', sorted(curry.modules))

# The two old symbols again: both run the code of third on the C++ backend.
print('second.f after the reload ->', vals(second.f))
print('first.f after the reload ->', vals(first.f))
