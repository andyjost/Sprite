# A makefile in Curry

Make reads a makefile, decides what to build and runs the commands.  Here
the makefile is a Curry module beside the sources of a small C project,
`project/Makefile.curry`.  Its rules are the equations of a relation, in
make's order: target, prerequisites, recipe.  The lesson is the relation:
a rule written once answers questions in every direction, and Python asks
them through the API.  A short driver, `minimake.py`, builds the project
in a few lines of Python.  The full driver, `make.py`, adds make's
arguments, three lints and a library, `Make.curry`, that asks the
questions in Curry.

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
the default goal.  Each `rule` equation is one rule of make: the target,
the list of prerequisites and the recipe with make's `$@`, `$<`, `$^` and
`$(NAME)`.  The first equation is the pattern rule `%.o: %.c`: `stem`
appears in the target and in the prerequisite, so the equation applies to
any `X.o` whose prerequisite is `X.c`.  It is a functional pattern, and
`stem` is solved, not substituted.  The guard on the second `libgeom.a`
rule is make's `ifdef`.  Each `depends` equation is one include edge.

## Asking the relation

`rule` is a relation, so it can be asked with any argument left unknown.
Make asks of a target: which prerequisites does it have, and what is its
recipe?  In Python the unknown is a free variable, the question is a call
of `rule` over it and `curry.solve` answers with the value of the call and
the bindings of the variable:

```python
import os; os.environ['SPRITE_FRONTEND_WARNINGS'] = '0'   # the rules overlap by design
import curry
curry.path.insert(0, 'project')
from curry.lib import Makefile

prereqs = curry.free('prereqs')
for recipe, bindings in curry.solve(Makefile.rule('demo', prereqs)):
    print(bindings[prereqs], recipe)
# ['main.o', 'report.o', 'libgeom.a'] $(CC) -o $@ $^
```

The bindings map each named variable to its value as Python data, a list
of strings here, under the variable itself or its name (`bindings['prereqs']`).
The pattern rule answers the same question for an object file, and
`stem` is solved on the way:

```python
prereqs = curry.free('prereqs')
for recipe, bindings in curry.solve(Makefile.rule('vec.o', prereqs)):
    print(bindings[prereqs], recipe)
# ['vec.c'] $(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

The recipe is make's template.  `$@` stands for the target and `$<` for
the first prerequisite, so the answer fills both:

```python
print(recipe.replace('$@', 'vec.o').replace('$<', bindings[prereqs][0]))
# $(CC) $(CPPFLAGS) $(CFLAGS) -c vec.c -o vec.o
```

`$(CC)` is a variable of the makefile: a Curry definition, evaluated like
any other value.  `CFLAGS` is a conditional definition, and its value
follows `DEBUG`:

```python
print(next(curry.eval(Makefile.CC)), next(curry.eval(Makefile.CFLAGS)))
# cc -O2 -Wall
```

A target with two rules gets two answers.  `libgeom.a` gets one here,
because the guard of its second rule fails while `WITH_PLOT` is empty.  A
source gets none: no equation matches `vec.c`.  A goal can also be Curry
text, and then the unknown can itself be a pattern.  This asks for a rule
for `main.o` with a C file among its prerequisites, and the stem comes back
with the answer:

```python
goal = curry.parse('rule "main.o" (xs ++ [stem ++ ".c"] ++ ys)  where xs, stem, ys free', imports=[Makefile])
for recipe, bindings in curry.solve(goal):
    print(bindings)
# {xs=[], stem="main", ys=[]}
```

## The headers, as a set

`depends` has one equation per include edge, which is the convenient way
to write them, and the question "which headers does `main.c` include?"
wants every value at once.  Python collects the values of the call:

```python
print(sorted(curry.eval(Makefile.depends('main.c'))))
# ['shape.h', 'vec.h']
```

In Curry the same question is a set function: `set1 depends "main.c"` is
the set of values of `depends "main.c"`, and `sortValues` lists them.  Set
functions are a Curry library, and Python can call them as well:

```python
SetFunctions = curry.import_('Control.SetFunctions')
headers = SetFunctions.sortValues(SetFunctions.set1(Makefile.depends, 'main.c'))
print(next(curry.eval(headers)))
# ['shape.h', 'vec.h']
```

`Make.curry` asks it this way, in `withHeaders`, because the set of one
file's headers feeds the next question in Curry.  From Python, `curry.eval`
gives the values one by one, so no set function is needed there.

## Make in a few lines of Python

Curry solves the rules; Python owns the files, the clock and the
processes.  `minimake.py` is make in seven functions.  The rules of a
target are the answers above, as data:

```python
import concurrent.futures, re, shlex, subprocess

def rules(target):
    prereqs = curry.free('prereqs')
    return [(bindings[prereqs], recipe)
            for recipe, bindings in curry.solve(Makefile.rule(target, prereqs))]
```

What a target reads is the prerequisites of its rules and every header
behind them, through the include edges.  A source has no rule and reads
nothing:

```python
def headers(source):
    found = set(curry.eval(Makefile.depends(source)))
    return found.union(*map(headers, found))

def needs(target):
    prereqs = [p for ps, recipe in rules(target) for p in ps]
    return prereqs + sorted(set().union(*map(headers, prereqs)))
```

The command of a target is its recipe expanded: `$(NAME)` from the
makefile, `$@`, `$<` and `$^` from the answer:

```python
def command(target):
    [(prereqs, recipe)] = rules(target)
    for name in re.findall(r'\$\((\w+)\)', recipe):
        recipe = recipe.replace('$(%s)' % name, next(curry.eval(getattr(Makefile, name))))
    return (recipe.replace('$@', target).replace('$<', prereqs[0])
                  .replace('$^', ' '.join(needs(target))))
```

Whether a target is stale is a question of the clock, so Python answers
it.  A target is stale when it is missing, when it is older than a file it
reads or when it reads a stale target:

```python
def stale(name):
    if not os.path.exists(name):
        return True
    return any(stale(f) or os.path.getmtime(f) > os.path.getmtime(name)
               for f in needs(name))
```

The build runs the stale targets from the goal down, wave by wave.  A wave
holds the pending targets that read no pending target, and its commands
run at once in a pool of threads:

```python
def names(target):
    return {target}.union(*map(names, needs(target)))

def make(goal, jobs=4):
    pending = [t for t in sorted(names(goal)) if rules(t) and stale(t)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        while pending:
            wave = [t for t in pending if not any(f in pending for f in needs(t))]
            lines = [command(t) for t in wave]
            print(*lines, sep='\n', flush=True)
            list(pool.map(lambda line: subprocess.run(shlex.split(line), check=True), lines))
            pending = [t for t in pending if t not in wave]
```

That is the whole driver.  `minimake.py` takes the project directory and
the goal on its command line, and a second run finds nothing stale:

```
% python minimake.py project
cc  -O2 -Wall -c main.c -o main.o
cc  -O2 -Wall -c report.c -o report.o
cc  -O2 -Wall -c shape.c -o shape.o
cc  -O2 -Wall -c vec.c -o vec.o
ar rcs libgeom.a vec.o shape.o
cc -o demo main.o report.o libgeom.a
% python minimake.py project
demo is up to date
```

## What the library asks

`Make.curry` asks the same questions in Curry.  It builds make's database
from the goal down, asking `rule t prereqs` with `prereqs` free for every
name it meets, as a set of answers, and it answers over that database:
what a target reads (`needs`, with the headers behind each prerequisite),
what is stale, the plan in waves, what can run now, which targets two
rules claim, which sources are missing and what a change touches.  The
last one is the relation read backwards: the target is the unknown, drawn
from the targets of the build, and the question is whether it reads the
file.  The library never touches the file system.  The driver supplies the
variables and the stamps of the files, and it runs the recipes.

## Running it

`./run` builds the project in temporary copies.  It shows the short driver
first, then ten situations of `make.py`: the build from scratch, nothing
to do, a touched header with the inverse query, `DEBUG=1` from the command
line, `WITH_PLOT=1` adding a source and a define, an ambiguous target, a
variable defined twice, the compiler as a choice (`CC = "gcc" ? "clang"`),
a cycle of rules and a missing source.  `expected.out` records the output.
The driver takes make's arguments:

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
target claimed by two rules with a recipe, a missing source and a recipe
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
