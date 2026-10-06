-- The makefile of the project with the compiler left open: gcc or clang.
-- The compiler is a parameter of the rules, bound once per makefile, so one
-- compiler governs every rule of a plan, and the build has one plan per
-- compiler.  The driver prints both plans with -n and builds with the first
-- compiler on the PATH.

module Makefile_toolchain where

import Make
import Makefile (cflags, library, program, mainobjs)
import qualified Makefile

-- The default goal of the makefile.
goal :: Target
goal = Makefile.goal

-- The compilers that can build the project.
toolchains :: [String]
toolchains = ["gcc", "clang"]

-- The rules, with the compiler as a parameter.  The library rule does not
-- use it and comes from the makefile.
rulesWith :: String -> Target -> Rule
rulesWith cc t@(stem ++ ".o") =
  Rule t [stem ++ ".c"]
       (cc ++ " " ++ cflags ++ " -c " ++ stem ++ ".c -o " ++ t)
rulesWith _  t | t == library = Makefile.rule t
rulesWith cc t | t == program =
  Rule t ins (cc ++ " -o " ++ t ++ " " ++ unwords ins)
  where ins = mainobjs ++ [library]

-- One makefile per compiler.  The README says why the compiler is a list
-- here and not a choice, "gcc" ? "clang".
makefiles :: [(String, Makefile)]
makefiles = [(cc, rulesWith cc) | cc <- toolchains]
