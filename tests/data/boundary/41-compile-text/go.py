'''
Curry text crosses the boundary, on the public API: curry.compile
makes a module, and curry.parse reads a goal as the REPL reads it, a type
annotation in Curry.  imports takes names and module objects.  A str given
to curry.eval is refused with the two spellings.
'''
import os
import curry

HERE = os.path.dirname(os.path.abspath(__file__))

def show(label, thunk):
  '''Prints what thunk returns, or the class and the message of the error.'''
  try:
    print(label, '->', thunk())
  except Exception as exc:
    message = ' | '.join(l.strip() for l in str(exc).strip().splitlines())
    print(label, '!!', type(exc).__name__ + ':', message)

# The text of Nat.curry, compiled as an anonymous module.
with open(os.path.join(HERE, 'Nat.curry'), encoding='utf-8') as stream:
  Nat = curry.compile(stream.read())
print('anonymous module ->', curry.info(Nat).name, sorted(curry.modules))
print('natFromInt 3 ->', list(curry.eval(Nat.natFromInt(3))))

# A named module, and the same name a second time.
Named = curry.compile('x :: Int\nx = 7', modulename='Named')
print("'Named' in curry.modules ->", 'Named' in curry.modules)
show('the same name again', lambda: curry.compile('x :: Int\nx = 8', modulename='Named'))

# imports=[Nat]: a module object; the text imports it under its name.
Use = curry.compile(
    'import %s\nfive :: Nat\nfive = natFromInt 5' % curry.info(Nat).name, imports=[Nat])
print('five ->', list(curry.eval(Use.five)))

# imports by a library name, and the import line of the text alone.
NUB = 'import Data.List\nn :: [Int]\nn = nub [1, 1, 2]'
show("imports=['Data.List']", lambda: curry.eval(curry.compile(NUB, imports=['Data.List']).n).one())
print('the import line of the text ->', curry.eval(curry.compile(NUB).n).one())

# curry.parse: the text is a goal; a type annotation is written in Curry.
print("'natFromInt 3' parsed ->", list(curry.eval(curry.parse('natFromInt 3', imports=[Nat]))))
expr = curry.parse('natToInt (I O) :: Int', imports=[Nat])
print("'natToInt (I O) :: Int' ->", curry.eval(expr).one(), curry.typeof(expr))

# A str given to eval is refused.
show("eval('natToInt O')", lambda: list(curry.eval('natToInt O')))

# Overloaded text parses with its scheme; eval cannot default it; the
# annotation resolves it.
show("typeof 'toEnum 65'", lambda: curry.typeof(curry.parse('toEnum 65')))
show("eval 'toEnum 65' without a type", lambda: curry.eval(curry.parse('toEnum 65')).one())
print("'toEnum 65 :: Char' ->", curry.eval(curry.parse('toEnum 65 :: Char')).one())

# A syntax error: the first error line, no path.
try:
  curry.compile('f :: Int\nf = = 1')
except curry.CompileError as exc:
  print('a syntax error !!', type(exc).__name__ + ':', exc)
