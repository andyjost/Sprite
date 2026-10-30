# Choices, sharing, functions

This is the Python companion to 00-run-curry-programs.  Choice.curry has
coin = 0 ? 1, inc and a function returning an adder.  Python's
curry.choice(1, 2) builds a choice without parsing Curry text.

Holding t = C.coin and using t twice shares one computation: t + t has
values 0 and 2 and prints "let x1 = coin in x1 + x1".  Two reads of C.coin
are independent: their sum has three distinct values, 0, 1 and 2 (1 occurs
twice in the four answers).  The script uses set only for that comparison.
Arithmetic on terms builds Curry computations; \_\_choice_\_ is the explicit
choice hook available on ordinary Python.  The script sorts answers where
the scheduler's order is immaterial.

let/ref ties a cycle, "let a = 1 : a in a".  take 5 observes a finite prefix
lazily in Curry; converting the whole infinite list to Python would not
finish.  map receives C.inc as a function argument.  Evaluating adder 10
returns a callable curry.Function, which Python applies in a later goal.

Run "make stage" at the repository root, then "./run" here.  expected.out
records the output; all observations are finite.  Continue with
08-permutation-sort for encapsulated search.  The guide's logic-choices
section covers sharing and cycles; logic-answers covers named variables
in 06-variables.
