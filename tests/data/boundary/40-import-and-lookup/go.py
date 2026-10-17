'''
Import by name and by file, the Curry path, the loaded modules, and what a
module offers, on the public API.

curry.import_ takes a name, or a file recognized by its suffix.  curry.path is a list;
an assignment takes effect at the next import.  A module's attributes are
terms, M[name] reaches any name, and curry.info(M) holds types and symbols.
A library symbol is an attribute of its imported module.
'''
import os
import curry

HERE = os.path.dirname(os.path.abspath(__file__))

def show(label, thunk):
  '''Prints what thunk returns, or the class and message of the exception.'''
  try:
    print(label, '->', thunk())
  except Exception as exc:
    print(label, '!!', type(exc).__name__ + ': ' + str(exc).splitlines()[0])

curry.path.insert(0, HERE)
from curry.lib import Lookup
P = curry.import_('Prelude')

# Import by name: a second import returns the loaded object.  A file is a
# file by its suffix.
show('import_ by name is the loaded object', lambda: curry.import_('Lookup') is Lookup)
show('import_ of a path',
  lambda: curry.import_(os.path.join(HERE, 'Lookup.curry')).__name__)
show('import_ of a path is the loaded object',
  lambda: curry.import_(os.path.join(HERE, 'Lookup.curry')) is Lookup)
# An assignment to curry.path takes effect at the next import_.
saved = list(curry.path)
curry.path[:] = ['nowhere']
show("after curry.path[:] = ['nowhere'], import_('Data.Char')",
  lambda: curry.import_('Data.Char').__name__)
curry.path[:] = saved
show('sorted(curry.modules)', lambda: sorted(curry.modules))
# What the module offers: a type is under M.types, its constructors are
# attributes; an operator and a keyword name are M[name]; a private name
# is reached too.
show('Lookup.Item', lambda: Lookup.Item)
show("curry.info(Lookup).types['Item'].constructors",
  lambda: [c.name for c in curry.info(Lookup).types['Item'].constructors])
show("Lookup['+++'] [1] [2]", lambda: curry.eval(Lookup['+++']([1], [2])).one())
show("P['not'] True", lambda: curry.eval(P['not'](True)).one())
show('Lookup.twice 4', lambda: curry.eval(Lookup.twice(4)).one())
show('Lookup.helper (private) 1 2', lambda: curry.eval(Lookup.helper(1, 2)).one())
show('sorted(curry.info(Lookup).symbols)', lambda: sorted(curry.info(Lookup).symbols))
show('dir(Lookup)', lambda: dir(Lookup))
# A symbol of a library module is an attribute of the imported module.
show("P['+'] 1 2", lambda: curry.eval(P['+'](1, 2)).one())
show("import_('Data.List').nub [1, 1, 2]",
  lambda: curry.eval(curry.import_('Data.List').nub([1, 1, 2])).one())
show("import_('Data.Char').toUpper 'a'",
  lambda: curry.eval(curry.import_('Data.Char').toUpper(curry.Char('a'))).one())
show("import_('Nope')", lambda: curry.import_('Nope'))
show('sorted(curry.modules) at the end', lambda: sorted(curry.modules))
