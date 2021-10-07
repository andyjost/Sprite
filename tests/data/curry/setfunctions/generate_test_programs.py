#!/usr/bin/python

import sys
sys.path.insert(0, '../../scripts')
from generate_test_programs_lib import generate_test_programs

PREDEF = '''\
{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
'''

# Test encapsulated narrowing computations.
BASIC_PROGRAMS = [
    'main = sortValues (set0 a)'
  , 'main = sortValues (set0 (True ? False))'
  , 'main = sortValues (set1 g1 a)'
  , 'main = sortValues (set1 f1 a)'
  , 'main = sortValues $ set2 g2 a a'
  , 'main = sortValues $ set2 g2 a (True ? False)'
  , 'main = sortValues $ set2 g2 (True ? False) a'
  , 'main = sortValues $ set2 g2 (True ? False) (True ? False)'
  , 'main = sortValues $ set2 g2 a (False ? True)'
  , 'main = sortValues $ set2 g2 (False ? True) (True ? False)'
  , 'main = sortValues $ set2 f2 a a'
  , 'main = sortValues $ set2 f2 a (True ? False)'
  , 'main = sortValues $ set2 f2 (True ? False) a'
  , 'main = sortValues $ set2 f2 (True ? False) (True ? False)'
  , 'main = sortValues $ set2 f2 a (False ? True)'
  , 'main = sortValues $ set2 f2 (False ? True) (True ? False)'
  , 'main = sortValues $ set1 fa ab'
  , 'main = sortValues $ set1 fa abc'
  , 'main = sortValues $ set1 k a'
  , 'main = sortValues $ set1 k (True ? False)'
  ]

# Test set functions applied to free variables.  PAKCS cannot evaluate them.
FREE_PROGRAMS = [
    'main = sortValues (set1 g1 x) where x free'
  , 'main = sortValues (set1 f1 x) where x free'
  , 'main = sortValues $ set2 g2 a x where x free'
  , 'main = sortValues $ set2 g2 x x where x free'
  , 'main = sortValues $ set2 g2 x y where x,y free'
  , 'main = sortValues $ set2 g2 x (True ? False) where x free'
  , 'main = sortValues $ set2 g2 (True ? False) x where x free'
  , 'main = sortValues $ set2 f2 a x where x free'
  , 'main = sortValues $ set2 f2 x x where x free'
  , 'main = sortValues $ set2 f2 x y where x,y free'
  , 'main = sortValues $ set2 f2 x (True ? False) where x free'
  , 'main = sortValues $ set2 f2 (True ? False) x where x free'
  ]

# Test when a set function applies to an expression.
EXPR_PROGRAMS = [
    'main = sortValues (set1 (g1 ? h1) a)'
  , 'main = sortValues (set1 (f1 ? f1) a)'
  , 'main = sortValues (set1 (f1 ? f1) (True ? False))'
  ]

# Test when a set function applies one of its argument.
APPLY_PROGRAMS = [
    r'main = sortValues $ set1 (\x -> x a) id'
  , r'main = sortValues $ set1 (\x -> x True) comb'
  , r'main = sortValues $ set1 (\x -> x a) comb'
  , r'main = sortValues $ set1 (\x -> x a a) f2'
  , r'main = sortValues $ set1 (\x -> let y = a in x y y) f2'
  , r'main = sortValues $ set2 (\x y -> x y a) f2 True'
  , r'main = sortValues $ set2 (\x y -> x y a) f2 a'
  , r'main = sortValues $ set1 (\x -> x a a) (f2 ? g2)'
  , r'main = sortValues $ set1 (\x -> let y = a in x y y) (f2 ? g2)'
  , r'main = sortValues $ set2 (\x y -> x y a) (f2 ? g2) True'
  , r'main = sortValues $ set2 (\x y -> x y a) (f2 ? g2) a'
  , r'main = sortValues $ (set3 (\x a b -> x a ? x b)) fa ab A'
  , r'main = sortValues $ (set3 (\x a b -> x (a ? b))) fa ab A'
  , r'main = sortValues $ (set2 (\a b -> fa a ? fa b)) ab A'
  , r'main = sortValues $ (set2 (\a b -> fa (a ? b))) ab A'
  , r'main = sortValues $ (set3 (\x a b -> x a ? x b)) ga A x where x free'
  , r'main = sortValues $ (set3 (\x a b -> x a ? x b)) fa ab x where x free'
  , r'main = sortValues $ (set3 (\x a b -> x (a ? b))) fa ab x where x free'
  ]

# Test set functions involving constraints.
CONSTRAINT_PROGRAMS = [
    r'main = sortValues $ set1 (\u -> u =:= a) a'
  , r'main = sortValues $ set1 (\u -> u =:= x) a where x free'
  , r'main = sortValues $ set1 (\u -> u =:= unknown) a'
  , r'main = sortValues $ set1 (\u -> u =:= a) y where y free'
  , r'main = sortValues $ set1 (\u -> u =:= x) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u =:= unknown) (y::Bool) where y free'
  , r'main = sortValues $ set1 (\u -> a =:= u) a'
  , r'main = sortValues $ set1 (\u -> x =:= u) a where x free'
  , r'main = sortValues $ set1 (\u -> unknown =:= u) a'
  , r'main = sortValues $ set1 (\u -> a =:= u) y where y free'
  , r'main = sortValues $ set1 (\u -> x =:= u) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> unknown =:= u) (y::Bool) where y free'
  , r'main = (sortValues $ set1 (\u -> u =:= x) a, x) where x free'
  , r'main = (x, sortValues $ set1 (\u -> u =:= x) a) where x free'
  , r'main = (x, sortValues $ set1 (\u -> u =:= x) a, x) where x free'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> x) a'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> u) a'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> a) a'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> x) (y::Bool) where y free'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> u) (y::Bool) where y free'
  , r'main = sortValues $ set1 (\u -> let x=unknown in u=:=x &> a) (y::Bool) where y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow x) (x::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow u) (x::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow a) (x::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> a       ) (x::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow y) (x::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow x) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow u) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow a) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> a       ) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow y) (y::Bool) where x,y free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow x) (a::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow u) (a::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow a) (a::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> a       ) (a::Bool) where x free'
  , r'main = sortValues $ set1 (\u -> u=:=x &> narrow y) (a::Bool) where x,y free'
  ]

NOT_GROUND_PROGRAMS = [
    '{-# ORACLE_RESULT * _a #-}\n'
    'main :: Bool\n'
    'main = chooseValue $ set0 f\n'
    '    where f = x\n'
    '          x free\n'

  , '{-# ORACLE_RESULT * (_a, _a) #-}\n'
    'main :: (Bool, Bool)\n'
    'main = chooseValue $ set1 f x\n'
    '    where f u = (x, u)\n'
    '          x free\n'

  , '{-# ORACLE_RESULT * (_a, _a, _b) #-}\n'
    'main :: (Bool, Bool, Bool)\n'
    'main = chooseValue $ set2 f x y\n'
    '    where f u v = (x, u, v)\n'
    '          x,y free\n'

  ### Also involving constraints.

  , 'main = sortValues $\n'
    '  set1 (\\u -> let x=unknown in u=:=x &> (z::Bool)) (y::Bool)\n'
    '  where y,z free\n'

  , '{-# ORACLE_RESULT * [_a] #-}\n'
    'main = sortValues $\n'
    '  set1 (\\u -> let x=unknown in u=:=x &> x) (y::Bool)\n'
    '  where y free\n'

  , '{-# ORACLE_RESULT * [_a] #-}\n'
    'main = sortValues $\n'
    '  set1 (\\u -> let x=unknown in u=:=x &> u) (y::Bool)\n'
    '  where y free\n'

  , 'main = sortValues $\n'
    '  set1 (\\u -> let x=unknown in u=:=x &> a) (y::Bool)\n'
    '  where y free\n'

  , 'main = sortValues $\n'
    '  set1 (\\u -> (x::Bool)) (y::Bool)\n'
    '  where x,y free\n'

  ]

# Programs for applicative set functions.
APPLICATIVE_PROGRAMS = [
    '-- Split on the argument.\n'
    '{-# ORACLE_RESULT * Values [G_T] #-}\n'
    '{-# ORACLE_RESULT * Values [G_F] #-}\n'
    'main = evalS (set g1 $> x) where x free\n'

  , '-- No splits.\n'
    '{-# ORACLE_RESULT * Values [G_T, G_F] #-}\n'
    'main = evalS (set g1 $< x) where x free\n'

  , '-- Split on g/h.  (f1) reduces to (g1) and (h1).\n'
    '{-# ORACLE_RESULT * Values [G_F, G_T] #-}\n'
    '{-# ORACLE_RESULT * Values [H_F, H_T] #-}\n'
    'main = evalS (set f1 $< x) where x free\n'

  , '-- Split on g/h and the argument.\n'
    '{-# ORACLE_RESULT * Values [G_F] #-}\n'
    '{-# ORACLE_RESULT * Values [G_T] #-}\n'
    '{-# ORACLE_RESULT * Values [H_F] #-}\n'
    '{-# ORACLE_RESULT * Values [H_T] #-}\n'
    'main = evalS (set f1 $> x) where x free\n'

  , "-- No splits.  (h') is not reducible.\n"
    '{-# ORACLE_RESULT * Values [G_F, G_T, H_F, H_T] #-}\n'
    "main = evalS (set f1' $< x) where x free\n"

  , '-- Split on the argument only.\n'
    '{-# ORACLE_RESULT * Values [G_F, H_F] #-}\n'
    '{-# ORACLE_RESULT * Values [G_T, H_T] #-}\n'
    "main = evalS (set f1' $> x) where x free\n"

  , '-- Split on g/h.  (f3) reduces to (g3) and (h3).\n'
    '{-# ORACLE_RESULT * Values [G_F, G_T] #-}\n'
    '{-# ORACLE_RESULT * Values [H_F, H_T] #-}\n'
    'main = evalS (set f1 $< x) where x free\n'

  ]

generate_test_programs([
  # programtext           fileprefix   digits  predef
  # +---------------------+------------+-------+-----------------------------
    (BASIC_PROGRAMS       , 'basic'    , 2     , PREDEF                     )
  , (FREE_PROGRAMS        , 'free'     , 2     , PREDEF                     )
  # , (EXPR_PROGRAMS        , 'expr',    , 2     , PREDEF                     )
  # , (APPLY_PROGRAMS       , 'apply'    , 2     , PREDEF                     )
  # , (CONSTRAINT_PROGRAMS  , 'constr'   , 2     , PREDEF                     )
  # , (NOT_GROUND_PROGRAMS  , 'notground', 2     , PREDEF                     )
  , (APPLICATIVE_PROGRAMS , 'applic'   , 2     , PREDEF                     )
  ])
