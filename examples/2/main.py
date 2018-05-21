import curry
from curry.lib import Peano

for ans in curry.eval([Peano.add, [Peano.S, Peano.O], Peano.O]):
  print str(ans)

