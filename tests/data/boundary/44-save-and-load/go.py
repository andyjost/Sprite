'''
curry.save and curry.load of a module and of a program on the Python
backend, the pair that round-trips.

A loaded module crosses the boundary back to disk as Python source:
curry.save with module_main=False writes a module that curry.load reads in
a later interpreter, and curry.save with goal='main' writes a program that
the Python of the installation runs (the run script does so after this
driver).  The goal of save is a name and not a symbol (P39).  The driver
runs in a temporary copy, so that the saved files stay out of the corpus.
'''
import os, curry

HERE = os.path.dirname(os.path.abspath(__file__))

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

curry.path.insert(0, HERE)
M = curry.import_('M')
print('M.f ->', vals(M.f))

# A module without a main program, and a program whose goal is main.
curry.save(M, os.path.join(HERE, 'M.py'), module_main=False)
curry.save(M, os.path.join(HERE, 'Prog.py'), goal='main')
print('saved ->', sorted(name for name in os.listdir(HERE) if name.endswith('.py')))

# save needs a goal or module_main=False; the first clause of the error.
try:
  curry.save(M, os.path.join(HERE, 'X.py'))
except ValueError as exc:
  print('save without a goal !! ValueError:', str(exc).split(':')[0])

# The goal is a string; a symbol is a TypeError (P39).
try:
  curry.save(M, os.path.join(HERE, 'Y.py'), goal=M.main)
except TypeError:
  print('save with goal=M.main !! TypeError')

# Without a file name, save returns the text of the module.
text = curry.save(M, module_main=False)
print('text of the module ->', text.splitlines()[0])

# A reset forgets M; load reads the saved module back under its name.
curry.reset()
L = curry.load(os.path.join(HERE, 'M.py'))
print('loaded ->', L.__name__, sorted(curry.modules))
print('L.f ->', vals(L.f))
print("curry.modules['M'] is L ->", curry.modules['M'] is L)
print('load again is L ->', curry.load(os.path.join(HERE, 'M.py')) is L)
