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

The result is `S (S O)`. Wheels include the compiled Curry library and run
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

The `curry` package on PyPI is Sprite. `currylang` was its name until
0.9.0a1 and remains for one more release as an alias that depends on `curry`.
The Curry community also uses `currylang` as its namespace on Docker Hub.
The name `curry` on PyPI was held from 2009 by Malthe Borch for his package
of partial application; he agreed to its transfer to this project, for
which we thank him.
