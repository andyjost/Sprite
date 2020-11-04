#!/usr/bin/python

import sys
sys.path.insert(0, '../../scripts')
from generate_test_programs_lib import generate_test_programs

LAST_PREDEF = '''
last (xs++[x]) = x
main = '''

LAST_PROGRAMS = [
    'last []'
  , 'last [True]'
  , 'last [failed, False]'
  , 'last [failed, (failed, True)]'
  , 'snd $ last [failed, (failed, True)]'
  , 'fst $ last [failed, (True, failed)]'
  , 'snd $ last [(failed, True)]'
  ]


SPLIT_PREDEF = '''
split :: [Bool] -> ([Bool],[Bool])
split (x++y) = (x,y)
main = '''

SPLIT_PROGRAMS = [
    'split []'
  , 'split [True]'
  , 'split [True,False]'
  , 'split [True,False,True]'
  , 'split [x] where x free'
  , 'split [True,x] where x free'
  , 'split [x,True] where x free'
  , 'split [False,x,True] where x free'
  , 'split [x,y] where x,y free'
  , 'split [True,x,y] where x,y free'
  , 'split [x,True,y] where x,y free'
  , 'split [x,y,True] where x,y free'
  ]

ISIN_PREDEF = '''
data N = N1 | N2 | N3 | N4 | N5
isin :: N -> [N] -> Bool
isin x (_++[x]++_) = True
main = '''

ISIN_PROGRAMS = [
    'N1 `isin` []'
  , 'N1 `isin` [N1]'
  , 'N1 `isin` [N2]'
  , 'N1 `isin` [N2, N3, N4, N5]'
  , 'N1 `isin` [N2, N3, N1, N4, N5]'
  , 'N1 `isin` [N2, N3, N4, N5, N1]'
  ]

PERM_PREDEF = '''
data N = N1 | N2 | N3 | N4 | N5
insert :: N -> [N] -> [N]
insert a [] = [a]
insert a (b:bs) = a:b:bs
insert a (b:bs) = b: insert a bs
perm :: [N] -> [N]
perm [] = []
perm (a:as) = insert a (perm as)

main = '''

PERM_PROGRAMS = [
    'insert N1 [N2, N3, N4, N5]'
  , 'insert N1 []'
  , 'perm [N1, N2, N3]'
  ]

generate_test_programs([
  # programtext         fileprefix      digits  predef
  # +-------------------+---------------+-------+-------------
    (LAST_PROGRAMS    , 'funpat_last' , 2     , LAST_PREDEF )
  , (SPLIT_PROGRAMS   , 'funpat_split', 2     , SPLIT_PREDEF)
  , (ISIN_PROGRAMS    , 'funpat_isin' , 2     , ISIN_PREDEF )
  , (PERM_PROGRAMS    , 'funpat_perm' , 2     , PERM_PREDEF )
  ])
