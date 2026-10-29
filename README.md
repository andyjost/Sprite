<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/v/curry" alt="PyPI"></a>
  <a href="https://pypi.org/project/curry/"><img src="https://img.shields.io/pypi/pyversions/curry" alt="Python versions"></a>
  <img src="https://img.shields.io/badge/platforms-Linux%20%7C%20macOS-blue" alt="Platforms">
  <a href="https://github.com/andyjost/Sprite/actions/workflows/ci.yml"><img src="https://github.com/andyjost/Sprite/actions/workflows/ci.yml/badge.svg?branch=master&event=push" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/andyjost/Sprite" alt="License"></a>
</p>

Sprite puts a logic engine in your Python program. You write what an answer
has to satisfy, as ordinary typed code, and the runtime finds it. Write a
printer and the parser comes with it. Write the rule for a dependency once and
ask it in either direction. The language is [Curry](https://www.curry-lang.org/):
it looks like Haskell, and it adds nondeterminism, logic variables and search
to the language itself. Sprite compiles Curry to native code and imports it
like a Python module.

Sprite is in alpha. `pip install --pre curry` brings two small wheels and
nothing else. Try it, and
[tell us what breaks](https://github.com/andyjost/Sprite/issues).

## The printer and the parser

Say you have a data type and a function that prints it. One day you need the
text back as data, for a round trip or a config file. In Python you'd write a
tokenizer and a recursive-descent parser, and keep them in step with the
printer by hand. In Curry it's one line, the last one in this module:

```curry
-- Logic.curry
data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula

render :: Formula -> String
render T = "T"
render F = "F"
render (Not p) = "!" ++ render p
render (And p q) = "(" ++ render p ++ " & " ++ render q ++ ")"
render (Or p q) = "(" ++ render p ++ " | " ++ render q ++ ")"

parse :: String -> Formula
parse (render p) = p
```

The data type and `render` are plain functional code, as in Haskell. The
pattern of `parse` is where Curry departs: it's a call of `render` with an
unknown argument. To match it, Sprite solves for the formula `p` whose
rendering is the input, and that `p` is the result. From Python:

```python
import curry
curry.path.insert(0, '.')          # Curry's sys.path
from curry.lib import Logic as L   # compiles and imports ./Logic.curry

formula = L.And(L.Or(L.T, L.F), L.Not(L.F))
goal = L.render(formula)
text = curry.eval(goal).one()        # the one value: '((T | F) & !F)'
tree = curry.eval(L.parse(text)).one()
print(tree)                          # And (Or T F) (Not F)
tree == formula                      # True
list(curry.eval(L.parse('(T &')))    # []
```

That's the whole parser. There's no second copy of the grammar to keep in
step, and the parser can't disagree with the printer, because it is the
printer. Malformed input has no value, so the list comes back empty. This is
where Curry excels: the specification is the program, and there's nothing
more to write and nothing more to get wrong.

The Python side is as thin as it looks. `curry.path` is Curry's `sys.path`;
the first import compiled `Logic.curry` to native code, or interprets it on a
machine without a C++ compiler, and later imports reuse the result; the
constructors are there as `L.And` and friends; and the string came back as a
plain `str`.

It's a toy parser, with no error messages and exactly one accepted spelling.
The same trick scales to the things you'd otherwise write a search for. The
repository has a [build system](https://andyjost.github.io/Sprite/Examples.html#example-24)
whose pattern rules run both ways, a
[package dependency solver](https://andyjost.github.io/Sprite/Examples.html#example-15)
with no search code, and a model of
[C++ overload resolution](https://andyjost.github.io/Sprite/Examples.html#example-21)
that also tells you which argument types pick a given overload. We think
compiler IR, where passes are rewrite rules over a term graph, is another
natural fit.

## How can a pattern call a function?

Because Curry is nondeterministic. Every expression may have any number of
values, and a function call in a pattern means "any argument this call could
have produced, once for each way of producing it". Here is the smallest
example we know:

```curry
-- Lists.curry
split (xs ++ ys) = (xs, ys)
```

`++` is list concatenation, so the rule applies whenever its argument can be
taken apart as `xs ++ ys`. A list of three can be taken apart four ways, and
Sprite's search finds all four:

```python
from curry.lib import Lists

for xs, ys in curry.eval(Lists.split([1, 2, 3])):
    print(xs, ys)
# [] [1, 2, 3]
# [1] [2, 3]
# [1, 2] [3]
# [1, 2, 3] []
```

`curry.eval` returns an iterator and hands the values over as they're found,
each one a Python tuple of two lists, which is why the loop can unpack it.
When you expect exactly one value, as the parser did, `.one()` takes it and
complains if there are more; use `next` to take the first of many values.
The parser is this same mechanism with `render` in place of `++` and a string
in place of the list: there, exactly one `p` fits, or none does.

## Under the hood

The runtime is a term-graph rewriting engine, about 23,000 lines of C++
behind a Python API. Its evaluation strategy, the Fair Scheme, is proved
sound, complete and optimal: it finds exactly the values of any expression,
and it executes only the steps needed to produce them. The proofs are in a
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
and a shorter [paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf).
Curry modules compile through C++ to native code; a module starts interpreted
the moment it's imported and swaps to the compiled code when the build
finishes. Sprite uses the Curry front end and the base library of PAKCS, so
most PAKCS programs run unchanged. The test suite runs on every change on
Linux and macOS, on every Python from 3.11 to 3.15, and the twenty-six
[examples](https://andyjost.github.io/Sprite/Examples.html) each come with a
README, a run script and recorded output.

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
works today. Questions and bug reports go to the
[issue tracker](https://github.com/andyjost/Sprite/issues).

## Contributing

Pull requests are welcome; [CONTRIBUTING.md](CONTRIBUTING.md) has the
conventions. Every new feature or fixed bug comes with a unit test.

## License

[BSD 3-Clause](LICENSE). The Curry library under `curry/lib` is the base
library of PAKCS and carries its license and a notice of its origin.
