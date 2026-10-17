'''
Values that come back from Curry under the public API.  curry.eval
converts by one table: the data of the Prelude become Python values, a
Char a curry.Char, a constructor of a user type a Data, a function a
Function, and an unbound variable the Var itself.  A value carries its
type, so the empty String is ''.  There is no converter flag.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Out')
P = curry.import_('Prelude')

def texts(goal):
  return [curry.show(value) for value in curry.eval(goal)]

# Values of a user type: the text is the Curry show; the conversion leaves
# the constructors as Data inside a Python list.
print('items ->', texts(M.items))
print('items converted ->', list(curry.eval(M.items)))

# A function as a value: the text is its name; the converted value is a
# Function, so its class alone is printed.
print('id inc ->', texts(P.id(M.inc)), type(curry.eval(P.id(M.inc)).one()).__name__)

# A Char converts to a curry.Char, a str of length 1; the text keeps the
# quotes.
print('chr 65 ->', texts(P.chr(65)), list(curry.eval(P.chr(65))))

# The empty String: the value carries its type, so it is '' however it is
# reached.
print('emptyString ->', texts(M.emptyString), list(curry.eval(M.emptyString)))
value = curry.eval(M.emptyString).one()
print('emptyString value ->', repr(value), curry.typeof(M.emptyString))

# Strings inside a structure follow the type of the goal: "" is '' here.
print('pairs ->', texts(M.pairs), list(curry.eval(M.pairs)))

# The Python classes of the values.
print('classes ->', [type(value).__name__ for value in curry.eval(M.pairs).one()])

# A free variable in a value: the printer prints it as _a, as PAKCS does.
value = curry.eval(M.freeList).one()
print('freeList ->', curry.show(value))
