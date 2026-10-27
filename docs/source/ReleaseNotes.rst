=============
Release Notes
=============

0.9.0a2 (2026-10-27)
====================

- The distribution is named ``curry`` on PyPI: ``pip install curry``.
  The name ``currylang`` of the first alpha is retired; the import name
  was ``curry`` from the start.
- Wheels for macOS 15 or newer, Apple silicon and Intel, beside the Linux
  wheels; the Curry front end 3.1.0 ships for both as ``curry-frontend``
  3.1.0.post1.
- The current tools are the default: the Curry front end 3.1.0 (the
  package ``curry-frontend`` 3.1.0) with the ``base`` library 3.4.0 of
  PAKCS 3.10.0.  The pair of front end 2.0.0
  and PAKCS 3.4.1 remains accepted.
- The source distribution builds without a Curry front end: the pinned
  products of the library ship with it.
- Unbounded integers: an ``Int`` that overflows the machine word
  promotes to a big integer.
- The Curry preprocessor ``currypp`` is an optional tool found on PATH.
- The tiered compile writes its products beside a source only when the
  compile is done, so a removed directory never holds half-written files
  (#173).  The runtime compiles without strict aliasing (#170).
- Set functions: #133, #134, #139 and #171 fixed.
- A benchmark harness with a community suite of Curry programs.
- The logo: a burst of dust beside the name.

0.9.0a1 (2026-10-24)
====================

The first public alpha, as ``currylang``: Linux wheels for x86-64 and
aarch64 (glibc 2.28 or newer) and CPython 3.11 to 3.15, the free-threaded
3.14 included; the C++ runtime alone, the Python backend having been
removed; the Curry front end 2.0.0 as the separate package
``curry-frontend``.
