# Find a perfect hash function for the Java keywords by searching the
# programs over three operations, shortest first; then do the same search
# in plain Python and compare the time.
import itertools, sys, time
import os
import curry
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import PerfectHash as H

KEYWORDS = '''abstract assert boolean break byte case catch char class const
continue default do double else enum extends final finally float for goto if
implements import instanceof int interface long native new package private
protected public return short static strictfp super switch synchronized this
throw throws transient try void volatile while'''.split()
SIZE = 512

for n in (1, 2, 3):
  t0 = time.perf_counter()
  with curry.eval(H.perfect(KEYWORDS, SIZE, n)) as results:
    found = next(results, None)
  print(f'length {n}: {9 ** n} programs; {found}')
  print(f'curry length {n}: {time.perf_counter() - t0:.6f} s', file=sys.stderr)
  if found is not None:
    break

# The same search in Python over the same space, for the comparison.
M32 = 4294967296
def key(s):
  h = 7
  for c in s: h = (h * 31 + ord(c)) % M32
  return h
OPS = [('Mul', c) for c in (31, 33, 37, 65599)] + [('Shr', k) for k in (2, 4)] + [('Add', c) for c in (1, 7, 13)]
def apply(ops, x):
  for name, c in ops:
    x = (x * c) % M32 if name == 'Mul' else x // (2 ** c) if name == 'Shr' else (x + c) % M32
  return x
keys = [key(k) for k in KEYWORDS]
t0 = time.perf_counter()
for n in (1, 2, 3):
  hit = next((ops for ops in itertools.product(OPS, repeat=n)
              if len({apply(ops, k) % SIZE for k in keys}) == len(keys)), None)
  if hit: break
print(f'python: length {n}: {hit}')
print(f'python search: {time.perf_counter() - t0:.6f} s', file=sys.stderr)
