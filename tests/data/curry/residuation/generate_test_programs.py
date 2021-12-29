#!/usr/bin/python

import sys
sys.path.insert(0, '../../scripts')
from generate_test_programs_lib import generate_test_programs

PROGRAMS = [
    'main = list21'
  , 'main = show list21'
  , 'main = show $!! list21'
  ]

list21 = \
'''{-# ORACLE_RESULT main "[2,1]" #-}
list21 :: [Int]
list21 = [x, x=:=2&>1] where x free
'''

generate_test_programs([
  # programtext       fileprefix  digits  predef
  # +------------------+-----------+-------+-----------------------------------
    (PROGRAMS        , 'reslist' , 2     , list21                             )
  ])
