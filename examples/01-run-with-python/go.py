import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Hello as H, Prelude as P

print(curry.eval(H.greet('Python')).one())
with curry.eval(H.number) as results:
  for value in results:
    print('first:', value)
    break
  print('remaining:', list(results))  # break kept the position
print('closed:', list(results))
print('all:', list(curry.eval(H.number)))
print('no value:', list(curry.eval(H.nothing)))
try:
  curry.eval(H.nothing).one()
except curry.NoValueError as error:
  print(type(error).__name__, error)
results = curry.eval(H.bad)
print('eval returned; now next')
try:
  next(results)
except curry.DivisionByZeroError as error:
  print(type(error).__name__, error)
try:
  P.ord('A')
except curry.ConversionError as error:
  print(type(error).__name__, error)
print(curry.eval(P.ord(curry.Char('A'))).one())
print(curry.typeof([1, 2.5]), curry.eval([1, 2.5]).one())
try:
  curry.eval(P.read('5'))
except curry.DefaultingError as error:
  print(type(error).__name__, error)
print(curry.eval(curry.term(P.read('5'), type='Int')).one())
