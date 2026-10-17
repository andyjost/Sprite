'''
Values that come back from Curry.  The converter 'topython' turns the data
of the Prelude into Python values and leaves user constructors, functions
and free variables as nodes.  A value carries no type of its own, so the
empty String is [] unless a type is given.  The flag defaultconverter
changes the default in place; an assignment to curry.flags changes nothing.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Out')
P = curry.import_('Prelude')

def vals(*goal, **kwds):
  return list(curry.eval(*goal, converter='topython', **kwds))

def texts(*goal, **kwds):
  kwds.setdefault('converter', None)
  return [str(value) for value in curry.eval(*goal, **kwds)]

# Values of a user type: the text is the Curry show; the converter leaves
# the constructors as nodes inside a Python list.
print('items ->', texts(M.items))
print('items converted ->', vals(M.items))

# A function as a value: the text is its name; the converted value is a
# partial application node, whose repr differs by backend, so its class
# alone is printed.
print('id inc ->', texts(P.id, M.inc), type(vals(P.id, M.inc)[0]).__name__)

# A Char converts to a str of length 1; the text keeps the quotes.
print('chr 65 ->', texts(P.chr, 65), vals(P.chr, 65))

# The empty String: the goal has a type, so eval converts it to ''.  The
# value alone is [] in Curry and types as [a], so topython without a type
# gives [] and with exprtype='String' gives '' (P18).
print('emptyString ->', texts(M.emptyString), vals(M.emptyString))
node, = curry.eval(M.emptyString, converter=None)
print('topython ->', curry.topython(node), repr(curry.topython(node, exprtype='String')))

# Strings inside a structure follow the type of the goal: "" is '' here.
print('pairs ->', texts(M.pairs), vals(M.pairs))

# converter=None keeps the nodes.
print('converter=None ->', [type(node).__name__ for node in curry.eval(M.pairs, converter=None)])

# The flag defaultconverter, changed in place, converts by default.  An
# assignment to curry.flags rebinds the name of the package and changes
# nothing (P54).  Both are restored.
curry.flags['defaultconverter'] = 'topython'
print("flags['defaultconverter'] = 'topython' ->", list(curry.eval(M.inc, 1)))
curry.flags['defaultconverter'] = None
flags = curry.flags
curry.flags = {'defaultconverter': 'topython'}
print("flags = {...} ->", list(curry.eval(M.inc, 1)))
curry.flags = flags

# A free variable in a value: show_value prints it as _a, as PAKCS does.
value, = curry.eval(M.freeList, converter=None)
print('freeList ->', curry.show_value(value))
