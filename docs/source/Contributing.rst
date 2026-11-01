============
Contributing
============

Sprite is hosted at https://github.com/andyjost/Sprite.  Bug reports with a
reproducer are the most useful contribution right now; file them at
https://github.com/andyjost/Sprite/issues.  The semantics of the runtime are
delicate, so we don't take unsolicited pull requests: open an issue first,
and we'll talk.  The rest of this page is for work agreed that way.
``CONTRIBUTING.md`` at the root of the repository is the short form of this
page.

Where to start
==============

- :doc:`DeveloperSetup` sets up a machine: the packages, PAKCS, a conda
  environment, CMake and ``make stage``.
- :doc:`DeveloperNotes` holds the logging conventions, thread-safety rules,
  checker and runtime notes.
- ``AGENTS.md`` at the root of the repository describes the layout, the
  build, the tests and the conventions.
- ``tests/README`` explains the test suite: the layout, the drivers, the
  oracle and the environment variables of the test library.
- :doc:`DevelopmentVariables` lists the variables that
  the tools and the runtime read.

Conventions
===========

- Every new feature or fixed bug gets a unit test.  Mark a known failure
  with ``unittest.expectedFailure`` instead of deleting the test.
- Keep commits free of machine-specific paths and environment details.
- Before a push, run the fast tier of the unit suite from ``tests/``:
  ``./run_tests --fast``.
- Work lands on ``master``.  A topic branch holds the progress of one
  change until its merge and is deleted at the merge.

Windows tests
=============

On Windows, use ``python tests/run_tests.py --fast -j 2`` with a staged
installation in ``SPRITE_HOME`` and its Python package on ``PYTHONPATH``.
The runner starts process groups and uses ``taskkill /T /F`` for cleanup.
There is no Job Object hard memory cap; one notice explains this, and
optional ``psutil`` supplies the RSS watchdog and process names. Without it,
memory is reported as unknown and timeouts still apply. Tests of POSIX
facilities use ``cytest.posix_only(reason)``; Windows tests can use
``cytest.windows_only(reason)``. Functional files are skipped with one
notice when the PAKCS oracle is unavailable.

The plan
========

The `Sprite resuscitated milestone
<https://github.com/andyjost/Sprite/milestone/1>`_ lists the open work.
