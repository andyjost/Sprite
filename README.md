<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/lockup-dark.svg">
    <img alt="Sprite" src="assets/logo/lockup.svg" width="440">
  </picture>
</p>

## Overview

Sprite is an implementation of the Curry programming language
(https://www.curry-lang.org/). It is based on an evaluation strategy
called the Fair Scheme. You can read about it at
http://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf.

In addition to command-line tools for compiling and running Curry
programs, the Python API provides access to a Curry interpreter, (JIT)
compiler, and runtime. Curry code modules can thus be imported directly
into Python, enabling hybrid applications that leverage the strengths of
both languages.

The logo, a burst of dust beside the name, and the files of its identity
are under `assets/logo/`.

## Installation

On Linux, choose the path that fits your Python setup:

1. Without a suitable Python, let the installer bring its own:

   ```sh
   curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite | sh
   ```

   For confirmation before each installation step:

   ```sh
   curl -LsSf https://raw.githubusercontent.com/andyjost/Sprite/master/getsprite-i | sh
   ```

   The script installs uv if needed, then a managed Python 3.11.4 or newer
   and currylang with its curry-frontend dependency, all in your home
   directory. It leaves the system Python alone and never uses sudo. Run
   it again to upgrade Sprite. To preview the plan, download the script
   and run `sh getsprite --dry-run` (or `sh getsprite-i --dry-run`). Add
   the commands to your PATH, including in your shell startup file:

   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. With Python 3.11.4 or newer (through 3.15), install into your Python
   environment with pip:

   ```sh
   pip install currylang
   ```

   This also installs curry-frontend; uv is only needed by the script.

3. Python developers can run a Curry source file or open the Curry REPL
   through the Python they installed into:

   ```sh
   python -m curry MyProgram.curry
   python -m curry
   ```

A C++ compiler (g++) is optional. Without one, new modules run
interpreted; see "Installing and running without a C++ compiler" in the
documentation.

A conda recipe for linux-64 is under development under `conda/`. It is not
published; `conda/README.md` describes it.

A developer who sets up a new machine runs
`scripts/setup-dev-machine.sh --prefix DIR`. The script checks the apt
packages and prints the apt command when one is missing; it never runs
sudo. It installs PAKCS 3.4.1 and a conda environment
(`conda/dev-environment.yml`) under the prefix, links `install/` and
`object-root/` of the checkout into it, runs CMake and `make stage` in a
clean environment, and runs a smoke test. Say `--dry-run` to print the
plan first. The page "Developer Setup" of the documentation
(`docs/source/DeveloperSetup.rst`) describes the steps, the options, and
the layout of the prefix.

## Running a program

Programs run with `sprite-exec`. In a staged source checkout, for example,
run this from the repository root:

```sh
install/bin/sprite-exec examples/Peano.curry
```

The C++ backend runs a module interpreted until the compiled code is
ready, so an installation without a C++ compiler runs every program (see
the page "Installing and running without a C++ compiler" of the
documentation).

The numbered directories under `examples/` hold runnable examples of
Curry programs and of Curry called from Python. Each has a run script and
a README. `tests/unit_examples.py` compares their output with
`expected.out` on the declared backends. Example 19 is the successor to
the retired Flask blocks-world example. `examples/cxx/` and
`examples/Peano.curry` are support sources, without separate run scripts
or expected-output tests. See `examples/README` for the list.

## Documentation

The user guide is published at https://andyjost.github.io/Sprite/ from
the master branch. To build it yourself, run `make -C docs html` from the
repository root after `make stage`. The output is written under
`object-root/docs/html`. The sources are hosted at
https://github.com/andyjost/Sprite.

## Contact and bug reporting

Sprite was developed and is maintained by Andy Jost
(andy.m.jost@gmail.com). Feel free to contact him with questions, bug
reports, feature requests, and other miscellania. Direct general
questions about Curry to the Curry mailing list
(curry@lists.RWTH-Aachen.DE).

If you find a bug, please report it. The easiest way is to create a
minimal unit test decorated with `unittest.expectedFailure`. Further
instructions on developing and running tests can be found under
`tests/README`. Once you have written the test, submit a pull request or
send the diff by email.

## Contributing to Sprite

Contributions are welcome! For more information, see `CONTRIBUTING.md`.

## License

Sprite is distributed under the BSD 3-Clause License; see the `LICENSE`
file. The vendored Curry library under `curry/lib` carries its own BSD
license and notice.
