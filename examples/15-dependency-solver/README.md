# A package dependency solver

An index lists the versions of every package with their requirements; a
requirement names a package and a range of its versions.  A plan picks one
version for every package that the roots reach, and it is consistent when
each pick meets every requirement of that package which the plan reaches.
This example writes that sentence down as a Curry function and lets the
runtime find the plans.  There is no loop over candidates, no backtracking
code and no search state.

## The relation

`solveFrom` keeps the demands still to meet, in order, and the versions
chosen so far:

```curry
solveFrom _   _      _    []                 plan = plan
solveFrom idx yanked lock ((p, r) : pending) plan =
  case lookup p plan of
    Just v  -> if inRange r v then solveFrom idx yanked lock pending plan
                              else failed
    Nothing -> solveFrom idx yanked lock (requires idx (p, v) ++ pending)
                                         (plan ++ [(p, v)])
  where
    v = anyOf (candidates idx yanked lock (p, r))
```

A demand on a package already in the plan is a test: the chosen version
meets it, or the branch fails there and then.  A demand on a new package is
a choice: `anyOf` picks one of its candidates, and the requirements of that
version join the queue.  `anyOf []` fails, so a package without a candidate
ends the branch too.  Every value of `solve` is a consistent plan of the
roots, and a branch that goes wrong dies at its first violated demand,
before it builds the rest of the plan.

`candidates` is the policy: the version of the lockfile first, then the
others newest first, and a yanked version only when the lockfile names it or
the range pins it, which is pip's rule.  Sprite's search is fair rather than
depth-first, so the first plan it finds is not always the one a depth-first
resolver would return.  `preferred` pins that plan: at each choice it takes
the first candidate that still leaves a plan, asking a set function whether
the search below the candidate has a value.

Failure is the absence of a value, and the same relation explains it.
`conflict` runs the search with the requirer beside every demand and returns
the first violation of each failing branch, and `solvable`, the set function
of `solve` under `notEmpty`, answers whether a plan exists for an index with
one requirement removed.  Together they say which requirements break the
plan.

## From Python

The index, the yank list, the lockfile and the roots are Python lists and
tuples.  One call hands them to Curry, which converts each by the type of
its parameter, and the plan comes back as a list of pairs:

```python
plan = next(curry.eval(Deps.preferred(INDEX, yanked, lock, roots)), None)
# [('app', 1), ('web', 3), ('http', 2), ('db', 1)]
```

`preferred` is deterministic, so it has one value or none, and `None` means
that no plan exists.  The driver `go.py` prints the plan as a lockfile in
TOML, reads a lockfile back, and when there is no plan asks `conflict` and
`solvable` and prints the answers as sentences:

```
% python go.py app=2
roots: app 2
no plan
a plan exists without any one of these requirements:
  app 2 needs web 3
  app 2 needs db 2
  web 3 needs http 2
  db 2 needs http 1
```

Curry decides, Python asks.  The question, the files and the exit status
belong to the driver.

## Running it

`./run` resolves the roots of the index, a root without a plan, a yanked
version, a lockfile, two roots whose plans do not agree, an unknown root and
a version that no entry has.  `expected.out` records the output.  To ask
other questions:

```
python go.py --index              # print the index
python go.py app=2                # resolve a root
python go.py --yank web=3 app=1   # with a yanked version
python go.py --lock plan.lock     # prefer the versions of a lockfile
```

## Limits

A version is an `Int` and a range one closed interval; resolvelib and
PubGrub work with version sets, pre-releases and semantic versions, order
the open requirements, and learn from conflicts, none of which this example
does.  Its size is a toy's: a handful of packages, a plan in milliseconds.
The benchmark harness holds a comparison with resolvelib on generated
indexes (`tests/README`, section 9); the fair search pays for its fairness
there, and the preference of `preferred` costs one lookahead per candidate
it tries.  Features and extras, platform conditions, several versions of one
package in one plan, and the sources and hashes of a lockfile are out of
scope.
