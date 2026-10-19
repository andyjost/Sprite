import os
from itertools import islice
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Streams as M

s = curry.stream(M.threeOut)
print('before:', s.result)
print(list(s))
print('result:', curry.show(s.result))
primes = curry.stream(M.primesOut)
try:
  print(list(islice(primes, 10)))
finally:
  primes.close()
totals = curry.stream(M.totalsOut)
print('totals:', list(totals))
print('result:', totals.result)
