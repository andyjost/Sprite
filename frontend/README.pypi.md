# curry-frontend

The Curry front end, version 2.0.0 with PAKCS 3.4.1 or version 3.1.0
with PAKCS 3.10.0: the
compiler stage that parses and type-checks a Curry program and writes its
FlatCurry. This distribution packages the upstream program for Linux as
manylinux wheels, x86-64 and aarch64, and, for 2.0.0, for macOS 15 or newer
as wheels for Apple Silicon and Intel, built from the pinned PAKCS source
(2.0.0) or the GitHub tag v3.1.0 (3.1.0) in the
continuous integration of [Sprite](https://github.com/andyjost/Sprite), a
Curry compiler and runtime with a Python API. Sprite's package,
`currylang`, depends on it and runs it when it loads a Curry source file.

The wheel installs one command:

```sh
curry-frontend --numeric-version   # prints 2.0.0 or 3.1.0
curry-frontend --flat Prog.curry   # writes .curry/Prog.fcy and its interface
```

The program is the work of the Curry group at the University of Kiel
(the upstream project `curry-frontend`; 3.1.0 is sourced from GitHub); its license and the notices of the
libraries bundled with the executable are in the wheel. The version's
`post` number counts Sprite's packaging revisions of each upstream version: 2.0.0.post6 and 3.1.0.post1.
Sprite keeps 2.0.0/3.4.1 as its default until upgrade stage G.
The executable prints its upstream version without the packaging suffix.
