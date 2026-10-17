'''
Residuation and concurrency driven from Python (the public API).

Five programs of PAKCS cross the boundary by import.  rigidadd adds by
residuation: add suspends on a free argument (ensureNotFree) until the
conjunction & lets the generator isNat bind it.  rigidor suspends an
or-branch the same way.  infresiduate reverses by narrowing, where
residuation would not end.  Account is an active object: an account waits
on a stream of messages (ensureSpine) while a client appends to the
stream, and the final stream is the value.  digit solves arithmetic as a
passive constraint: x + x =:= y and x * x =:= y wait until digit x binds x.
A goal with parameters is applied to named variables from curry.free(name)
and asked with curry.solve, which yields an Answer per value, printed as the
REPL prints it.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
rigidadd, rigidor = curry.import_('rigidadd'), curry.import_('rigidor')
infresiduate = curry.import_('infresiduate')
Account, digit = curry.import_('Account'), curry.import_('digit')

# rigidadd.goal: add x O =:= S O & isNat x.  True once x is bound to S O.
print('rigidadd.goal ->', list(curry.eval(rigidadd.goal)))

# rigidor.goal: f (g x) (h x) & x =:= 0.  g and h suspend on x until the
# equation binds it; then f 0 _ applies.
print('rigidor.goal ->', list(curry.eval(rigidor.goal)))

# infresiduate.goal l = rev [0] l: the reversal of [0] by narrowing.
l = curry.free('l')
print('infresiduate.goal l ->', [str(a) for a in curry.solve(infresiduate.goal(l))])

# Account.goal1 b and goal2 b: the balance after the deposits and the
# withdrawal, read back through the variable b.
b = curry.free('b')
print('Account.goal1 b ->', [str(a) for a in curry.solve(Account.goal1(b))])
print('Account.goal2 b ->', [str(a) for a in curry.solve(Account.goal2(b))])

# Account.goal3 s: the client and the account exchange messages over the
# stream s until the balance is 50.  The binding of s is the whole stream, a
# Python list of messages.
s = curry.free('s')
for value, bindings in curry.solve(Account.goal3(s)):
  print('Account.goal3 s ->', value)
  for message in bindings['s']:
    print('  ', message)

# digit.goal x y: the digits x with x + x == x * x: 0 and 2.
x, y = curry.free('x'), curry.free('y')
print('digit.goal x y ->', [str(a) for a in curry.solve(digit.goal(x, y))])
