<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/v/curry" alt="PyPI"></a>
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/pyversions/curry" alt="Python versions"></a>
  <a href="https://github.com/andyjost/Sprite/actions/workflows/ci.yml"><img src="https://github.com/andyjost/Sprite/actions/workflows/ci.yml/badge.svg?branch=master&event=push" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/andyjost/Sprite" alt="License"></a>
</p>

Sprite compiles and runs [Curry](https://www.curry-lang.org/), and lets you
call it from Python. Curry is a functional logic programming language. Its
functional half is Haskell's, syntax included: algebraic data types, pattern
matching, type inference, lazy evaluation. Its logic half adds nondeterminism,
logic variables and search: a function may have several results, a value may
be left unknown, and the runtime finds the values that fit by unification. So
you can state what a result has to satisfy and leave the search to the
language. Sprite's evaluation strategy, the Fair Scheme, is proved correct and
optimal: it finds exactly the values of an expression, and it executes only
the steps needed to produce them.

Sprite is in alpha. Try it, and [tell us what breaks](https://github.com/andyjost/Sprite/issues).

## A first module

Here is a Curry module. It defines a small type of Boolean formulas and a
function that prints one.

```curry
-- Logic.curry
data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

render :: Formula -> String
render T = "T"
render F = "F"
render (Not p) = "!" ++ render p
render (And p q) = "(" ++ render p ++ "&" ++ render q ++ ")"
render (Or p q) = "(" ++ render p ++ "|" ++ render q ++ ")"
```

If you've read Haskell, nothing here is new. Save it next to your Python code
and import it:

```python
import curry
curry.path.insert(0, '.')
from curry.lib import Logic as L

f = L.And(L.Or(L.T, L.F), L.Not(L.F))
goal = L.render(f)
curry.eval(goal).one()    # '((T|F)&!F)'
```

The constructors of `Formula` are there as `L.T`, `L.And` and so on, and the
result comes back as a Python string. `L.render(f)` builds an expression
without running it; `curry.eval` runs it, and `.one()` returns its value when
there is exactly one. The first import translates and compiles the module;
later imports reuse the result.

We've tried to make Sprite easy to depend on. `pip install` brings two wheels
and nothing else: `curry`, which holds the runtime, the compiled Curry library
and the Python API in about 3 MB, and `curry-frontend`, the Curry front end as
a native executable, between 2.6 and 8.3 MB depending on the platform. There's
no Prolog, no Haskell toolchain and no JVM behind it. Curry code compiles
through C++ to native machine code, and on a machine without a C++ compiler
Sprite interprets the same modules instead. The wheels cover Python 3.11 to
3.15, the free-threaded build included, on Linux (x86-64 and aarch64) and
macOS 15 or newer, and the test suite runs on all of them on every change.
The license is BSD 3-Clause.

## More than one answer

A Curry function can have more than one result for the same input. The `++`
in this pattern is list concatenation, the same `++` as in `render`:

```curry
-- Lists.curry
split (xs ++ ys) = (xs, ys)
```

The rule says: if the argument is some `xs` followed by some `ys`, return the
pair. A list of three can be read that way four times, and Sprite gives you
all of them:

```python
from curry.lib import Lists

for xs, ys in curry.eval(Lists.split([1, 2, 3])):
    print(xs, ys)
# [] [1, 2, 3]
# [1] [2, 3]
# [1, 2] [3]
# [1, 2, 3] []
```

An expression has zero or more values, and `curry.eval` hands them over as
they're found. Zero values isn't an error: the loop just doesn't run. `.one()`
is for the case where you expect exactly one, and it complains otherwise.

## Running a function backwards

Back to `Logic`. We have a printer. We'd like a parser too, which in Python or
C++ means a tokenizer and a recursive descent over the same grammar, kept in
step with the printer by hand. In Curry the parser is one line, added to
`Logic.curry`:

```curry
-- Logic.curry, continued
parse :: String -> Formula
parse (render p) = p
```

The pattern is a call of `render`. To match it, Sprite finds a formula `p`
whose rendering is the given string, and that `p` is the answer:

```python
tree = curry.eval(L.parse('((T|F)&!F)')).one()
print(tree)                            # And (Or T F) (Not F)
tree == f                              # True
list(curry.eval(L.parse('(T&')))       # []
```

The five rules of `render` are the whole grammar, read right to left, and
malformed input gives you an empty list.

The same trick applies wherever you have one direction of a relation and want
the other. The repository has small examples of a
[build system](https://andyjost.github.io/Sprite/Examples.html#example-24)
whose pattern rules run both ways, a
[package dependency solver](https://andyjost.github.io/Sprite/Examples.html#example-15)
with no search code, and
[C++ overload resolution](https://andyjost.github.io/Sprite/Examples.html#example-21)
that can also tell you which argument types pick a given overload. We think
compiler IR, where passes are rewrite rules over a term graph, is another
natural fit.

## Installation

```sh
pip install --pre curry
```

The `--pre` is needed while Sprite is in alpha. If you'd rather not touch
your Python at all, a one-line installer brings its own and installs Sprite
under your home directory:

```sh
curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh
```

## Documentation

The [documentation](https://andyjost.github.io/Sprite/) has a
[Quickstart](https://andyjost.github.io/Sprite/Quickstart.html), a
[Curry primer](https://andyjost.github.io/Sprite/CurryPrimer/index.html) for
Python programmers, the [Python API](https://andyjost.github.io/Sprite/PythonAPI/index.html),
the [REPL](https://andyjost.github.io/Sprite/REPL.html), and a
[Status](https://andyjost.github.io/Sprite/Status.html) page that says what
works today. The twenty-six [examples](https://andyjost.github.io/Sprite/Examples.html)
each come with a README, a run script and recorded output. The Fair Scheme
and its proofs are written up in a
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
and a shorter [paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf).

Questions and bug reports go to the
[issue tracker](https://github.com/andyjost/Sprite/issues).

## Contributing

Pull requests are welcome; [CONTRIBUTING.md](CONTRIBUTING.md) has the
conventions. Every new feature or fixed bug comes with a unit test.

## License

[BSD 3-Clause](LICENSE). The Curry library under `curry/lib` is the base
library of PAKCS and carries its license and a notice of its origin.
