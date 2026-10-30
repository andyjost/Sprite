# Overload resolution over a model of C++ types

A C++ compiler decides which overload a call picks: a candidate is viable
when every argument converts to its parameter, each conversion has a rank,
and the best viable function beats every other candidate in some argument
and loses in none.  This example writes those rules as Curry rules over an
algebraic model of C++ types, asks them from Python, and then asks the
question a compiler never answers: which argument types would make this
call ambiguous?

It is the second of four examples on one model of C++ types, the shared
modules under `../cxx`: template argument deduction (20), overload
resolution (this one), trait checking (22) and member layout (23).  This
example adds `CxxOverload.curry`: the standard conversion sequences, the
viable candidates of a call, and the best viable function.

## Conversions are rules

`standard` has one rule per conversion of the standard, each with a guard
that names its case:

```curry
standard _ a p | a == p = Exact
standard _ a p | a /= p && qualifies a p = Exact
standard _ a p | promotes a p = Promotion
...
```

In Curry two rules with the same left-hand side are alternatives, not a
chain of fall-throughs.  The guards do not overlap, so a pair of types has
at most one conversion, and a pair that no guard accepts has no value at
all: no `Maybe`, no error code, no `else`.

That absence does the work in `viable`, which picks a candidate and converts
every argument:

```curry
viable h cands args
  | length params == length args = (cand, zipWith (convert h) args params)
  where cand = anyOf cands
        params = snd cand
```

When one argument has no conversion, the value for that candidate fails and
the candidate is gone from the search.  A set function collects what
remains: the viable set of the call, each candidate with the rank of each
argument.  An empty set is "no viable function".  `better` compares two
sequences for the same argument by rank, then by the tie-breakers of the
standard: a pointer conversion that does not go to `bool` beats one that
does, `Derived*` to `Base*` beats `Derived*` to `void*`, and a sequence
without a qualification conversion beats the same sequence with one.

## The question a compiler never answers

Overload resolution maps a call to a result.  A free variable and a bounded
generator run it backwards:

```curry
ambiguousArg n cands
  | t =:= anyType n && (ambiguousCall cands $## t) = t
  where t free
```

`anyType n` is every type of depth at most `n`, one per value; `t` is bound
to each in turn, and the guard keeps the types whose call is ambiguous.  A
set function collects them.

## From Python

The overload sets, the class hierarchy and the calls are Python lists and
tuples built from the constructors of the model, `Overloads` converts them
by the types of its parameters, and every answer comes back as text.  The
driver `go.py` runs four scenarios; `expected.out` records them:

```
(a) overloads f(int), f(long), f(double)
  f(char)   viable: f(int) [promotion], f(long) [conversion], f(double) [conversion]
            result: f(int) [promotion]
  f(int*)   viable: none
            result: no viable function
(b) overloads f(long), f(double)
  f(int)    viable: f(long) [conversion], f(double) [conversion]
            result: ambiguous: f(long), f(double)
(c) class Derived : Base; overloads k(int*), k(int const*), k(void*), k(Base*), k(bool)
  k(Derived*)        result: k(Base*) [conversion]
  k(int*)            result: k(int*) [exact]
(d) the argument types of depth at most 2 that make the call ambiguous for f(long), f(double), f(int const*)
  120 types; after the lvalue transformations, 12: bool, char, signed char, unsigned char, short, ...
```

Scenario (d) tries the 1245 types of depth at most two and finds the 120
that make the call ambiguous.  A compiler that runs Python during
compilation could hand such a model its own types and ask it.

## Limits

The model has no user-defined conversions, no templates, no
argument-dependent lookup, and references and value categories only in the
simple cases: a parameter `T&` or `T&&` has no rule, so a candidate with one
is never viable.  The benchmark harness compares `resultLine` over a
thousand calls with a plain-Python implementation of the same ranking
(`tests/README`, section 9).
