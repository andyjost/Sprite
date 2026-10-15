'''
Import by name and by file, the Curry path, the loaded modules, and what a
module offers.

A Curry module crosses the boundary as a Python module object.  curry.import_
finds a name on curry.path; a file name needs is_sourcefile=True.  The
object offers the public functions and the constructors as attributes, an
operator through getattr, a type through curry.type, and a symbol of any
loaded module through curry.symbol.  Each line prints what a call returns,
or the class of the exception it raises; a message that holds a path is
left out.
'''
import os, curry

HERE = os.path.dirname(os.path.abspath(__file__))

def show(label, thunk, message=False):
  '''Prints what thunk returns, or the class of the exception it raises.'''
  try:
    print(label, '->', thunk())
  except Exception as exc:
    print(label, '!!', type(exc).__name__ + (': ' + str(exc) if message else ''))

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

curry.path.insert(0, HERE)
from curry.lib import Lookup
P = curry.module('Prelude')

# Import by name: a second import returns the loaded object.
show('import_ by name is the loaded object', lambda: curry.import_('Lookup') is Lookup)
# Import by file: a path is not a legal module name without the flag (P39).
show('import_ of a path', lambda: curry.import_(os.path.join(HERE, 'Lookup.curry')))
show('import_ of a path with is_sourcefile=True'
    , lambda: curry.import_(os.path.join(HERE, 'Lookup.curry'), is_sourcefile=True).__name__)
# An assignment to curry.path rebinds a name of the package; the interpreter
# keeps its own list (P54).  Change the list in place instead.
path = curry.path
curry.path = ['nowhere']
show('after curry.path = [...] the interpreter keeps its list'
    , lambda: curry.getInterpreter().path is path)
curry.path = path
show('sorted(curry.modules)', lambda: sorted(curry.modules))
# What the module offers (P34): a type is not an attribute, its constructors
# are, and curry.type reaches the type.  An operator needs getattr, and so
# does a Prelude name that is a Python keyword.  A private function is absent.
show('Lookup.Item', lambda: Lookup.Item)
show("curry.type('Lookup.Item').constructors"
    , lambda: [str(c) for c in curry.type('Lookup.Item').constructors])
show("getattr(Lookup, '+++') [1] [2]", lambda: vals(getattr(Lookup, '+++'), [1], [2]))
show("getattr(P, 'not') True", lambda: vals(getattr(P, 'not'), True))
show('Lookup.twice 4', lambda: vals(Lookup.twice, 4))
show('Lookup.helper (private)', lambda: Lookup.helper)
# inspect.symbols lists the names that start with a letter: the private
# helper is in, the operator is out.  dir lists what attaches (P34).
show('inspect.symbols(Lookup)', lambda: sorted(curry.inspect.symbols(Lookup)))
show('dir(Lookup)', lambda: sorted(n for n in dir(Lookup) if not n.startswith(('_', '.'))))
# curry.symbol takes a dotted name and splits it at the first dot (P33), so
# a symbol of Data.List is found once the package Data is loaded.
show("curry.symbol('Prelude.+') 1 2", lambda: vals(curry.symbol('Prelude.+'), 1, 2))
show("curry.symbol('Data.List.nub') before an import"
    , lambda: curry.symbol('Data.List.nub'), message=True)
curry.import_('Data.List')
show("curry.symbol('Data.List.nub') after the import"
    , lambda: vals(curry.symbol('Data.List.nub'), [1, 1, 2]))
# curry.module imports a module of the library by name, and no other (P33).
show("curry.module('Data.Char').toUpper 'a'", lambda: vals(curry.module('Data.Char').toUpper, 'a'))
show("curry.module('Nope')", lambda: curry.module('Nope'), message=True)
show('sorted(curry.modules) at the end', lambda: sorted(curry.modules))
