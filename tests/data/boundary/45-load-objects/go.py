'''
The compiled object on the C++ backend: a module loaded from its object, a
save of it, a load during and after a background compile, a refused second
load, and evaluation after the swap.

The run script compiled Obj to a shared object with sprite-make, so the
import loads the object and no background compile runs.  curry.save of
that module returns C++ text with its step functions (#113).  A second
module, Other, is imported from its source: it runs interpreted while the
background compile runs; evaluation still works after the swap.
curry.load of the object of Obj returns the loaded module; the object of a
second copy under the same name is refused with DynloadError, and the
module still works after the refusal (#109).  The exit status is 0.
'''
import glob, os, curry
from curry.backends.cxx import tiered

HERE = os.path.dirname(os.path.abspath(__file__))

def vals(*goal):
  return list(curry.eval(goal[0](*goal[1:]) if len(goal) > 1 else goal[0]))

def objects(subdir):
  '''The shared objects of Obj under subdir.'''
  return sorted(glob.glob(os.path.join(HERE, subdir, '.curry', '*', 'Obj.so')))

curry.path.insert(0, HERE)
Obj = curry.import_('Obj')
print('Obj.f ->', vals(Obj.f))
status = tiered.status()
print('background compiles after the import ->', status['queued'] + status['running'])

# #113: the saved module of an object-loaded module has step functions.
text = curry.save(Obj, module_main=False)
print('save: first line ->', text.splitlines()[0])
print('save: step functions ->'
    , sum(1 for line in text.splitlines() if line.startswith('tag_type Cy')))

# Other is compiled in the background; wait for the swap.
Other = curry.import_('Other')
print('Other.h ->', vals(Other.h))
tiered.wait()
print('swapped modules ->', tiered.status()['swapped_modules'])

# curry.load of the object: the same module.  The object of the second
# copy, under the same name, is refused (#109), and Obj still runs.
so, so2 = objects('.'), objects('second')
print('objects ->', [os.path.basename(p) for p in so], [os.path.basename(p) for p in so2])
print('load of the object is Obj ->', curry.load(so[0]) is Obj)
try:
  curry.load(so2[0])
except Exception as exc:
  print('load of the second copy !!', type(exc).__name__)
print('Obj.g 1 after the refusal ->', vals(Obj.g, 1))
