-- Build.curry: the build of demo as six rules, their commands and two
-- questions.
module Build where

-- The rules, written once: what each target is made from, as cc -MM lists
-- it.  A source has no rule.
needs :: String -> [String]
needs "demo"      = ["main.o", "report.o", "libgeom.a"]
needs "libgeom.a" = ["vec.o", "shape.o"]
needs "main.o"    = ["main.c", "shape.h", "vec.h"]
needs "report.o"  = ["report.c", "vec.h"]
needs "shape.o"   = ["shape.c", "shape.h", "vec.h"]
needs "vec.o"     = ["vec.c", "vec.h"]

-- The command that makes each target.
command :: String -> [String]
command "demo"      = ["cc", "-o", "demo", "main.o", "report.o", "libgeom.a"]
command "libgeom.a" = ["ar", "rcs", "libgeom.a", "vec.o", "shape.o"]
command "main.o"    = ["cc", "-c", "main.c"]
command "report.o"  = ["cc", "-c", "report.c"]
command "shape.o"   = ["cc", "-c", "shape.c"]
command "vec.o"     = ["cc", "-c", "vec.c"]

-- Everything a target depends on: a file it needs, or anything that file
-- depends on.  The list comprehension reads as Python's.  anyOf and ? are
-- from the Prelude, which every module imports: anyOf xs is any element
-- of xs, and a ? b has both values.
depends :: String -> String
depends t = anyOf [f ? depends f | f <- needs t]

-- What a change to a file touches: depends with the known and the unknown
-- exchanged.  The pattern is a call, so the runtime solves for the
-- targets t whose walk reaches the given file.
touches :: String -> String
touches (depends t) = t
