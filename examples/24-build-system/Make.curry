-- Make: the questions of make over a makefile written in Curry.
--
-- A makefile is two relations and some variables.  The relation rule gives
-- a target its inputs and its recipe, one equation per rule of make.  The
-- relation depends gives a file a header it includes, one equation per
-- edge.  This module reads the rules of every name from the goal down into
-- a build, as make reads a makefile into its database, and it asks the
-- questions of make over the build: what a target reads, what is stale,
-- what to build and in which order, what can run now, what a change
-- touches, which targets two rules claim, which sources are missing, and
-- what the recipe of a target is.  It never touches the file system.  The
-- driver supplies the variables as a table and the stamps of the files,
-- and it runs the recipes.

module Make
  ( Target, Rules, Deps, Vars, Table, Build
  , noDepends, build, names, targets, needs, recipes, undefined
  , stale, waves, plan, ready, affected, ambiguous, missing
  ) where

import Control.SetFunctions
import Data.List ((\\), nub)

type Target = String

-- The rules of a makefile: rule target inputs = recipe.  Every equation
-- that matches a target is one answer.  An empty recipe is a prerequisite
-- line, as "libgeom.a: plot.o" in a makefile.
type Rules = Target -> [Target] -> String

-- The header edges: depends file = header.  Every equation is one edge.
type Deps = Target -> Target

-- The variables, as the driver read them from the makefile: (NAME, value).
-- A name with two entries has two values.  A name without one is undefined.
type Vars = [(String, String)]

-- The stamps of the files that exist.  A larger stamp is a newer file.  A
-- missing file has no entry.
type Table = [(Target, Int)]

-- A rule as the build holds it: the inputs and the recipe, plain data.
type Rule = ([Target], String)

-- The depends relation of a makefile without one: no file includes a header.
noDepends :: Deps
noDepends _ = failed

-- 1. The build: the rules of every name from the goal down, with the edges
-- and the variables beside them.  The goal comes last, after what it
-- reads.  A name with no rule is a source.  The list seen stops a cycle of
-- rules.  Every question below reads the build and never the makefile.
data Build = Build Deps Vars [(Target, [Rule])]

build :: Rules -> Deps -> Vars -> Target -> Build
build rule deps vars goal =
  Build deps vars (reverse (snd (visit ([], []) goal)))
  where
    visit (seen, done) t
      | t `elem` seen = (seen, done)
      | otherwise     = (seen', (t, rs) : done')
      where rs = rulesOf rule t
            (seen', done') = foldl visit (t : seen, done) (needsOf deps rs)

-- Which rules does a target have?  The relation is asked with the inputs
-- free, and narrowing fills them in: the answers are every equation that
-- matches the target, as plain data.  The rules with a recipe come first,
-- so their inputs lead the merged list, as the rule that make runs does.
rulesOf :: Rules -> Target -> [Rule]
rulesOf rule t = withRecipe rs ++ (rs \\ withRecipe rs)
  where rs = sortValues (set2 candidate rule t)

candidate :: Rules -> Target -> Rule
candidate rule t = (ins, rule t ins) where ins free

withRecipe :: [Rule] -> [Rule]
withRecipe rs = [r | r@(_, recipe) <- rs, not (null recipe)]

-- The names of a build, sources and targets, each after what it reads.
names :: Build -> [Target]
names (Build _ _ db) = map fst db

rules :: Build -> Target -> [Rule]
rules (Build _ _ db) t = maybe [] id (lookup t db)

-- The targets of a build: the names with a rule with a recipe.
targets :: Build -> [Target]
targets b = [t | t <- names b, not (null (withRecipe (rules b t)))]

-- 2. What does a target read?  The inputs of every rule of it, merged as
-- make merges the prerequisite lines of a target, each with the headers it
-- includes, directly or through another header.  A source reads nothing.
needs :: Build -> Target -> [Target]
needs b@(Build deps _ _) t = needsOf deps (rules b t)

needsOf :: Deps -> [Rule] -> [Target]
needsOf deps rs
  | null (withRecipe rs) = []
  | otherwise = nub (concatMap (withHeaders deps []) (nub (concatMap fst rs)))

-- A file and every header behind it: the answers of depends, and theirs.
-- The list seen stops a cycle of includes, as an include guard does.
withHeaders :: Deps -> [Target] -> Target -> [Target]
withHeaders deps seen f
  | f `elem` seen = []
  | otherwise     = f : concatMap (withHeaders deps (f : seen))
                                  (sortValues (set1 deps f))

-- 3. The recipe of a target, expanded.  One value is the normal case.  Two
-- values come from a variable with two values.  No value comes from an
-- undefined variable, or from no rule with a recipe, or from two.
recipes :: Build -> Target -> [String]
recipes b t = sortValues (set2 recipe b t)

recipe :: Build -> Target -> String
recipe b@(Build _ vars _) t = case withRecipe (rules b t) of
  [(ins, template)] -> expand (value vars) t ins (needs b t) template
  _                 -> failed

-- The value of a variable: any entry of the table under its name.
value :: Vars -> String -> String
value vars name = anyOf [v | (n, v) <- vars, n == name]

-- The interpolator: $@ is the target, $< the first input of the rule with
-- the recipe (nothing when the rule has none, as in make), $^ everything
-- the target reads, $(NAME) a variable.  Any other $x stays as written.
-- The catch-all is a guard, not a fourth equation: an equation that also
-- matched $ would be a second answer.
expand :: (String -> String) -> Target -> [Target] -> [Target] -> String
       -> String
expand v t ins all = go
  where
    go [] = []
    go (c:rest) | c == '$'  = dollar rest
                | otherwise = c : go rest
    dollar [] = "$"
    dollar (c:rest)
      | c == '@'  = t ++ go rest
      | c == '<'  = concat (take 1 ins) ++ go rest
      | c == '^'  = unwords all ++ go rest
      | c == '('  = v name ++ go (drop 1 rest')
      | otherwise = '$' : c : go rest
      where (name, rest') = break (== ')') rest

-- The variables that the recipe of a target reads and the table does not
-- define.
undefined :: Build -> Target -> [String]
undefined b@(Build _ vars _) t =
  [ n | n <- nub (concatMap (references . snd) (withRecipe (rules b t)))
      , n `notElem` map fst vars ]

-- The names a recipe reads through $(NAME).
references :: String -> [String]
references [] = []
references (c:rest)
  | c == '$' && take 1 rest == "(" = name : references (drop 1 rest')
  | otherwise                      = references rest
  where (name, rest') = break (== ')') (drop 1 rest)

-- 4. What is stale?  A target is stale when it is missing, when it is older
-- than an input, or when an input is stale.  A source is stale only when it
-- is missing.  The list seen holds the targets on the path from the
-- question to this file, so a cycle of rules ends here.
stale :: Build -> Table -> Target -> Bool
stale b table = staleFrom b table []

staleFrom :: Build -> Table -> [Target] -> Target -> Bool
staleFrom b table seen t
  | t `elem` seen = False
  | otherwise     = case lookup t table of
      Nothing -> True
      Just s  -> any (\i -> staleFrom b table (t : seen) i
                              || maybe False (s <) (lookup i table))
                     (needs b t)

-- 5. What to build, and in which order?  The stale targets in waves: a wave
-- holds the stale targets whose stale inputs are all in earlier waves.  A
-- cycle leaves targets that never enter a wave.  The guard fails then, and
-- the plan has no value.
waves :: Build -> Table -> [[Target]]
waves b table = layers b [t | t <- targets b, stale b table t]

layers :: Build -> [Target] -> [[Target]]
layers _ []      = []
layers b pending | not (null wave) = wave : layers b (pending \\ wave)
  where wave = [t | t <- pending, all (`notElem` pending) (needs b t)]

-- The plan: every stale target in dependency order, with what it reads and
-- its recipe.
plan :: Build -> Table -> [(Target, [Target], String)]
plan b table = [(t, needs b t, recipe b t) | t <- concat (waves b table)]

-- 6. What can run now?  The stale targets whose inputs are all up to date.
ready :: Build -> Table -> [Target]
ready b table =
  [t | t <- targets b, stale b table t, not (any (stale b table) (needs b t))]

-- 7. What does a change touch?  The relation of 2 read backwards: the
-- target is the unknown, drawn from the targets of the build, and the
-- guard asks whether it reads the file.  Each answer is one value.
affected :: Build -> Target -> Target
affected b f | reads b t f = t
  where t = anyOf (targets b)

reads :: Build -> Target -> Target -> Bool
reads b = readsFrom b []

readsFrom :: Build -> [Target] -> Target -> Target -> Bool
readsFrom b seen t f
  | t `elem` seen = False
  | otherwise     = f `elem` ins || any (\i -> readsFrom b (t : seen) i f) ins
  where ins = needs b t

-- 8. Which targets do two rules claim?  Every rule with a recipe of every
-- target that has more than one, with the recipe as written.
ambiguous :: Build -> [(Target, [Target], String)]
ambiguous b =
  concat [ [(t, ins, template) | (ins, template) <- claims]
         | t <- targets b, let claims = withRecipe (rules b t)
         , length claims > 1 ]

-- 9. Which sources are missing?  A source is a name without a recipe, and
-- a missing one has no stamp, so nothing can make it.  Each entry names the
-- source and the targets that read it.
missing :: Build -> Table -> [(Target, [Target])]
missing b table =
  [ (s, [t | t <- targets b, s `elem` needs b t])
  | s <- names b, s `notElem` targets b, s `notElem` map fst table ]
