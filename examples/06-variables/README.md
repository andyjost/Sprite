# Variables: narrowing and suspension

Two relations in Vars.curry: `last` by a functional pattern, and `split`,
which narrows two free variables to every way of splitting a list.
Both signatures need Data a: the functional pattern and =:= constrain
the element type.  go.py asks the same questions from Python: `curry.free('xs')` is a variable, one
object wherever it appears; `curry.solve` returns an Answer per solution,
with the bindings by name and by variable; an unbound variable stays
itself in an answer.

The second half is residuation.  `x + 1 =:= 3` cannot narrow `x`, because
arithmetic is rigid: the evaluation suspends, and Sprite reports it as a
SuspensionError after the values of the other alternatives.  Put a
generator beside it with `&`, the concurrent conjunction, and the
arithmetic resumes once `x` is bound.  The dunders of a term build the
Prelude's operators: `x + 1` is the term `x + 1`, and `a & b` is `a & b`.

Run "make stage" from the root of the repository first, then "./run"
from this directory.  The file expected.out records the standard output.
