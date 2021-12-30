#!/usr/bin/python

import sys
sys.path.insert(0, '../../scripts')
from generate_test_programs_lib import generate_test_programs

PROGRAMS = [
    'main = list21'
  , 'main = show $!! list21'
  , 'main = show $## list21'
  , 'main = show [2,1]'
  , 'main = head $!! [True,x] where x free'
  ]

SUSPENDING_PROGRAMS = [
    'main = show list21'
  , 'main = show $# list21'
  , 'main = head $## [True,x] where x free'
  ]

RESULT = '{-# ORACLE_RESULT main "[2,1]" #-}\n'
SUSPEND = '{-# ORACLE_RESULT main !suspend #-}\n'

DEFS = \
'''
list21 :: [Int]
list21 = [x, x=:=2&>1] where x free
'''

generate_test_programs([
  #  programtext           fileprefix  digits  predef
  # -+---------------------+-----------+-------+---------------
    (PROGRAMS            , 'reslist' , 2     , RESULT + DEFS  )
  , (SUSPENDING_PROGRAMS , 'suslist' , 2     , SUSPEND + DEFS )
  ])
