-- A build system: the decisions of make as a relation.
--
-- Python describes a toy C project and a table of file stamps.  Curry
-- answers the questions of make: which rule builds a target, what a target
-- reads, what is stale, what to build and in which order, what can run now,
-- what a change touches, and which targets two rules claim.  Curry never
-- touches the file system.  Python owns the files and runs the recipes.

module Build where

import Control.SetFunctions
import Data.List ((\\), nub)

type Name = String

-- A rule: the target, its direct inputs, and the words of its recipe.
type Rule = (Name, [Name], [String])

-- The stamps of the files that exist.  A larger stamp is a newer file.  A
-- missing file has no entry.
type Table = [(Name, Int)]

-- The project as Python describes it.
data Project = Project
  { sources  :: [Name]            -- the C sources
  , library  :: (Name, [Name])    -- the static library and its objects
  , program  :: (Name, [Name])    -- the program and its objects
  , includes :: [(Name, [Name])]  -- the headers each file includes
  , explicit :: [Rule]            -- rules written for one target each
  }

-- 1. Which rule builds a target?  Each equation is one rule, and every
-- equation that matches is one answer.  The first is the pattern rule
-- %.o: %.c of make: the functional pattern stem ++ ".o" matches an object
-- name and binds the stem.  The next two name their targets.  The last takes
-- the explicit rules of the project: the free variables ins and words take
-- the inputs and the recipe of every entry for the target.
rulesFor :: Project -> Name -> Rule
rulesFor _ (stem ++ ".o") =
  (stem ++ ".o", [stem ++ ".c"], ["cc", "-c", "-o", stem ++ ".o", stem ++ ".c"])
rulesFor p t | t == lib = (lib, objs, "ar" : "rcs" : lib : objs)
  where (lib, objs) = library p
rulesFor p t | t == prog = (prog, objs ++ [lib], "cc" : "-o" : prog : objs ++ [lib])
  where (prog, objs) = program p
        lib = fst (library p)
rulesFor p t | (t, ins, words) =:= anyOf (explicit p) = (t, ins, words)
  where ins, words free

-- The rules of a target as a list.  The set function collects every answer
-- of rulesFor.  No rule means a source or a header.  Two rules are the
-- ambiguity of 7.  The rest of the module reads the rules through this list.
rulesOf :: Project -> Name -> [Rule]
rulesOf p t = sortValues (set2 rulesFor p t)

-- The targets: one object per source, the library, the program, and the
-- target of every explicit rule.  An explicit rule for a new name adds a
-- target; one for a target of the project adds a second rule.
targets :: Project -> [Name]
targets p = nub (map object (sources p) ++ [fst (library p), fst (program p)]
                 ++ [t | (t, _, _) <- explicit p])

-- The object of a source: the suffix .c becomes .o.
object :: Name -> Name
object s = case reverse s of
  ('c' : '.' : rest) -> reverse rest ++ ".o"

-- 2. What does a target read?  The inputs of its rule, each with the headers
-- it includes, directly or through another header.  A file that no rule
-- builds reads nothing.
inputs :: Project -> Name -> [Name]
inputs p t =
  nub [f | (_, ins, _) <- rulesOf p t, f <- concatMap (withIncludes p []) ins]

-- A file and every header it includes.  The list seen stops a cycle of
-- includes, as an include guard does.
withIncludes :: Project -> [Name] -> Name -> [Name]
withIncludes p seen f
  | f `elem` seen = []
  | otherwise     = f : concatMap (withIncludes p (f : seen)) headers
  where headers = maybe [] id (lookup f (includes p))

-- The recipe of a target: the words of its rule.
recipe :: Project -> Name -> [String]
recipe p t = head [words | (_, _, words) <- rulesOf p t]

-- 3. What is stale?  A target is stale when it is missing, when it is older
-- than an input, or when an input is stale.  A file that reads nothing is
-- stale only when it is missing.  The list seen holds the targets on the
-- path from the question to this file, as in withIncludes: a target on its
-- own path reads nothing more, so a cycle of rules ends here and fails in
-- layers.
stale :: Project -> Table -> Name -> Bool
stale p table = staleFrom p table []

staleFrom :: Project -> Table -> [Name] -> Name -> Bool
staleFrom p table seen t
  | t `elem` seen = False
  | otherwise     = case lookup t table of
      Nothing -> True
      Just s  -> any (\i -> staleFrom p table (t : seen) i
                              || maybe False (s <) (lookup i table))
                     (inputs p t)

-- 4. What to build, and in which order?  The stale targets in waves: a wave
-- holds the stale targets whose stale inputs are all in earlier waves, so
-- the targets of one wave can run at once.  A cycle leaves targets that
-- never enter a wave.  The guard fails then, and the plan has no value.
waves :: Project -> Table -> [[Name]]
waves p table = layers p [t | t <- targets p, stale p table t]

layers :: Project -> [Name] -> [[Name]]
layers _ []      = []
layers p pending | not (null wave) = wave : layers p (pending \\ wave)
  where wave = [t | t <- pending, all (`notElem` pending) (inputs p t)]

-- The plan: every stale target in dependency order, with what it reads and
-- the words of its recipe.
plan :: Project -> Table -> [Rule]
plan p table = [(t, inputs p t, recipe p t) | t <- concat (waves p table)]

-- 5. What can run now?  The stale targets whose inputs are all up to date.
-- The driver runs them in parallel, records the new stamps, and asks again.
ready :: Project -> Table -> [Name]
ready p table =
  [t | t <- targets p, stale p table t, not (any (stale p table) (inputs p t))]

-- 6. What does a change touch?  The relation of 2 read backwards: the target
-- is the unknown, drawn from the targets, and the guard asks whether it reads
-- the file, directly or through another target.  Each answer is one value.
affected :: Project -> Name -> Name
affected p f | reads p t f = t
  where t = anyOf (targets p)

reads :: Project -> Name -> Name -> Bool
reads p = readsFrom p []

-- The list seen stops a cycle of rules, as in staleFrom.
readsFrom :: Project -> [Name] -> Name -> Name -> Bool
readsFrom p seen t f
  | t `elem` seen = False
  | otherwise     = f `elem` ins || any (\i -> readsFrom p (t : seen) i f) ins
  where ins = inputs p t

-- 7. Which targets do two rules claim?  One rule is a well-defined target.
-- Two rules are an ambiguity, which the driver reports.  Make would pick one
-- of them by a tie-break rule you have to remember.
ambiguous :: Project -> [(Name, [Rule])]
ambiguous p = [(t, rulesOf p t) | t <- targets p, length (rulesOf p t) > 1]
