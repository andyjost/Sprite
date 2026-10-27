<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

Sprite is a compiler and runtime for the Curry language, with a Python API.
Curry is a typed, lazy functional language with the syntax of Haskell and two
things that Python and C++ lack: a function may have several rules that apply
at once, and an argument may be an unknown. So a function written once runs
forwards and backwards, and an expression has zero, one or many values. Few
teams reach for that, because it has meant a dependency on Prolog, or a
language nobody else on the team reads. With Sprite it is `pip install curry`
and `import curry`.

## The printer, run backwards

Your project has a data type and a printer for it: one function writes every
node of an IR, a type or a schema as text. One day you need the text back as
data, for a round-trip test or for a user's input. The parser is the printer
run backwards, and no function in C++ or Python runs backwards. So you write
a tokenizer and a recursive-descent parser, a second copy of the grammar, and
you keep both copies in step.

With Sprite the parser is one line. Here is the printer, as a Curry module.

```curry
module Logic where

data Formula = T | F | Not Formula | And Formula Formula | Or Formula Formula
  deriving (Eq, Show)

render :: Formula -> String
render T = "T"
render F = "F"
render (Not p) = "!" ++ render p
render (And p q) = "(" ++ render p ++ "&" ++ render q ++ ")"
render (Or p q) = "(" ++ render p ++ "|" ++ render q ++ ")"

parse :: String -> Formula
parse s | render p =:= s = p  where p free
```

```python
import curry
curry.path.insert(0, '.')
from curry.lib import Logic

goal = Logic.parse('((T|F)&!(F&T))')
tree = curry.eval(goal).one()
print(tree)   # And (Or T F) (Not (And F T))
```

The last line of the module is the parser. `where p free` declares `p` as an
unknown formula. The guard `render p =:= s` asks that `render p` and `s` be
equal, and the engine binds `p` to make it so. There is no parsing code: the
five rules of the printer are the grammar, read in the other direction.
`render` is lazy and `=:=` compares the strings character by character. A
candidate that starts wrong is dropped before the rest of it is built. The
answer comes back at once.

The Python side is small:

- `from curry.lib import Logic` imports a Curry module from a directory on
  `curry.path`. The first import translates and compiles it.
- `Logic.parse(text)` builds a typed Curry expression and runs nothing. Python
  `str`, `int`, `bool`, `list` and `tuple` convert by the Curry types.
- `curry.eval(goal)` returns its values, and `.one()` takes the first. An
  expression has zero or more values, and zero is not an error:
  `list(curry.eval(goal))` is then empty.

## Overload resolution, both ways

A compiler is full of functions that run in one direction, and of questions
that go the other way. Here is a small model of C++ overload resolution:
five arithmetic types, three ranks of conversion, a call with one argument.

```curry
module Overloads where

data Type = Char | Int | Long | Float | Double  deriving (Eq, Show)
data Rank = Exact | Promotion | Conversion  deriving (Eq, Ord, Show)

rank :: Type -> Type -> Rank
rank a p | a == p = Exact
         | (a, p) `elem` [(Char, Int), (Float, Double)] = Promotion
         | otherwise = Conversion

overloads :: [(String, Type)]
overloads = [("f(int)", Int), ("f(long)", Long), ("f(double)", Double)]

resolve :: Type -> String
resolve a | all (\(_, p) -> rank a p >= r) overloads
          && length [p | (_, p) <- overloads, rank a p == r] == 1 = name
  where (name, param) = anyOf overloads
        r = rank a param

picks :: String -> Type
picks name | resolve a =:= name = a  where a free
```

`anyOf overloads` stands for any one candidate, and each candidate runs as
its own branch. The guard keeps the candidate whose rank is the best and
shared by no other. An ambiguous call has no value, with no error code and
no else branch. `picks` asks the same function backwards: `where a free`
leaves the argument type unknown, and `resolve a =:= name` asks for every
type that picks the named overload. The runtime narrows `a` to each
constructor of `Type` and keeps the ones that fit, in no fixed order.

```python
import curry
curry.path.insert(0, '.')
from curry.lib import Overloads as Ov

curry.eval(Ov.resolve(Ov.Char)).one()    # 'f(int)'     char promotes to int
curry.eval(Ov.resolve(Ov.Float)).one()   # 'f(double)'

goal = Ov.picks('f(double)')
[str(t) for t in curry.eval(goal)]                 # ['Double', 'Float']
[str(t) for t in curry.eval(Ov.picks('f(int)'))]   # ['Int', 'Char']
```

The full model, with the standard conversion sequences, is
[examples/21-cxx-types-overloads](examples/21-cxx-types-overloads). Three more
share its model of C++ types. [Example 20](examples/20-cxx-types-deduction) deduces
template arguments by unification. [Example 22](examples/22-cxx-types-trait-check)
finds counterexamples to type traits over every type up to a depth.
[Example 23](examples/23-cxx-types-layout) lays out a struct by search, with the
struct described from Python as a reflection would. A compiler that embeds
Python could hand such a model the types under compilation, and ask the
questions a compiler does not answer, such as which argument types would
make a call ambiguous.

## Where it helps

- Compilers and IR. An intermediate representation is a term graph, and many
  passes are conditional rewrite rules. [Example 14](examples/14-parser-functional-patterns)
  parses expressions with three rules with functional patterns and no parser
  library. [Example 17](examples/17-type-inference) infers the types of lambda
  terms by unification, with free variables as the unknown types.
- Packaging and builds. [Example 15](examples/15-dependency-solver) is a
  package dependency solver: the plan is a value of the relation it states,
  and there is no search code. [Example 24](examples/24-build-system) is a
  makefile written in Curry: the pattern rule `%.o: %.c` is a functional
  pattern, and the same rules answer who needs a header.

The nodes of a term graph can stand for types, as above, for lambda terms or
for tensor expressions. The [Examples](https://andyjost.github.io/Sprite/Examples.html)
page lists all 26, each with a README, a run script and its recorded output.

## How it works

The runtime rewrites term graphs. When two rules apply to one node, it keeps
both as a choice. The branches advance in turns, so no branch waits forever
on another. This strategy, the Fair Scheme, is proved correct and complete:
every value of an expression is found and nothing else, whatever the order
of exploration. A
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
and a [paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf)
describe the scheme.

The Curry front end reads a module and writes FlatCurry. Sprite translates
it to ICurry, then to C++, then to a shared object. A module runs
interpreted the moment it is imported, and it swaps to the compiled code
when the background compile finishes. A C++ compiler is optional.

The runtime is about 23,000 lines of C++ and the Python side about 34,000.
The suite has 154 unit test files and 27 functional test files. It runs on
every change, on Linux and macOS and on every Python from 3.11 to 3.15.
Sprite uses the front end and the base library of PAKCS 3.10.0. The
translator is checked byte for byte against the tools of PAKCS over the 30
modules of that library.

## Installation

```sh
pip install curry
```

Two wheels and nothing else. `curry` holds the runtime, the compiled Curry
library and the Python API, 2.9 to 3.1 MB per Python version.
`curry-frontend`, the only dependency, holds the Curry front end as a native
executable: 3.1 MB on Linux x86-64, 6.3 MB on Linux aarch64, 8.3 MB on macOS
arm64 and 2.6 MB on macOS x86-64. At run time there is no Prolog, no Haskell
toolchain and no JVM. The wheels cover Python 3.11 to 3.15, the
free-threaded build included: manylinux_2_28 wheels for Linux x86-64 and
aarch64, and macOS wheels for macOS 15 or newer, Apple silicon and Intel.

Without a suitable Python, a one-line installer brings its own, installs
Sprite under your home directory and leaves the system Python alone:

```sh
curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh
```

## Support

Questions, bug reports and feature requests go to the
[issue tracker](https://github.com/andyjost/Sprite/issues). The
[documentation](https://andyjost.github.io/Sprite/) has a
[Quickstart](https://andyjost.github.io/Sprite/Quickstart.html), a
[Curry primer](https://andyjost.github.io/Sprite/CurryPrimer/index.html), the
Python API, the REPL, the [Installation](https://andyjost.github.io/Sprite/Installation/Installation.html)
page with the build from source, and the [Status](https://andyjost.github.io/Sprite/Status.html) page.

## Contributing

Pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) names the pages
to read first and the conventions. Every new feature or fixed bug comes with
a unit test.

## License

Sprite is distributed under the [BSD 3-Clause License](LICENSE). The Curry
library under `curry/lib` is the base library of PAKCS and carries the
license of PAKCS and a notice of its origin.
