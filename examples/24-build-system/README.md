# A makefile in Curry

Make reads a makefile, decides what to build, and runs the commands.  Here
the makefile is a Curry module beside the sources of a small C project,
`project/Makefile.curry`.  Its rules are the equations of a relation, in
make's order: target, inputs, recipe.  A library, `Make.curry`, answers the
questions of make over that relation, and a driver, `make.py`, runs the
recipes.  The point of the example is the relation: a rule written once
answers questions in every direction.

## The makefile

```curry
module Makefile where

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

depends "main.c"   = "shape.h"
depends "main.c"   = "vec.h"
depends "shape.c"  = "shape.h"
depends "shape.h"  = "vec.h"
depends "vec.c"    = "vec.h"
depends "report.c" = "vec.h"
depends "plot.c"   = "shape.h"
```

Read it as a makefile.  `CC = "cc"` is a variable and `goal = "demo"` names
the default goal.  Each `rule` equation is one rule of make: the target, the
list of inputs, and the recipe with make's `$@`, `$<`, `$^` and `$(NAME)`.
The first equation is the pattern rule `%.o: %.c`: `stem` appears in the
target and in the input, so the equation applies to any `X.o` whose input
is `X.c`.  It is a functional pattern, and `stem` is solved, not
substituted.  The guard on the second `libgeom.a` rule is make's `ifdef`.
Each `depends` equation is one include edge.

## Asking the relation

`rule` is a relation, so it can be asked with any argument left unknown.
`Make.curry` asks it the way make reads a makefile, with the inputs free:
which inputs does this target have, and what is its recipe?

```python
import os; os.environ['SPRITE_FRONTEND_WARNINGS'] = '0'   # the rules overlap by design
import curry
curry.path.insert(0, 'project')
from curry.lib import Makefile

def ask(text):
    for answer in curry.solve(curry.parse(text, imports=[Makefile])):
        print(answer)

ask('rule "demo" ins  where ins free')
# {ins=["main.o","report.o","libgeom.a"]} "$(CC) -o $@ $^"
```

The pattern rule answers the same question for an object file:

```python
ask('rule "vec.o" ins  where ins free')
# {ins=["vec.c"]} "$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@"
```

The unknown can itself be a pattern.  This asks for a rule for `main.o`
with a C file among its inputs, and the stem comes back with the answer;
`rule t [x]` would ask for a rule with exactly one input:

```python
ask('rule "main.o" (xs ++ [stem ++ ".c"] ++ ys)  where xs, stem, ys free')
# {xs=[], stem="main", ys=[]} "$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@"
```

A target with two rules gets two answers.  `libgeom.a` gets one here,
because the guard of its second rule fails while `WITH_PLOT` is empty.
`depends` is a function with several values:

```python
ask('depends "main.c"')
# "shape.h"
# "vec.h"
```

## What the library asks

`Make.curry` builds make's database from the goal down, asking `rule t ins`
with `ins` free for every name it meets, and answers over that database:
what a target reads (`needs`, with the headers behind each input), what is
stale, the plan in waves, what can run now, which targets two rules claim,
which sources are missing, and what a change touches.  The last one is the
relation read backwards: the target is the unknown, drawn from the targets
of the build, and the question is whether it reads the file.  The library
never touches the file system; the driver supplies the variables and the
stamps of the files, and it runs the recipes.

## Running it

`./run` builds the project in temporary copies and shows ten situations:
the build from scratch, nothing to do, a touched header with the inverse
query, `DEBUG=1` from the command line, `WITH_PLOT=1` adding a source and a
define, an ambiguous target, a variable defined twice, the compiler as a
choice (`CC = "gcc" ? "clang"`), a cycle of rules, and a missing source.
`expected.out` records the output.  The driver takes make's arguments:

```
python make.py [-f FILE] [-C DIR] [-j N] [-n] [--touch FILE]
               [--affected FILE] [--trace] [GOAL] [NAME=value ...]
```

```
% python make.py -C project --touch shape.h --affected shape.h
affected: demo libgeom.a main.o shape.o
plan: 4 targets
```

Three lints run before the plan, and any answer refuses the build: a
target claimed by two rules with a recipe, a missing source, and a recipe
with two values or none (a variable defined twice, or undefined).  GNU
make takes the last recipe and the last assignment in silence; here two
equations are two answers, and the lint names them.

## Limits

The project is a toy by design.  Make's `+=`, `?=`, target-specific
variables, `.PHONY`, order-only prerequisites, `$(wildcard)`, VPATH and the
search among several pattern rules have no form here, and a recipe runs as
one process without a shell.  A real project would read its header edges
from the dependency output of the compiler and would need those features.
The relations would not change; only the equations would grow.
