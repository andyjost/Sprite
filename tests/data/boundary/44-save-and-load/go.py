'''
curry.save and curry.load of a module and of a program on the Python
backend, the pair that round-trips.

A loaded module crosses the boundary back to disk as Python source:
curry.save with module_main=False writes a module that curry.load reads in
a later interpreter, and curry.save with main=M.main writes a program that
the Python of the installation runs (the run script does so after this
driver).  The goal of save is a name and not a symbol (P39).  The driver
runs in a temporary copy, so that the saved files stay out of the corpus.
'''
import os, curry

HERE = os.path.dirname(os.path.abspath(__file__))

def vals(*goal):
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

curry.path.insert(0, HERE)
M = curry.import_('M')
print('M.f ->', vals(M.f))

# A module without a main program, and a program whose goal is main.
curry.save(M, os.path.join(HERE, 'M.py'))
curry.save(M, os.path.join(HERE, 'Prog.py'), main=M.main)
print('saved ->', sorted(name for name in os.listdir(HERE) if name.endswith('.py')))

# A term names the main goal; the destination path is required.
curry.save(M, os.path.join(HERE, 'Y.py'), main=M.main)
print('save with main=M.main -> program')
try:
  curry.save(M)
except TypeError:
  print('save without path !! TypeError')

# A reset forgets M; load reads the saved module back under its name.
curry.reset()
L = curry.load(os.path.join(HERE, 'M.py'))
print('loaded ->', L.__name__, sorted(curry.modules))
print('L.f ->', vals(L.f))
print("curry.modules['M'] is L ->", curry.modules['M'] is L)
print('load again is L ->', curry.load(os.path.join(HERE, 'M.py')) is L)
