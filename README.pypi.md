<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup.svg" width="440">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/v/curry" alt="PyPI"></a>
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/pyversions/curry" alt="Python versions"></a>
  <img src="https://img.shields.io/badge/platforms-Linux%20%7C%20macOS-blue" alt="Platforms">
  <a href="https://github.com/andyjost/Sprite/actions/workflows/ci.yml"><img src="https://github.com/andyjost/Sprite/actions/workflows/ci.yml/badge.svg?branch=master&event=push" alt="CI"></a>
  <a href="https://github.com/andyjost/Sprite/blob/master/LICENSE"><img src="https://img.shields.io/github/license/andyjost/Sprite" alt="License"></a>
</p>

The `curry` package is Sprite. Sprite compiles and runs
[Curry](https://www.curry-lang.org/), and lets you call it from Python. Curry is a functional logic programming language. On the
functional side it follows Haskell down to the syntax: algebraic data types,
pattern matching, type inference, lazy evaluation. On the logic side it adds
nondeterminism, logic variables and search: an expression may have any number
of values, an argument may be left unknown, and the runtime finds the values
that fit by unification. So you can state what a result has to satisfy and
leave the search to the language. Sprite's evaluation strategy, the Fair
Scheme, is proved sound, complete and optimal: it finds exactly the values of
any expression, and it executes only the steps needed to produce them.

Sprite is in alpha. It installs with `pip install --pre curry`, two small
wheels and nothing else. Try it, and
[tell us what breaks](https://github.com/andyjost/Sprite/issues).

## Import Curry into Python

Here is a Curry module. It defines a small type of Boolean formulas and a
function that prints one.

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

If you've read Haskell, nothing here is new. Save it next to your Python code
and import it:

```python
import curry
curry.path.insert(0, '.')          # Curry's sys.path
from curry.lib import Logic as L   # compiles and imports ./Logic.curry

formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
goal = L.render(formula)
curry.eval(goal).one()             # the one value: '((T | F) & !F)'
```

The constructors of `Formula` are there as `L.T`, `L.And` and so on, and the
result comes back as a Python string. `L.render(formula)` builds an expression
without running it, and `curry.eval` runs it. The first import translates the
module and compiles it to native code; on a machine without a C++ compiler,
Sprite interprets it instead. Later imports reuse the result.

## Nondeterminism

Curry is nondeterministic: every expression may have any number of values.
The pattern here is `xs ++ ys`, a call of list concatenation. You can't write
that in Haskell, where a pattern is built from constructors only. Curry lets
you, and reads it as: this rule applies whenever the argument can be taken
apart as `xs ++ ys`, once for each way of taking it apart:

```haskell
-- Lists.curry
split (xs ++ ys) = (xs, ys)
```

A list of three splits four ways, and Sprite's search finds all four:

```python
from curry.lib import Lists

for xs, ys in curry.eval(Lists.split([1, 2, 3])):
    print(xs, ys)
# [] [1, 2, 3]
# [1] [2, 3]
# [1, 2] [3]
# [1, 2, 3] []
```

`curry.eval` hands the values over as they're found, each as a Python tuple
of two lists, which is why the loop can unpack it. When you expect exactly
one value, as in the first example, `.one()` takes it and complains if there
are more; use `next` to take the first of many values.

## Running a function backwards

Back to `Logic`. To build a toy parser from `render`, write the call of
`render` as the pattern and leave the formula unknown. That's the whole
parser, one line added to `Logic.curry`:

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
list(curry.eval(L.parse('(T &')))      # []
```

The five rules of `render` serve as the grammar, read right to left, and
malformed input gives you an empty list. There's no second copy of the
grammar to keep in step, and the parser can't disagree with the printer,
because it is the printer. This is where Curry excels: the specification is
the program. There's nothing more to write, and nothing more to get wrong.

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
each come with a README, a run script and recorded output. The Fair Scheme
and its proofs are written up in a
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
and a shorter [paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf).

Questions and bug reports go to the
[issue tracker](https://github.com/andyjost/Sprite/issues). The source is at
[github.com/andyjost/Sprite](https://github.com/andyjost/Sprite).

## Contributing

Pull requests are welcome;
[CONTRIBUTING.md](https://github.com/andyjost/Sprite/blob/master/CONTRIBUTING.md)
has the conventions. Every new feature or fixed bug comes with a unit test.

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
