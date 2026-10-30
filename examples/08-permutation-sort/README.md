# Permutation sort: generate, test, collect

`perm` is a nondeterministic function: each value is a permutation.  `sort`
takes a permutation and keeps it only if it is sorted; every other
candidate fails, and failure is not an error, just an alternative that
produces no value.  Set functions collect: `permS xs` is the Values of all
permutations, `sortS xs` the Values of all sorted ones, a multiset, so a
list with equal elements has equal sorted permutations more than once.

In Python a Values is a collection: it has a length, iterates, sorts.  The
last lines show the rule of the capsule: a choice made outside the set
function is not collected inside it, so `sortS (xs ? ys)` has two values,
one Values for each outside alternative.  The queens example (10) is the
same idea at work.

Run "make stage" from the root of the repository first, then "./run"
from this directory.  The file expected.out records the standard output.
