# What a change rebuilds

You edit `shape.h`. What does that rebuild? A build rule names a target and
the files it is made from, so the rules say what `demo` needs. Your question
runs the other way: which targets are made from `shape.h`, directly or
through other targets? This lesson keeps the six rules of a small C build in
Curry, in the makefile's direction, and asks the reverse question from
Python with one call.

```python
import curry
curry.path.insert(0, '.')          # Curry's sys.path, which lacks the cwd
from curry.lib import Build        # Build.curry, shown below

# the same rules, asked backwards; two paths reach demo, and set keeps one
targets = set(curry.eval(Build.touches('shape.h')))
print('touch shape.h: rebuild', *sorted(targets))
# touch shape.h: rebuild demo libgeom.a main.o shape.o
```

The reverse question is the last line of `Build.curry`,
`touches (depends t) = t`: the pattern is a call. The runtime tries `t`
against the six targets of the rules, and the ones whose forward walk
`depends` reaches `shape.h` are the values. A Curry function may have
several values, the same ones on every run, which Curry calls
nondeterminism. `touches "shape.h"` has five, one per path from a target to
the file, and `set` keeps one of each.

Make answers your question with a touch and a dry run over timestamps.
Python needs a dict of the rules beside the makefile and a six-line loop
that tries every target forward. Here the rules have one copy and the loop
is gone.

To run it, `pip install --pre curry` brings the runtime and the Curry front
end; Sprite is in alpha. The build runs `cc` and `ar`; the import needs no C
or C++ compiler. Run the blocks in this directory. The first import
translates `Build.curry` into `.curry/` beside it, a directory for your
ignore file.

## The rules

```curry
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
```

`needs` is the makefile: each equation names a target and the files it is
made from, and a source has no equation. `depends` walks forward, one value
per path: `depends "demo"` has fifteen, one per edge of this build, and
`depends "main.c"` has none, because no equation of `needs` matches a
source. A call with no value is an empty result: `curry.eval` yields nothing
and raises no exception.

`touches` takes the file and solves for the target. Its pattern is the call
`depends t` with `t` unknown, and only the patterns of `needs` bind `t`: six
string literals, so the runtime tries six values of `t` and nothing else.
The search ends because the rules have no cycle.

`curry.eval` returns an iterator over the values of a call, and `.one()`
takes the value when there is exactly one and raises otherwise. Forward, the
rules answer make's questions:

```python
print(curry.eval(Build.needs('demo')).one())   # exactly one, a list of str
# ['main.o', 'report.o', 'libgeom.a']
print(len(list(curry.eval(Build.depends('demo')))))   # one value per edge
# 15
print(sorted(curry.eval(Build.touches('shape.h'))))   # demo once per path
# ['demo', 'demo', 'libgeom.a', 'main.o', 'shape.o']
```

## The build

Curry holds the rules and Python owns the files. The driver, `build.py`,
builds `demo` or says what a change rebuilds:

```python
# build.py: builds demo in project/ from the rules of Build.curry, or says
# what a changed file rebuilds.
#   python build.py            build demo
#   python build.py shape.h    the targets a change to shape.h rebuilds
import os, subprocess, sys
import curry
here = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, here)         # Curry's sys.path, which lacks the cwd
from curry.lib import Build        # Build.curry, the rules
os.chdir(os.path.join(here, 'project'))   # the C files; commands run here

def stale(target, inputs):
    return not os.path.exists(target) or any(
        os.path.getmtime(f) > os.path.getmtime(target) for f in inputs)

def build(target):
    # needs has one value for a target and none for a source: the loop is an if
    for inputs in curry.eval(Build.needs(target)):
        for f in inputs:
            build(f)
        if stale(target, inputs):
            command = curry.eval(Build.command(target)).one()
            print(*command, flush=True)
            subprocess.run(command, check=True)

if len(sys.argv) == 1:
    build('demo')
else:
    changed = sys.argv[1]
    if not os.path.exists(changed):
        sys.exit(f'{changed}: no such file')
    # the same rules, asked backwards; two paths reach demo, and set keeps one
    targets = sorted(set(curry.eval(Build.touches(changed))))
    print(f'touch {changed}: rebuild', *(targets or ['nothing']))
```

`build` walks the rules from `demo` down and runs the command of a stale
target after the targets it needs. `needs target` has one value for a target
and none for a source, so the loop over its values is an `if`. The driver
checks that the file exists before it asks: `touches` of a misspelled name
has no value and would answer `rebuild nothing`, like a file no target
reads. `./run` runs the driver in a temporary copy of this directory against
a staged source checkout; `expected.out` is its transcript:

```
% python build.py
cc -c main.c
cc -c report.c
cc -c vec.c
cc -c shape.c
ar rcs libgeom.a vec.o shape.o
cc -o demo main.o report.o libgeom.a
% project/demo
c = (0, 3)
area = 6
% python build.py
% touch project/shape.h
% python build.py shape.h
touch shape.h: rebuild demo libgeom.a main.o shape.o
% python build.py
cc -c main.c
cc -c shape.c
ar rcs libgeom.a vec.o shape.o
cc -o demo main.o report.o libgeom.a
```

## The numbers

`touches 'shape.h'` takes 1.8 ms in Curry and 3 µs as the Python loop over
the same six rules as a dict: `timing.py`, the median of 100 calls after 100
warm calls, interpreted (`jit:off`), on an AMD EPYC Genoa processor, on
2026-11-01. On a generated build of 272 rules and 984 edges, a header one
object includes (three targets) takes 13 ms against 0.35 ms. The header that
all 240 objects include, 720 values over 272 targets, takes 110 ms against
0.11 ms: the Python loop stops at a target's first path, and `touches` finds
every path. The first import of the 272 rules translates the module in
5.4 s; later imports load the saved translation in 0.04 s.
`python build.py shape.h` takes 1.0 s the first time and 0.25 s after. The
default flags compile a function after its hundredth call; one run of
`build.py` calls none that often, so `Build` runs interpreted there too.

## What you did not write

No line of this page walks the graph backwards. `touches` is `depends` with
the known and the unknown exchanged. The search is sound, complete, and
optimal: every value is a target whose walk reaches the file, every such
target is a value, once per path, and no step runs that no value needs. The
clock is the section above. Your project may hold one direction of an
acyclic relation and read it in the other: a symbol table, or an include
graph after its cycles are cut.

[Curry in ten minutes](https://andyjost.github.io/Sprite/CurryInTenMinutes.html)
teaches the Curry this lesson assumes, and the
[Quickstart](https://andyjost.github.io/Sprite/Quickstart.html) has the first
calls. Lesson [15](../15-dependency-solver) solves package dependencies with
no search code of its own, and lesson [26](../26-ir-canonicalization) asks
eight rewrite rules of a small IR for every normal form of an input.

## Limits

This is a toy. The six rules are written by hand where a real build reads
them from `cc -MM`. Make's `$@`, `$<`, pattern rules, variables and phony
targets have no form here, so the commands repeat file names. A command runs
as one process without a shell. `touches` yields a target once per path, so
the count of values is the count of paths. A target with two `needs`
equations has two values, and `build` visits it once per value. If `needs`
had a cycle, `depends` would have no end, and neither would `touches`: check
a graph for cycles before you write it as rules.
