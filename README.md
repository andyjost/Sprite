<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

**Sprite brings the Curry language to Python.** [Curry](https://www.curry-lang.org/)
is a functional logic language: it has the functions, the types and the lazy
evaluation of Haskell, and it builds two ideas from logic programming into the
language itself, *logic variables* and *nondeterministic choice*. With Sprite, a
Curry module is imported like a Python module and its functions are called from
Python. A function with several results gives Python all of them, and an
argument that is left unknown is solved for.

Sprite is a compiler and runtime for Curry built on the Fair Scheme, an
evaluation strategy that Sergio Antoy and Andy Jost proved correct and
complete: a computation produces every value of an expression and nothing
else, and no alternative can starve the others. The strategy and this
implementation are the subject of the
[dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf)
behind Sprite; the
[LoPSTR 2013 paper](http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf)
is the short account.

## Hello, Curry

Save this as `Hello.curry`:

```curry
greet :: String -> String
greet name = "Hello, " ++ name ++ "!"
```

Then, from Python in the same directory:

```python
import curry
curry.path.insert(0, '.')        # where Sprite looks for Curry modules
from curry.lib import Hello      # translates and compiles Hello.curry

curry.eval(Hello.greet('World')).one()
# 'Hello, World!'
```

A Python string goes in and a Python string comes out: Sprite types the call
from the Curry signature and converts the values both ways.

## A taste of logic programming

Add a function with three results to `Hello.curry`:

```curry
color :: String
color = "red" ? "green" ? "blue"
```

`?` is the choice operator of Curry. Python iterates over every result:

```python
list(curry.eval(Hello.greet(Hello.color)))
# ['Hello, red!', 'Hello, green!', 'Hello, blue!']
```

Now run `greet` backwards. Leave its argument free and state the result;
Curry finds the argument:

```python
goal = curry.parse('greet who =:= "Hello, Curry!" where who free', imports=[Hello])
for answer in curry.solve(goal):
    print(answer.bindings['who'])
# Curry
```

`=:=` is an equational constraint, `where who free` declares a logic
variable, and `curry.solve` yields each solution with its bindings. These two
ideas, choice and free variables, solve puzzles, parse text and search: the
[examples](examples/README) include sudoku, cryptarithms, n-queens with set
functions, a regular-expression matcher and a parser built from functional
patterns. The [Quickstart](https://andyjost.github.io/Sprite/Quickstart.html)
continues from here.

## Installation

```sh
pip install curry
```

Sprite supports Python 3.11 to 3.15 on Linux (x86-64 and aarch64) and on
macOS 15 or newer (Apple silicon and Intel). The wheels include the compiled
Curry library, and pip installs the Curry front end beside them (the package
`curry-frontend`). A C++ compiler (g++) is optional: without one, new modules
run interpreted.

Without a suitable Python, let the installer bring its own. It installs
[uv](https://docs.astral.sh/uv/), a managed Python and Sprite under your home
directory, and it never uses sudo:

```sh
curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh
```

The [Installation Guide](https://andyjost.github.io/Sprite/Installation/Installation.html)
covers the options of the installer, building from source and running without
a C++ compiler. `python -m curry` opens the Curry REPL, and
`python -m curry Program.curry` runs a program.

## Learn more

- [Quickstart](https://andyjost.github.io/Sprite/Quickstart.html): five minutes with the Python API.
- [Examples](https://andyjost.github.io/Sprite/Examples.html): twenty-six runnable programs, from a first Curry program to applications.
- [The Python Interface](https://andyjost.github.io/Sprite/PythonAPI/index.html): terms, evaluation, answers and bindings, set functions and streams.
- [The REPL](https://andyjost.github.io/Sprite/REPL.html) and the [command-line tools](https://andyjost.github.io/Sprite/CommandLineInterface/index.html).
- [Curry Primer](https://andyjost.github.io/Sprite/CurryPrimer/index.html): the language for a Python programmer.
- [API Reference](https://andyjost.github.io/Sprite/Reference/index.html).

**For Curry researchers.** Sprite uses the Curry front end of PAKCS and ships
the `base` library of PAKCS 3.10.0, so most programs written for PAKCS run
unchanged, with the same answers in another order. The runtime is a C++ graph
rewriting engine that implements the Fair Scheme with pull-tabbing; set
functions follow the weak encapsulation of the dissertation. The
[Status](https://andyjost.github.io/Sprite/Status.html) page lists what
differs and the known limits, and
[Performance](https://andyjost.github.io/Sprite/Performance.html) holds the
measurements.

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
