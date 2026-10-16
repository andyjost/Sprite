'''
curry.compile of Curry text in both modes.

Curry text crosses the boundary as a module (the default mode) or as an
expression (mode='expr').  A module gets a generated name or the one of
modulename, and a name in use is refused.  A module object in imports makes
it visible to the text; a library name in imports is imported on demand (P32, #146).  An
expression is typed from its text, with exprtype where the text alone is
overloaded.  The front end runs in this process on every run.
'''
import os, curry

HERE = os.path.dirname(os.path.abspath(__file__))

def show(label, thunk):
  '''Prints what thunk returns, or the class and last line of the error.'''
  try:
    print(label, '->', thunk())
  except Exception as exc:
    print(label, '!!', type(exc).__name__ + ':', str(exc).strip().splitlines()[-1].strip())

def vals(*goal):
  return list(curry.eval(*goal, converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(*goal)]

# The text of Nat.curry, compiled as an anonymous module: the name is
# generated, and the module is in curry.modules under it.
with open(os.path.join(HERE, 'Nat.curry'), encoding='utf-8') as stream:
  Nat = curry.compile(stream.read())
print('anonymous module ->', Nat.__name__, sorted(curry.modules))
print('natFromInt 3 ->', texts(Nat.natFromInt, 3))

# A named module, and the same name a second time (P32).
Named = curry.compile('x :: Int\nx = 7', modulename='Named')
print("'Named' in curry.modules ->", 'Named' in curry.modules)
show('the same name again', lambda: curry.compile('x :: Int\nx = 8', modulename='Named'))

# imports=[Nat]: a module object; the text imports it under its name.
Use = curry.compile('import %s\nfive :: Nat\nfive = natFromInt 5' % Nat.__name__, imports=[Nat])
print('five ->', texts(Use.five))

# imports by a library name imports the module on demand (P32, #146).  The import line of
# the text alone works.
NUB = 'import Data.List\nn :: [Int]\nn = nub [1, 1, 2]'
show("imports=['Data.List']", lambda: curry.compile(NUB, imports=['Data.List']))
print('the import line of the text ->', vals(curry.compile(NUB).n))

# mode='expr': the text is a goal.  exprtype fixes its type.
print("'natFromInt 3' as an expression ->"
    , texts(curry.compile('natFromInt 3', mode='expr', imports=[Nat])))
expr = curry.compile('natToInt (I O)', mode='expr', imports=[Nat], exprtype='Int')
print("'natToInt (I O)' with exprtype='Int' ->", vals(expr), curry.typeof(expr))

# A str given to eval is a String value, not a goal (P12).
print("eval('natToInt O') ->", vals('natToInt O'))

# Overloaded text without a type is a CompileError; exprtype resolves it.
show("'toEnum 65' without a type", lambda: texts(curry.compile('toEnum 65', mode='expr')))
print("'toEnum 65' with exprtype='Char' ->"
    , vals(curry.compile('toEnum 65', mode='expr', exprtype='Char')))

# A syntax error: the class alone, as the message holds a path (P45).
try:
  curry.compile('f :: Int\nf = = 1')
except Exception as exc:
  print('a syntax error !!', type(exc).__name__)
