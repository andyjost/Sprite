'''
Residuation and concurrency driven from Python.

Five programs of PAKCS cross the boundary by import.  rigidadd adds by
residuation: add suspends on a free argument (ensureNotFree) until the
conjunction & lets the generator isNat bind it.  rigidor suspends an
or-branch the same way.  infresiduate reverses by narrowing, where
residuation would not end.  Account is an active object: an account waits
on a stream of messages (ensureSpine) while a client appends to the
stream, and the final stream is the value.  digit solves arithmetic as a
passive constraint: x + x =:= y and x * x =:= y wait until digit x binds x.
A goal with parameters gets markers from curry.free(), paired in a tuple.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import rigidadd, rigidor, infresiduate, Account, digit

def vals(*goal):
  return list(curry.eval(curry.expr(*goal), converter='topython'))

def texts(*goal):
  return [str(v) for v in curry.eval(curry.expr(*goal), converter=None)]

# rigidadd.goal: add x O =:= S O & isNat x.  True once x is bound to S O.
print('rigidadd.goal ->', vals(rigidadd.goal))

# rigidor.goal: f (g x) (h x) & x =:= 0.  g and h suspend on x until the
# equation binds it; then f 0 _ applies.
print('rigidor.goal ->', vals(rigidor.goal))

# infresiduate.goal l = rev [0] l: the reversal of [0] by narrowing.
l = curry.free()
print('(infresiduate.goal l, l) ->', vals(([infresiduate.goal, l], l)))

# Account.goal1 b and goal2 b: the balance after the deposits and the
# withdrawal, read back through the marker b.
b = curry.free()
print('(Account.goal1 b, b) ->', vals(([Account.goal1, b], b)))
b = curry.free()
print('(Account.goal2 b, b) ->', vals(([Account.goal2, b], b)))

# Account.goal3 s: the client and the account exchange messages over the
# stream s until the balance is 50.  The value of s is the whole stream.
s = curry.free()
for value in curry.eval(curry.expr(([Account.goal3, s], s)), converter=None):
  print('(Account.goal3 s, s) ->', value[0])
  for message in str(value[1]).strip('[]').split(', '):
    print('  ', message)

# digit.goal x y: the digits x with x + x == x * x: 0 and 2.
x, y = curry.free(), curry.free()
print('(digit.goal x y, x, y) ->', vals(([digit.goal, x, y], x, y)))
