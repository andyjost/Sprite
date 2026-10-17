'''
An edited source is not read again by curry.import_ in one process (#110).

The driver writes the module Ed with f = 1, imports it, and rewrites the
file with f = 2.  A second import_ returns the loaded module and warns on
stderr that the source changed; the running code is the old one.  On the
C++ backend the background compile does not swap the running code when the
source changed (the narrower rule of the fix of #110).  A reset and a new
import read the file again.  The run script runs the driver in a temporary
copy, so that the file it writes stays out of the corpus.
'''
import os, time, curry

HERE = os.path.dirname(os.path.abspath(__file__))

def vals(*goal):
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

def write(n):
  '''Writes Ed.curry with f = n.'''
  with open(os.path.join(HERE, 'Ed.curry'), 'w', encoding='utf-8') as stream:
    stream.write('module Ed where\nf :: Int\nf = %d\n' % n)

curry.path.insert(0, HERE)
write(1)
M = curry.import_('Ed')
print('f ->', vals(M.f))

# The edit.  A second later, so that the modification time of the file
# moves past the time the import recorded.
time.sleep(1.1)
write(2)
print("import_('Ed') is the loaded module ->", curry.import_('Ed') is M)
print('f after the edit ->', vals(M.f))

# The background compile of the C++ backend, when there is one, never swaps
# the running code to the code of a changed source, whichever file its child
# read.  On the Python backend wait returns at once.
curry.wait()
print('f after the background compile ->', vals(M.f))

# A reset forgets the module; the next import reads the file.
del M
curry.reset()
curry.path.insert(0, HERE)
print('f after reset and import ->', vals(curry.import_('Ed').f))
