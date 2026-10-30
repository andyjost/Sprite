<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup.svg" width="440">
  </picture>
</p>

Sprite, the `curry` package on PyPI, is an implementation of the multi-paradigm
programming language [Curry](https://www.curry-lang.org/) exposed to Python. It
seamlessly integrates features of functional programming (algebraic data types,
pattern matching, strong typing, type inference, lazy evaluation) and logic
programming (nondeterminism, logic variables, search) into your Python project
without adding heavy dependencies. You state what a desired value has to satisfy
and leave the search to Sprite. As a result, many programs are trivial to
construct and obviously correct. Sprite's evaluation strategy, the Fair Scheme,
is proved sound, complete, and optimal, meaning it finds exactly the values of
any expression, and it executes only the steps needed to produce them.

Curry imports directly into Python. Your project uses it at whatever granularity
it chooses, freely mixing imperative, functional, and logic styles. In other
words, you always get to use the best tool exactly where it makes sense.

Sprite is in alpha. Install it with `pip install --pre curry`. Try it and [tell
us what breaks](https://github.com/andyjost/Sprite/issues).

## Getting started

The following Curry module defines a small type of Boolean formulas along with
a printer.

```haskell
-- Logic.curry
data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

render :: Formula -> String
render T = "T"
render F = "F"
render (Not p) = "!" ++ render p
render (And p q) = "(" ++ render p ++ " & " ++ render q ++ ")"
render (Or p q) = "(" ++ render p ++ " | " ++ render q ++ ")"
```

So far this is ordinary Haskell code. Save it next to your Python code, then
import it, construct a formula, and render it as a string:

```python
import curry
curry.path.insert(0, '.')          # Curry's sys.path
from curry.lib import Logic as L   # compiles and imports ./Logic.curry

formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
goal = L.render(formula)
curry.eval(goal).one()             # the one value: '((T | F) & !F)'
```

The import compiles the Curry module to native code and loads it. The
constructors of `Formula` appear as `L.T`, `L.And`, and so on.
`L.render(formula)` builds an expression without running it, `curry.eval`
evaluates it, and Sprite converts the result to a Python string.

## Nondeterminism

Curry is nondeterministic, meaning expressions may have any number of values.
This fact undergirds all of Curry's logic features. By writing a rule containing
a function call in its pattern (a *functional pattern*, something not possible
in Haskell), you can define a search. Sprite finds all the solutions. Here,
`split` generates all ways of splitting a list into two parts:

```haskell
-- Lists.curry
split (xs ++ ys) = (xs, ys)
```

This matches any time the argument can be split into `xs` and `ys` such that
their concatenation forms the original list. To evaluate the function and
iterate through the results, write:

```python
from curry.lib import Lists

for xs, ys in curry.eval(Lists.split([1, 2, 3])):
    print(xs, ys)
# [] [1, 2, 3]
# [1] [2, 3]
# [1, 2] [3]
# [1, 2, 3] []
```

`curry.eval` returns an iterator over the results. Use `one` (as in the
previous example) when one result is expected, or `next` to take the first of
possibly several values.

## Running a function backwards

We can use this idea to build a parser from `render`: write the call of
`render` as the pattern and leave the formula unknown. That's the whole
parser, one rule added to `Logic.curry`:

```haskell
-- Logic.curry, continued
parse :: String -> Formula
parse (render p) = p
```

`p` is a logic variable. To match the pattern, Sprite solves for the formula
whose rendering is the given string, and that formula is the answer:

```python
tree = curry.eval(L.parse('((T | F) & !F)')).one()
print(tree)                            # And (Or T F) (Not F)
tree == formula                        # True
```

The five rules of `render` serve as the grammar. There's no second copy of the
grammar to keep in step, and the parser can't disagree with the printer,
because it is the printer. This is where Curry excels: the specification is
the program. There's nothing more to write, and nothing more to get wrong.

The same trick applies wherever you have one direction of a relation and want
the other. The repository has small [examples](https://andyjost.github.io/Sprite/Examples.html) of a
[build system](https://github.com/andyjost/Sprite/tree/master/examples/24-build-system)
whose pattern rules run both ways, a
[package dependency solver](https://github.com/andyjost/Sprite/tree/master/examples/15-dependency-solver)
with no search code, and
[C++ overload resolution](https://github.com/andyjost/Sprite/tree/master/examples/21-cxx-types-overloads)
that can also tell you which argument types pick a given overload. We think
compiler IR, where passes are rewrite rules over a term graph, is another
natural fit.

## Installation

```sh
pip install --pre curry
```

The `--pre` flag is needed while Sprite is in alpha. If you'd rather not touch
your Python at all, a one-line installer brings its own and installs Sprite
under your home directory:

```sh
curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh
```

The source distribution builds with pip, a C++ compiler and the Python
development headers; pip installs CMake and Ninja in its isolated build
environment. The Curry front end is needed at run time for new Curry text;
PAKCS, Prolog and Haskell are not.

## Documentation

The [documentation](https://andyjost.github.io/Sprite/) has a
[Quickstart](https://andyjost.github.io/Sprite/Quickstart.html), a
[Curry primer](https://andyjost.github.io/Sprite/CurryPrimer/index.html) for
Python programmers, the [Python API](https://andyjost.github.io/Sprite/PythonAPI/index.html),
the [REPL](https://andyjost.github.io/Sprite/REPL.html), and a
[Status](https://andyjost.github.io/Sprite/Status.html) page that says what
works today. The twenty-six [examples](https://andyjost.github.io/Sprite/Examples.html)
each come with a README, a run script, and recorded output. The Fair Scheme
and its proofs are written up in a
[dissertation](https://doi.org/10.15760/etd.3564)
and a shorter [paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf).

Questions and bug reports go to the
[issue tracker](https://github.com/andyjost/Sprite/issues). The source is at
[github.com/andyjost/Sprite](https://github.com/andyjost/Sprite).

## Contributing

Bug reports with a reproducer are the most useful contribution right now, and
we welcome them on the [issue tracker](https://github.com/andyjost/Sprite/issues).
The semantics of the runtime are delicate, so we don't take unsolicited pull
requests; if you want to work on something, open an issue first and we'll
talk. [CONTRIBUTING.md](https://github.com/andyjost/Sprite/blob/master/CONTRIBUTING.md) has the setup and the conventions.

## License

[BSD 3-Clause](https://github.com/andyjost/Sprite/blob/master/LICENSE). The
Curry library under `curry/lib` is the base library of PAKCS and carries its
license and a notice of its origin; the distribution includes the notices for
its vendored Curry library and pybind11.

## About the name

The name `curry` was held from 2009 by Malthe Borch for his package of partial
application; he agreed to its transfer, for which we thank him. Version
0.9.0a1 was published as `currylang` on 2026-10-24; from 0.9.0a2 the
distribution is `curry`.
