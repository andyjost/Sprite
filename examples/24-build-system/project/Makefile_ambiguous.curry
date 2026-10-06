-- The makefile of the project with one rule more: a second rule with a
-- command for main.o.  The lint of the driver reports the target and the
-- build does not start.  Make would pick one of the two rules by its
-- tie-break order.

module Makefile_ambiguous where

import Make
import Makefile (cc)
import qualified Makefile

-- The default goal of the makefile.
goal :: Target
goal = Makefile.goal

-- Every rule of the makefile, and one more for main.o.  Both equations
-- match main.o, so main.o has two rules with a command.
rule :: Target -> Rule
rule t = Makefile.rule t
rule "main.o" = Rule "main.o" ["main.c"] (cc ++ " -O3 -c main.c -o main.o")
