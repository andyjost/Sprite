import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Choice as C, Prelude as P

print(list(curry.eval(curry.choice(1, 2))))
t = C.coin
shared = t + t
print(shared)
print(sorted(curry.eval(shared)))
print(sorted(set(curry.eval(C.coin + C.coin))))
goal = curry.term(1) + C.coin
print(goal, sorted(curry.eval(goal)))
print(sorted(curry.eval(goal.__choice__(9))))
ones = curry.let(curry.ref('a'), a=P[':'](1, curry.ref('a')))
print(ones)
print(curry.eval(P.take(5, ones)).one())
print(curry.eval(P.map(C.inc, [1, 2, 3])).one())
function = curry.eval(C.adder(10)).one()
print(isinstance(function, curry.Function))
print(curry.eval(function(5)).one())
