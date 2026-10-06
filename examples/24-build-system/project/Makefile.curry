-- The makefile of the project: four sources, two headers, a static library
-- of two objects, and a program.  A variable of make is a definition here,
-- and a rule of make is an equation of rule.  The driver make.py reads the
-- includes, the stamps and the files; the library Make answers the
-- questions of make over this function.

module Makefile where

import Make

-- The variables.  Make writes CC; Curry keeps an uppercase name for a
-- constructor, so the variables are lowercase here.
cc :: String
cc = "cc"

cflags :: String
cflags = "-O2 -Wall"

ar :: String
ar = "ar"

library :: Target
library = "libgeom.a"

program :: Target
program = "demo"

libobjs, mainobjs :: [Target]
libobjs  = ["vec.o", "shape.o"]
mainobjs = ["main.o", "report.o"]

-- The default goal.
goal :: Target
goal = program

-- The rules.  The first is the pattern rule %.o: %.c of make: the functional
-- pattern stem ++ ".o" matches every object name and binds the stem, and
-- the as-pattern names the target, as $@ does.  The next two name their
-- targets through the variables.  The last is a prerequisite line without
-- a command: main.o also reads shape.h.  The scanner of the driver finds
-- that include as well; the line shows the form.
rule :: Target -> Rule
rule t@(stem ++ ".o") =
  Rule t [stem ++ ".c"]
       (cc ++ " " ++ cflags ++ " -c " ++ stem ++ ".c -o " ++ t)
rule t | t == library =
  Rule t libobjs (ar ++ " rcs " ++ t ++ " " ++ unwords libobjs)
rule t | t == program =
  Rule t ins (cc ++ " -o " ++ t ++ " " ++ unwords ins)
  where ins = mainobjs ++ [library]
rule "main.o" = Rule "main.o" ["shape.h"] ""
