#!/usr/bin/python

import operator as op, sys
sys.path.insert(0, '../../scripts')
from generate_test_programs_lib import generate_test_programs
from math import *

negate = op.neg

def safe(f, *args):
  # Indicates whether the given function application should succeed.
  try:
    f = eval(f)
    f(*args)
  except ValueError:
    return False
  else:
    return True

INTEGER_MATH_PROGRAMS = [
    template.format(op, a)     # Int -> Int
        for a in [3, -2]
        for op in ['negate']
        for template in [ 'main = {0} ({1!r})' ]
  ] + [
    template.format(op, a, b)  # Int -> Int -> Int
        for a,b in [(3, 7), (-2, 5), (10, -2), (-3, -4)]
        for op in ['+', '-', '*', '`div`', '`mod`', '`quot`', '`rem`']
        for template in [ 'main = ({1!r}) {0} ({2!r})'
                        , 'main = ({2!r}) {0} ({1!r})'
                        ]
  ] + [
    template.format(op, a)     # Float -> Int
        for a in [0.25, -0.3]
        for op in ['ceiling', 'floor', 'round', 'truncate']
        for template in [ 'main = {0} ({1!r})' ]
  ]

FLOAT_MATH_PROGRAMS = [
    template.format(op, a)     # Float -> Float (positive)
        for a in [0.25, 1.1, 0. -0.33]
        for op in [
            'negate', 'exp', 'log', 'sqrt' , 'sin', 'cos', 'tan', 'asin'
          , 'acos', 'atan' , 'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh'
          ]
        for template in [ 'main = {0} ({1!r})' ]
        if safe(op, a)
  ] + [
    template.format(op, a, b)  # Float -> Float -> Float
        for a,b in [(3.1, 7.5), (-2.0, 5.2), (10.9, -2.3), (-3.2, -4.4)]
        for op in ['+', '-', '*', '/']
        for template in [ 'main = ({1!r}) {0} ({2!r})'
                        , 'main = ({2!r}) {0} ({1!r})'
                        ]
  ] + [
    template.format(op, a)     # Int -> Float
        for a in [0, 1, -3]
        for op in ['fromIntegral']
        for template in [ 'main = {0} ({1!r})' ]
  ]

COMPARE_PROGRAMS = [
    template.format(op, a, b)
        for a,b in [(1, 2), ('a', 'b'), (1.1, 1.2)]
        for op in ['==', '/=', '<', '<=', '>', '>=']
        for template in [ 'main = {1!r} {0} {1!r}'
                        , 'main = {1!r} {0} {2!r}'
                        , 'main = {2!r} {0} {1!r}'
                        ]
  ] + [
    template.format(op, a, b)
        for a,b in [(True, True), (True, False), (False, True), (False, False)]
        for op in ['&&', '||']
        for template in [ 'main = {1!r} {0} {1!r}' ]
  ]

SORT_PROGRAMS = [
    'main :: [Int]\n'    'main = sort [3, 1, 2]'
  , 'main :: [Char]\n'   "main = sort ['c', 'a', 'b']"
  , 'main :: [Char]\n'   'main = sort "cab"'
  , 'main :: [Float]\n'  'main = sort [1.3, 1.1, 1.2]'
  , 'main :: [String]\n' 'main = sort ["banana", "apple", "carrot"]'
  ]


generate_test_programs([
  # programtext              fileprefix    digits  predef
  # +-------------------------+-------------+-------+------------------------
    (INTEGER_MATH_PROGRAMS    , 'intmath'   , 3     , 'main :: Int\n'       )
  , (FLOAT_MATH_PROGRAMS      , 'floatmath' , 3     , 'main :: Float\n'     )
  , (COMPARE_PROGRAMS         , 'compare'   , 2     , 'main :: Bool\n'      )
  , (SORT_PROGRAMS            , 'sort'      , 2     , 'import Data.List\n'  )
  ])
