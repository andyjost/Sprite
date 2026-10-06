-- The makefile of the project with the compiler as a choice inside the
-- rules: cc = "gcc" ? "clang".  A nullary definition is a function of no
-- arguments, and every use of it is a new evaluation and a new choice, so
-- every rule that reads cc picks a compiler on its own.  The set function
-- that collects the rules of a target then finds two rules for every target
-- that reads cc, and the lint of the driver reports them.

module Makefile_choice where

import Make
import Makefile (cflags, library, program, mainobjs)
import qualified Makefile

-- The default goal of the makefile.
goal :: Target
goal = Makefile.goal

cc :: String
cc = "gcc" ? "clang"

rule :: Target -> Rule
rule t@(stem ++ ".o") =
  Rule t [stem ++ ".c"]
       (cc ++ " " ++ cflags ++ " -c " ++ stem ++ ".c -o " ++ t)
rule t | t == library = Makefile.rule t
rule t | t == program = Rule t ins (cc ++ " -o " ++ t ++ " " ++ unwords ins)
  where ins = mainobjs ++ [library]
