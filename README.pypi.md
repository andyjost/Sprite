<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="https://raw.githubusercontent.com/andyjost/Sprite/master/assets/logo/lockup.svg" width="440">
  </picture>
</p>

# Sprite for Curry

`curry` provides Sprite, a compiler and runtime for the
[Curry functional logic language](https://www.curry-lang.org/). Its Python API
combines Curry's nondeterministic search and logic variables with Python
programs. The import name is `curry`.

This is an alpha release. Linux wheels target glibc 2.28 or newer on x86-64
and aarch64, for CPython 3.11 through 3.15, including free-threaded 3.14.

```sh
python -m pip install --pre curry curry-frontend
python -m curry Peano.curry
```

For example, save the following as `Peano.curry`:

```curry
data Nat = O | S Nat
add O n = n
add (S n) m = S (add n m)
main = add (S O) (S O)
```

`python -m curry Peano.curry` prints `S (S O)`. The same program runs from
Python. A Curry module imports like a Python module once its directory is on
`curry.path`:

```python
import curry
curry.path.insert(0, '.')            # the directory of Peano.curry
from curry.lib import Peano

result = curry.eval(Peano.main).one()
print(result)                        # S (S O)
```

`curry.eval` returns every value of an expression, and `.one()` takes the
first; `main` has exactly one. Now ask the module a question it was not
written for. Leave the two numbers unknown, and Sprite finds every pair that
adds up to two:

```python
from curry.lib import Prelude

x, y = curry.free('x'), curry.free('y')
two = Peano.S(Peano.S(Peano.O))
goal = Prelude['=:='](Peano.add(x, y), two)
for value, bindings in curry.solve(goal):
    print(f'{value=} with {bindings=}')
```

```
value=True with bindings={x=O, y=S (S O)}
value=True with bindings={x=S O, y=S O}
value=True with bindings={x=S (S O), y=O}
```

Wheels include the compiled Curry library and run
without a C++ compiler. Install `g++` to compile your own modules with
`sprite-make --so Peano.curry`. The separate `curry-frontend` package provides
the Curry front end used when loading source programs.

The source distribution builds with pip, a C++ compiler, and Python development
headers. Pip installs CMake and Ninja in its isolated build environment and
uses the shipped current-pair library products. The Curry front end is needed
at run time for new Curry text; PAKCS, Prolog, and Haskell are unnecessary.

See the [documentation](https://andyjost.github.io/Sprite/) and
[source and issue tracker](https://github.com/andyjost/Sprite).
Sprite uses the BSD 3-Clause license; the distribution includes the notices
for its vendored Curry library and pybind11.

The `curry` package on PyPI is Sprite (`pip install curry`, `import curry`).
The name was held from 2009 by Malthe Borch for his package of partial
application; he agreed to its transfer, for which we thank him.

Version 0.9.0a1 was published as `currylang` on 2026-10-24; from 0.9.0a2
the distribution is `curry`.
