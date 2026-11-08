"""The opt-in list-segment matcher: enumeration, laziness and fallback."""
import cytest

SOURCE = r'''
{-# LANGUAGE FunctionalPatterns #-}
module Segment where
splits :: [Int] -> ([Int],Int,Int,[Int])
splits (xs ++ [x,y] ++ ys) = (xs,x,y,ys)
lazy :: [Int] -> Int
lazy (_ ++ [x,y] ++ _) = y
same :: [Int] -> (Int,Int)
same (_ ++ [x,y] ++ _) = (x,x)
nonlinear :: [Int] -> Int
nonlinear (_ ++ [x,x] ++ _) = x
pick :: Int -> Int
pick n = if n == 1 then 0 ? 1 else failed
small :: (Int,Int)
small = let r = pick x in (x =:<= 1) &> (r,r) where x free
splitGoal = splits [1,2,3]
lazyGoal = lazy [failed,2]
partialGoal = lazy (1:2:failed)
choiceGoal = same [0 ? 1,2]
nonlinearGoal = nonlinear [1,1]
'''


class TestContinuationMatcher(cytest.TestCase):
  def test_opt_in_semantics_and_default(self):
    for flag, mode in (('0', 'all'), ('1', 'all'), ('1', 'off')):
      code = '''
import os
os.environ['SPRITE_FUNPAT_CONT'] = %r
os.environ['SPRITE_CACHE_FILE'] = ''
import curry
import tempfile
from pathlib import Path
curry.reset(interpret=%r, jit='off')
temp = tempfile.TemporaryDirectory()
source = Path(temp.name) / 'Segment.curry'
source.write_text(%r)
m = curry.import_('Segment', path=[temp.name] + curry.path)
expected = {
    'splitGoal': ['([], 1, 2, [3])', '([1], 2, 3, [])'],
    'lazyGoal': ['2'], 'partialGoal': ['2'],
    'choiceGoal': ['(0, 0)', '(1, 1)'], 'nonlinearGoal': ['1'],
    'small': ['(0, 0)', '(0, 1)', '(1, 0)', '(1, 1)']}
for name, want in expected.items():
    got = sorted(str(x) for x in curry.eval(getattr(m,name)))
    assert got == sorted(want), (name,got,want)
    print(name, got)
from curry.toolchain.flat2icurry import flatcurry as fc, funpat
from curry.toolchain import _frontend
fcy = _frontend.interfacefile(m.__file__, '.fcy')
prog = fc.load(fcy)
new, count = funpat.transform_prog(prog)
assert count == 3, count
assert funpat.transform_prog(new)[1] == 0
assert curry.cache.route_version() == (10010 if %r == '1' else 10)
assert _frontend.ROUTE_VERSION == 10
from curry.toolchain import _curry2icurry, _filenames
icy = _filenames.icurryfilename(str(source))
assert _curry2icurry.source_matches(str(source), icy)
os.environ['SPRITE_FUNPAT_CONT'] = '1' if %r == '0' else '0'
assert not _curry2icurry.source_matches(str(source), icy)
''' % (flag, mode, SOURCE, flag, flag)
      proc = cytest.run_in_subprocess(code, timeout=90, address_space=2 << 30)
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == '__main__':
  import unittest
  unittest.main()
