module Makefile_ambiguous where

CC = "cc"
AR = "ar"
DEBUG = "0"
WITH_PLOT = ""
CFLAGS = if DEBUG == "1" then "-O0 -g -Wall" else "-O2 -Wall"
CPPFLAGS = if WITH_PLOT /= "" then "-DWITH_PLOT" else ""

goal = "demo"

-- %.o: %.c
rule (stem ++ ".o") [stem ++ ".c"] = "$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@"
-- libgeom.a: vec.o shape.o
rule "libgeom.a" ["vec.o", "shape.o"] = "$(AR) rcs $@ $^"
-- ifdef WITH_PLOT
-- libgeom.a: plot.o
-- endif
rule "libgeom.a" ["plot.o"] | WITH_PLOT /= "" = ""
-- demo: main.o report.o libgeom.a
rule "demo" ["main.o", "report.o", "libgeom.a"] = "$(CC) -o $@ $^"
-- main.o: main.c
rule "main.o" ["main.c"] = "$(CC) -O3 -c $< -o $@"

depends "main.c"   = "shape.h"
depends "main.c"   = "vec.h"
depends "shape.c"  = "shape.h"
depends "shape.h"  = "vec.h"
depends "vec.c"    = "vec.h"
depends "report.c" = "vec.h"
depends "plot.c"   = "shape.h"
