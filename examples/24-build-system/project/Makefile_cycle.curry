-- The makefile of the project with one rule more: the program writes the
-- header shape.h, which its own objects read.  The rules have a cycle, so
-- the plan has no value, and the driver reports the failure.  Make reports
-- "Circular shape.h <- demo dependency dropped" and builds on.

module Makefile_cycle where

import Make
import qualified Makefile

-- The default goal of the makefile.
goal :: Target
goal = Makefile.goal

-- Every rule of the makefile, and one that closes the cycle.
rule :: Target -> Rule
rule t = Makefile.rule t
rule "shape.h" = Rule "shape.h" ["demo"] "./demo --emit-header shape.h"
