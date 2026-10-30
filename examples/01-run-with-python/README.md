# Hello, both ways

Hello.curry has a greeting, a choice, a failed goal and a division by zero.
go.py sends a Python String into greet and reads a Python String back with
Results.one(), which checks that exactly one answer exists.

The next call uses "with curry.eval(...) as results".  A break keeps the
search at its current position; the remaining answers are read inside the
block, and leaving it closes the search.  list consumes all answers of a
finite search.  Failure is an empty result; one() then raises NoValueError.
The bad goal returns Results at the call and raises DivisionByZeroError
when next advances it.

Three boundary surprises follow, each with its working spelling: a str is
String, so ord needs curry.Char('A'); [1, 2.5] has homogeneous type [Float]
and converts to [1.0, 2.5]; read "5" needs the annotation
curry.term(P.read('5'), type='Int') because Read has no default.

Run "make stage" at the repository root, then "./run" here.  expected.out
records every line, including the caught errors.  The input and all
searches are finite.  Continue with 02-dynamic-code-generation for compile
and parse, or 05-trees for user data.  The guide's results-lifecycle and
typed-errors sections explain the same boundary in more detail.
