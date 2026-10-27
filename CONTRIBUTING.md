# Contributing to Sprite

Sprite is hosted at https://github.com/andyjost/Sprite. Pull requests are
welcome.

## Where to start

- The page [Developer Setup](https://andyjost.github.io/Sprite/DeveloperSetup.html)
  of the documentation sets up a machine: the packages, PAKCS, a conda
  environment, CMake and `make stage`.
- `AGENTS.md` at the root describes the layout of the repository, the
  build, the tests and the conventions.
- `tests/README` explains the test suite: the layout, the drivers, the
  oracle, and the environment variables of the test library.
- The page [Environment Variables](https://andyjost.github.io/Sprite/CommandLineInterface/EnvironmentVariables.html)
  lists the variables that the tools and the runtime read.

## Conventions

- Every new feature or fixed bug gets a unit test.
- Keep commits free of machine-specific paths and environment details.
- Before a push, run the fast tier of the unit suite from `tests/`:
  `./run_tests --fast`.
