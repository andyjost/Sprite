-- Make: the decisions of make over a makefile written in Curry.
--
-- A makefile is a function from a target to its rule.  Each equation of the
-- function is one rule, and every equation that matches a target is one
-- answer.  This module reads such a function once, from the goal down, into
-- the rules of a build, as make reads a makefile into its database, and it
-- asks the questions of make over them: what a target reads, what is stale,
-- what to build and in which order, what can run now, what a change
-- touches, which targets two rules claim, and which sources are missing.
-- It never touches the file system.  The driver supplies the automatic
-- dependencies that a scanner found and a table of file stamps, and it runs
-- the commands.

module Make
  ( Target, Rule (..), Makefile, Includes, Table, Build
  , rulesOf, build, names, targets, rules, command, inputs
  , stale, waves, plan, ready, affected, ambiguous, missing, rows
  ) where

import Control.SetFunctions
import Data.List ((\\), nub)

type Target = String

-- A rule: the target, its prerequisites, and its command, one line as a
-- makefile writes it.  An empty command is a prerequisite line, as
-- "main.o: shape.h" in a makefile.
data Rule = Rule Target [Target] String
  deriving (Eq, Ord, Show)

-- A makefile: the rule of a target.  Every equation that matches is one
-- answer, so the function is non-deterministic where make has two rules.
type Makefile = Target -> Rule

-- The automatic dependencies: the headers each file includes, as the scanner
-- of the driver found them.  Make reads them from the .d files that the
-- compiler writes.
type Includes = [(Target, [Target])]

-- The stamps of the files that exist.  A larger stamp is a newer file.  A
-- missing file has no entry.
type Table = [(Target, Int)]

-- 1. Which rules does a target have?  The set function collects every
-- answer of the makefile as a list of plain data.  No rule means a source.
-- Two rules with commands are the ambiguity of 8.
--
-- Everything else reads the rules through this list.  A name that a
-- functional pattern produced carries its narrowing, and every later
-- comparison of that name pays for it again (#86): read from the makefile
-- directly, a plan over six targets took 10 s; read through the set
-- function, whose values are plain data, 0.01 s.
rulesOf :: Makefile -> Target -> [Rule]
rulesOf mk t = sortValues (set1 mk t)

-- 2. The build: the rules of every name from the goal down, and the
-- automatic dependencies.  build reads the makefile once, through rulesOf:
-- the goal, then what the goal reads, and so on.  A name comes after what it
-- reads, a name with no rule is a source, and the list seen stops a cycle of
-- rules.  The questions below read the build and never the makefile, as the
-- questions of make read its database (make -p prints it).
data Build = Build Includes [(Target, [Rule])]

build :: Makefile -> Includes -> Target -> Build
build mk inc goal = Build inc (reverse (snd (visit ([], []) goal)))
  where
    visit (seen, done) t
      | t `elem` seen = (seen, done)
      | otherwise     = (seen', (t, rs) : done')
      where rs = rulesOf mk t
            (seen', done') = foldl visit (t : seen, done) (inputsOf inc rs)

-- The names of a build, in the order of build: sources and targets.
names :: Build -> [Target]
names (Build _ db) = map fst db

-- The rules of a name of the build.
rules :: Build -> Target -> [Rule]
rules (Build _ db) t = maybe [] id (lookup t db)

-- A target is a name with a command.  A name without one is a source: the
-- driver does not build it, and it reads nothing.
targets :: Build -> [Target]
targets b = [t | t <- names b, not (null (withCommand (rules b t)))]

withCommand :: [Rule] -> [Rule]
withCommand rs = [r | r@(Rule _ _ cmd) <- rs, not (null cmd)]

-- The command of a target: the line of its rule with a command.  Two such
-- rules are the ambiguity of 8, which the driver reports before any plan.
command :: Build -> Target -> String
command b t = case withCommand (rules b t) of
  Rule _ _ cmd : _ -> cmd
  []               -> ""

-- 3. What does a target read?  The prerequisites of every rule of it,
-- merged as make merges the prerequisite lines of a target, each with the
-- headers it includes, directly or through another header.  A source reads
-- nothing.
inputs :: Build -> Target -> [Target]
inputs b@(Build inc _) t = inputsOf inc (rules b t)

inputsOf :: Includes -> [Rule] -> [Target]
inputsOf inc rs
  | null (withCommand rs) = []
  | otherwise             = nub (concatMap (withIncludes inc []) declared)
  where declared = nub (concat [ins | Rule _ ins _ <- rs])

-- A file and every header it includes.  The list seen stops a cycle of
-- includes, as an include guard does.
withIncludes :: Includes -> [Target] -> Target -> [Target]
withIncludes inc seen f
  | f `elem` seen = []
  | otherwise     = f : concatMap (withIncludes inc (f : seen)) headers
  where headers = maybe [] id (lookup f inc)

-- 4. What is stale?  A target is stale when it is missing, when it is older
-- than an input, or when an input is stale.  A source is stale only when it
-- is missing.  The list seen holds the targets on the path from the question
-- to this file: a target on its own path reads nothing more, so a cycle of
-- rules ends here and fails in layers.
stale :: Build -> Table -> Target -> Bool
stale b table = staleFrom b table []

staleFrom :: Build -> Table -> [Target] -> Target -> Bool
staleFrom b table seen t
  | t `elem` seen = False
  | otherwise     = case lookup t table of
      Nothing -> True
      Just s  -> any (\i -> staleFrom b table (t : seen) i
                              || maybe False (s <) (lookup i table))
                     (inputs b t)

-- 5. What to build, and in which order?  The stale targets in waves: a wave
-- holds the stale targets whose stale inputs are all in earlier waves, so
-- the targets of one wave can run at once.  A cycle leaves targets that
-- never enter a wave.  The guard fails then, and the plan has no value.
waves :: Build -> Table -> [[Target]]
waves b table = layers b [t | t <- targets b, stale b table t]

layers :: Build -> [Target] -> [[Target]]
layers _ []      = []
layers b pending | not (null wave) = wave : layers b (pending \\ wave)
  where wave = [t | t <- pending, all (`notElem` pending) (inputs b t)]

-- The plan: every stale target in dependency order, with what it reads and
-- its command.
plan :: Build -> Table -> [Rule]
plan b table =
  [Rule t (inputs b t) (command b t) | t <- concat (waves b table)]

-- 6. What can run now?  The stale targets whose inputs are all up to date.
-- The driver runs them at once, records the new stamps, and asks again.
ready :: Build -> Table -> [Target]
ready b table =
  [t | t <- targets b, stale b table t, not (any (stale b table) (inputs b t))]

-- 7. What does a change touch?  The relation of 3 read backwards: the target
-- is the unknown, drawn from the targets of the build, and the guard asks
-- whether it reads the file, directly or through another target.  Each
-- answer is one value.
affected :: Build -> Target -> Target
affected b f | reads b t f = t
  where t = anyOf (targets b)

reads :: Build -> Target -> Target -> Bool
reads b = readsFrom b []

-- The list seen stops a cycle of rules, as in staleFrom.
readsFrom :: Build -> [Target] -> Target -> Target -> Bool
readsFrom b seen t f
  | t `elem` seen = False
  | otherwise     = f `elem` ins || any (\i -> readsFrom b (t : seen) i f) ins
  where ins = inputs b t

-- 8. Which targets do two rules claim?  The rules with a command of every
-- target of the build that has more than one.  Make picks one of them by a
-- tie-break rule you have to remember.  Here the driver reports them and
-- refuses to build.
ambiguous :: Build -> [Rule]
ambiguous b = concat [twoOrMore (withCommand (rules b t)) | t <- targets b]

twoOrMore :: [a] -> [a]
twoOrMore xs = if length xs > 1 then xs else []

-- 9. Which sources are missing?  A source is a name without a command, and
-- a missing one has no stamp, so nothing can make it.  Make stops before it
-- builds: "No rule to make target 'vec.c', needed by 'vec.o'".  Each entry
-- names the source and the targets that read it directly.
missing :: Build -> Table -> [(Target, [Target])]
missing b table =
  [ (s, [t | t <- targets b, s `elem` inputs b t])
  | s <- names b, s `notElem` targets b, s `notElem` map fst table ]

-- The fields of rules as tuples, for the driver.  The converter of Sprite
-- turns a tuple of Strings and lists of Strings into Python data; a value of
-- a data type of this module stays a Curry node.
rows :: [Rule] -> [(Target, [Target], String)]
rows rs = [(t, ins, cmd) | Rule t ins cmd <- rs]
