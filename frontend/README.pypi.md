# curry-frontend

The Curry front end, version 2.0.0, as shipped with PAKCS 3.4.1: the
compiler stage that parses and type-checks a Curry program and writes its
FlatCurry. This distribution packages the upstream program for Linux as
manylinux wheels, x86-64 and aarch64, built from the PAKCS source in the
continuous integration of [Sprite](https://github.com/andyjost/Sprite), a
Curry compiler and runtime with a Python API. Sprite's package,
`currylang`, depends on it and runs it when it loads a Curry source file.

The wheel installs one command:

```sh
curry-frontend --numeric-version   # prints 2.0.0
curry-frontend --flat Prog.curry   # writes .curry/Prog.fcy and its interface
```

The program is the work of the Curry group at the University of Kiel
(the Hackage package `curry-frontend`); its license and the notices of the
libraries bundled with the executable are in the wheel. The version's
`post` number counts Sprite's packaging revisions of upstream 2.0.0; the
program version is always 2.0.0.
