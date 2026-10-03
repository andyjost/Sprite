-- A package dependency solver.
--
-- An index lists every package version and the requirements of that version.
-- A plan picks one version of every package in the index.  A plan is
-- consistent when it meets the root requirements and the requirements of
-- every version it picks.  The function plans means every consistent plan.

import Data.List (nub)

-- One entry per package version: (name, version, requirements).  A
-- requirement names a package and the versions of it that satisfy it.
type Index = [(String, Int, [(String, [Int])])]

-- A requirement: the package and its acceptable versions.
type Requirement = (String, [Int])

-- One version of every package in the index.
type Plan = [(String, Int)]

-- Generate and test.  The plan assigns each package anyOf its versions, so
-- the plan is a choice among every assignment.  The guard keeps the
-- assignments that meet the roots and the requirements of the chosen
-- versions.  The runtime finds every plan that passes.
plans :: Index -> [Requirement] -> Plan
plans idx roots
  | all (holds plan) roots && all (depsHold idx plan) plan = plan
  where plan = [ (p, anyOf (versionsOf idx p)) | p <- packages idx ]

-- The package names in the index, each once, in index order.
packages :: Index -> [String]
packages idx = nub [ p | (p, _, _) <- idx ]

-- The versions of a package in the index.
versionsOf :: Index -> String -> [Int]
versionsOf idx p = [ v | (q, v, _) <- idx, q == p ]

-- A plan holds a requirement when it picks an acceptable version.
holds :: Plan -> Requirement -> Bool
holds plan (p, allowed) = case lookup p plan of
  Just v  -> v `elem` allowed
  Nothing -> False

-- A plan meets the requirements of a chosen package version.
depsHold :: Index -> Plan -> (String, Int) -> Bool
depsHold idx plan (p, v) = all (holds plan) (requirements idx p v)

-- The requirements of one package version.
requirements :: Index -> String -> Int -> [Requirement]
requirements idx p v = concat [ reqs | (q, w, reqs) <- idx, q == p, w == v ]
