-- A package dependency solver.
--
-- An index lists every version of every package with the requirements of
-- that version.  A requirement names a package and a range of its versions.
-- A plan picks one version for every package that the roots reach: the
-- roots, what their versions require, and so on.  A plan is consistent
-- when the version it picks for a package meets every requirement of that
-- package which the plan reaches.
--
-- solve means every consistent plan of the roots.  preferred means one of
-- them: the plan that a depth-first search finds first when it tries the
-- candidates of a package in the order of preference.  conflict means the
-- first violation of each branch of the search that fails.

module Deps where

import Control.SetFunctions
import Data.List (sortBy)

-- One entry per package version: (name, version, requirements).
type Entry = (String, Int, [Requirement])
type Index = [Entry]

-- A requirement: the package and the range of its acceptable versions, both
-- bounds included.
type Requirement = (String, Range)
type Range = (Int, Int)

-- A version of a package, as a lockfile or a yank list names it.
type Pin = (String, Int)

-- The chosen versions, in the order of the choices.
type Plan = [Pin]

-- A requirement with the package version that states it.  The roots have
-- the requirer ("", 0).
type Demand = (Requirement, Pin)

-- A violation: the demand that fails; the version already in the plan with
-- its requirer, or an empty list when the demand has no candidate; and the
-- choices made before it, each with its requirer.
type Conflict = (Demand, [(Int, Pin)], [(Pin, Pin)])

inRange :: Range -> Int -> Bool
inRange (lo, hi) v = lo <= v && v <= hi

-- The requirements of one package version.
requires :: Index -> Pin -> [Requirement]
requires idx (p, v) = concat [ rs | (q, w, rs) <- idx, q == p, w == v ]

-- The candidates for a requirement, in the order of preference: the version
-- of the lockfile first, then the others newest first.  A yanked version is
-- a candidate only when the lockfile names it or the range pins it.
candidates :: Index -> [Pin] -> [Pin] -> Requirement -> [Int]
candidates idx yanked lock (p, (lo, hi)) = locked ++ fresh
  where
    versions = [ v | (q, v, _) <- idx, q == p, lo <= v, v <= hi ]
    locked   = [ v | v <- versions, (p, v) `elem` lock ]
    fresh    = [ v | v <- sortBy (>=) versions, v `notElem` locked
                   , (p, v) `notElem` yanked || lo == hi ]

-- Every consistent plan of the roots.
solve :: Index -> [Pin] -> [Pin] -> [Requirement] -> Plan
solve idx yanked lock roots = solveFrom idx yanked lock roots []

-- The search from a state: the demands still to meet, in order, and the
-- versions chosen so far.  A demand on a package in the plan is a test: the
-- chosen version meets it, or the branch fails.  A demand on a new package
-- is a choice among its candidates, and the requirements of the chosen
-- version come next.  anyOf [] fails, so a package without a candidate ends
-- the branch too.
solveFrom :: Index -> [Pin] -> [Pin] -> [Requirement] -> Plan -> Plan
solveFrom _   _      _    []                 plan = plan
solveFrom idx yanked lock ((p, r) : pending) plan =
  case lookup p plan of
    Just v  -> if inRange r v then solveFrom idx yanked lock pending plan
                              else failed
    Nothing -> solveFrom idx yanked lock (requires idx (p, v) ++ pending)
                                         (plan ++ [(p, v)])
  where
    v = anyOf (candidates idx yanked lock (p, r))

-- True when the roots have a plan.  The set function encapsulates the
-- search, so the test has one value, also when solve has many or none.
solvable :: Index -> [Pin] -> [Pin] -> [Requirement] -> Bool
solvable idx yanked lock roots = notEmpty (set4 solve idx yanked lock roots)

-- The preferred plan: the search of solve, but every choice takes the first
-- candidate that still leaves a plan.  The lookahead is the set function of
-- solveFrom on the state after the candidate.  The function is
-- deterministic, so it has one value or none, in whatever order the
-- scheduler runs the branches of solve.  Its value is the plan that a
-- depth-first search over the candidates in order finds first.
preferred :: Index -> [Pin] -> [Pin] -> [Requirement] -> Plan
preferred idx yanked lock roots = preferredFrom idx yanked lock roots []

preferredFrom :: Index -> [Pin] -> [Pin] -> [Requirement] -> Plan -> Plan
preferredFrom _   _      _    []                 plan = plan
preferredFrom idx yanked lock ((p, r) : pending) plan =
  case lookup p plan of
    Just v  -> if inRange r v
                 then preferredFrom idx yanked lock pending plan
                 else failed
    Nothing -> preferredFrom idx yanked lock
                 (requires idx (p, chosen) ++ pending)
                 (plan ++ [(p, chosen)])
  where
    chosen = head [ c | c <- candidates idx yanked lock (p, r)
                      , leavesAPlan c ]
    leavesAPlan c = notEmpty (set5 solveFrom idx yanked lock
                                   (requires idx (p, c) ++ pending)
                                   (plan ++ [(p, c)]))

-- The first violation of a failing branch of the search.  The search is
-- that of solve, with the requirer beside every demand and every choice.
-- A branch that reaches a plan has no violation and fails here, so when the
-- roots have no plan, the values of conflict are the ends of every branch.
conflict :: Index -> [Pin] -> [Pin] -> [Requirement] -> Conflict
conflict idx yanked lock roots =
  conflictFrom idx yanked lock [ (r, ("", 0)) | r <- roots ] []

conflictFrom :: Index -> [Pin] -> [Pin] -> [Demand] -> [(String, (Int, Pin))]
             -> Conflict
conflictFrom _   _      _    []                         _    = failed
conflictFrom idx yanked lock (((p, r), by) : pending) plan =
  case lookup p plan of
    Just (v, by') -> if inRange r v
                       then conflictFrom idx yanked lock pending plan
                       else (((p, r), by), [(v, by')], trace)
    Nothing -> if null cs
                 then (((p, r), by), [], trace)
                 else conflictFrom idx yanked lock
                        ([ (r', (p, chosen)) | r' <- requires idx (p, chosen) ]
                           ++ pending)
                        (plan ++ [(p, (chosen, by))])
  where
    cs     = candidates idx yanked lock (p, r)
    chosen = anyOf cs
    trace  = [ ((q, w), who) | (q, (w, who)) <- plan ]

-- The root names that the index does not know.  The driver asks this before
-- the search, so that "no such package" and "no plan" differ.
unknown :: Index -> [Requirement] -> [String]
unknown idx roots =
  [ p | (p, _) <- roots, p `notElem` [ q | (q, _, _) <- idx ] ]
