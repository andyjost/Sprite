<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

<p align="center"><em>Programs that search, as a Python import.</em></p>

Some problems are searches. Parse this text. Infer that type. Pick versions
that fit together. Find the overload a call resolves to. Imperative code
spells the search out, with loops, state, backtracking and special cases. A
logic program states the relation between a question and its answers and
lets an engine do the searching. Few teams reach for that, because it has
meant a dependency on Prolog, or a language nobody else on the team reads.

Sprite removes the dependency. It is a compiler and runtime for
[Curry](https://www.curry-lang.org/), a small, typed language of the Haskell
family in which a function may have several results, an argument may be left
unknown, and a pattern may describe the shape of a result. Sprite compiles
Curry modules to native code and runs them in its own runtime, and its
Python API imports such a module like any other. The results come back as
Python values.

## Patterns that search

One function, one rule, and the rule's pattern has a hole on each side:

```curry
-- Flags.curry: the argument that follows a flag, wherever the flag is.
after :: String -> [String] -> String
after flag (_ ++ [flag, value] ++ _) = value
```

```python
import curry
curry.path.insert(0, '.')          # where Sprite looks for Curry modules
from curry.lib import Flags

curry.eval(Flags.after('--out', ['nvcc', '-O3', '--out', 'a.o', 'x.cu'])).one()
# 'a.o'
list(curry.eval(Flags.after('-I', ['-I', 'inc', '-I', 'more', 'x.cu'])))
# ['inc', 'more']
list(curry.eval(Flags.after('--out', ['x.cu'])))
# []
```

The pattern `_ ++ [flag, value] ++ _` describes a list that contains the flag
and a value after it, with anything before and after them. The engine finds
every place where the pattern fits. Two fits are two results. No fit is no
result, which is not an error. A Curry expression has any number of values,
zero or more; `curry.eval` hands Python all of them, and `.one()` takes the
first.

## Programs that run backwards

A printer for Boolean formulas, and a parser that is the printer run in
reverse:

```curry
-- Logic.curry
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
from curry.lib import Logic

tree = curry.eval(Logic.parse('((T|F)&!(F&T))')).one()
print(tree)
# And (Or T F) (Not (And F T))
```

`p free` declares an unknown formula, and `render p =:= s` asks for its
rendering to equal the input. The engine finds the formula. There is no
parser; the printer is the grammar, read in the other direction. The
strategy that does this, the Fair Scheme, is proved correct and complete:
every solution is found and nothing else is, whatever the order in which the
alternatives are explored.

## Where this leads

The runtime is a term graph rewriting engine. A Curry function is a set of
rewrite rules, the rules may overlap, and the engine explores the
alternatives fairly. That is the shape of a compiler's work, and the larger
examples lean that way: [template argument deduction](examples/20-cxx-types-deduction),
[overload resolution](examples/21-cxx-types-overloads),
[trait checking by narrowing](examples/22-cxx-types-trait-check) and
[member layout by search](examples/23-cxx-types-layout), over one model of
C++ types; [type inference by unification](examples/17-type-inference) in a
dozen rules; [a parser from functional patterns](examples/14-parser-functional-patterns).
Searches under constraints read the same way: [a package dependency solver](examples/15-dependency-solver)
that is the relation and nothing else, [a scheduler](examples/16-scheduling),
[a makefile written in Curry](examples/24-build-system) and
[a perfect hash function found by search](examples/25-perfect-hash). Term
graphs are a natural home for symbolic tensor expressions, too; that work is
ahead.

Every example is a directory with a README, a run script and its recorded
output. The [catalogue](examples/README) lists all twenty-six.

## What you install

```sh
pip install curry
```

Two wheels and nothing else. `curry`, about 3 MB, holds the runtime, the
compiled Curry library and the Python API; `curry-frontend` holds the Curry
compiler front end as a native executable. No Prolog, no Haskell toolchain,
no JVM. Python 3.11 to 3.15, the free-threaded build included, on Linux
x86-64 and aarch64; wheels for macOS 15 or newer (Apple silicon and Intel)
follow with the macOS build of the front end. A C++ compiler is optional: a
module runs interpreted at once and swaps to compiled code when the
background compile finishes. Without a suitable Python, a one-line installer
brings its own; the
[Installation Guide](https://andyjost.github.io/Sprite/Installation/Installation.html)
has it, with the build from source and the run without a compiler.

## How it is built

A Curry module goes through the Curry front end to FlatCurry, through
Sprite's translator to ICurry, and through C++ to a shared object; the typed
boundary reads the Curry types and converts Python values in both
directions. The runtime is about 23,000 lines of C++ and the Python side
about 34,000. About 180 test files run on every change, on Linux and macOS
and on every Python from 3.11 to 3.15, and the translator is checked byte
for byte against the tools of PAKCS over the whole Curry library. The design
is the subject of a
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
and a shorter
[paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf).

## About Curry

Curry has the functions, the types and the lazy evaluation of Haskell, with
nondeterministic choice and logic variables built into the language. Sprite
uses the Curry front end and the `base` library of PAKCS 3.10.0, so most
programs written for PAKCS run unchanged, with the same answers in another
order; set functions follow the weak encapsulation of the dissertation, and
the [Status](https://andyjost.github.io/Sprite/Status.html) page lists what
differs and the known limits. The
[Curry Primer](https://andyjost.github.io/Sprite/CurryPrimer/index.html)
teaches the language to a Python programmer in an afternoon.

## Learn more

- [Quickstart](https://andyjost.github.io/Sprite/Quickstart.html): five minutes with the Python API.
- [Examples](https://andyjost.github.io/Sprite/Examples.html): the twenty-six programs, from a first Curry program to applications.
- [The Python Interface](https://andyjost.github.io/Sprite/PythonAPI/index.html): terms, evaluation, answers and bindings, set functions and streams.
- [The REPL](https://andyjost.github.io/Sprite/REPL.html) and the [command-line tools](https://andyjost.github.io/Sprite/CommandLineInterface/index.html).
- [API Reference](https://andyjost.github.io/Sprite/Reference/index.html).

## Support

Questions, bug reports and feature requests go to the
[issue tracker](https://github.com/andyjost/Sprite/issues). The best bug
report is a small Curry program or Python snippet with the answer you
expected; `tests/README` shows how to turn it into a unit test. Questions
about the Curry language itself go to the Curry mailing list
(curry@lists.RWTH-Aachen.DE). Sprite is developed and maintained by Andy Jost
(andy.m.jost@gmail.com).

## Contributing

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Sprite is distributed under the BSD 3-Clause License; see [LICENSE](LICENSE).
The Curry library under `curry/lib` carries its own BSD license and notice.
