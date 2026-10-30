=====================
The ``curry`` Package
=====================

.. _top-api:

The :download:`installed public stub <../../../src/python/__init__.pyi>`
records the public names and their landed signatures. The public API uses
terms and converted values.  Import with
``curry.import_``; the loaded registry is ``curry.modules``.  A module's
attributes are symbols, item lookup reaches operators, and ``curry.info``
provides metadata, including its name, file, symbols and types.

Calling a symbol constructs a typed ``Term``.  ``curry.term`` converts a
Python value, ``curry.parse`` reads Curry text, and ``curry.typeof`` gives
the type.  ``curry.free(name)``, ``curry.anonymous`` and ``curry.choice``
construct variables and choices.  ``curry.let`` and ``curry.ref`` describe
explicit bindings.  A held Python term shares a computation when reused.

``curry.eval`` returns ``Results`` of converted values; ``curry.solve``
returns ``Answer`` objects with ``Bindings``.  ``Results.one()`` checks
uniqueness.  User data is ``Data``, callable function values are
``Function``, finite set values are ``Values``, and ``Char`` is distinct
from String.  ``curry.show`` prints Curry text.

Curry ``Int`` is unbounded and maps to Python ``int`` in both directions.
Signed 64-bit values use the runtime's inline fast path. Arithmetic
promotes an overflowing result to libtommath and demotes a result that fits
inline. ``Char`` retains its Unicode code point range.

``curry.compile`` creates modules.  The current session signatures of
``save``, ``load``, ``reset`` and ``reload`` are described in
:doc:`UsingTheAPI`.  ``curry.path`` controls imports, ``curry.flags`` holds
interpreter settings, and ``curry.stats`` reports runtime counters.
The public error tree is rooted at ``curry.CurryError``.

.. _interpreter-flags:

Interpreter flags
=================

:data:`curry.flags` is a read-only mapping of the current session's flags.
The environment variable ``SPRITE_INTERPRETER_FLAGS`` sets the initial
flags of a process (``interpret:off,rotation:steps:65536``).  Use
``curry.reset(**flags)`` to start a new session with changed settings.  Reset retains ``curry.path`` and makes earlier
terms stale.  ``curry.reload(module, text=...)`` replaces a module's code;
it does not set interpreter flags.  :mod:`curry.interpreter.flags`
describes every flag at length; the table names them with their defaults.

===========================  =====================  ========================================================
Flag                         Default                What it changes
===========================  =====================  ========================================================
``backend``                  ``'cxx'`` [1]_         The backend: ``'cxx'``, the C++ backend.
``interpret``                ``'tiered'``           How the C++ backend runs a module without a compiled
                                                    object: ``'tiered'`` interprets it at once and
                                                    compiles it in the background; ``'new'`` interprets
                                                    it and never compiles it; ``'all'`` interprets every
                                                    module; ``'off'`` compiles every module first.
``rotation``                 ``'time:10ms'``        How the C++ backend paces the rotation of its queue
                                                    of alternatives: time mode (``time:<N><unit>``) or
                                                    step mode (``steps:<N>``), in which the order of the
                                                    values of a search reproduces.  ``SPRITE_ROTATION``
                                                    sets it alone.
``stack_limit``              ``4194304``            The bytes of C stack the C++ backend lets one
                                                    use on the caller; ``None`` disables the guard.
``worker_stack``             ``1073741824``         The retained worker's stack reservation in bytes;
                                                    ``None`` disables escalation for deep evaluations.
``recursion_limit``          ``262144``             Reserved for compatibility; has no effect.
``step_budget``              ``2048``               Reserved for compatibility; has no effect.
``inline_budget``            ``4``                  The largest function body, in nodes built, that the
                                                    optimizer inlines at a call; a call of a single-case
                                                    function on a constructor becomes the branch.  ``0``
                                                    turns both rules off.
``checker``                  ``False``              The checker mode of the Fair Scheme proofs program: the
                                                    runtime asserts the run-time invariants of the Fair
                                                    Scheme at every fork, escape, pull-tab, instantiation
                                                    and yield.
``debug``                    ``False``              More consistency checks; the C++ backend compiles its
                                                    modules in the debug flavor.
``trace``                    ``False``              Reserved; runtime traces require a ``TRACE`` build.
``telemetry_interval``       ``None``               Reserved for compatibility; use ``curry.stats`` for
                                                    runtime counters.
``lazycompile``              ``True``               Reserved for compatibility; has no effect.
``keep_temp_files``          ``False``              Keep the temporary files; a string names the
                                                    directory for them.
``postmortem``               ``False``              Copy the generated code of a failed compile from a
                                                    string to the working directory.
===========================  =====================  ========================================================

.. [1] The only value of ``backend`` is ``cxx``.

Package Structure
=================

The contents of the ``curry`` package are documented in detail in the
:ref:`reference-material`.  The major submodules are described briefly below.

:mod:`curry.backends`
    The interface :class:`IBackend <curry.backends.IBackend>`, its
    implementation, the C++ backend (:mod:`curry.backends.cxx`), and the
    generic code of the backends (:mod:`curry.backends.generic`).

:mod:`curry.cache`
    Implements caching for Curry-to-ICurry and other conversions.

:mod:`curry.common`
    Contains common definitions used throughout Sprite.

:mod:`curry.config`
    Functions for interacting with Sprite's system configuration.

:mod:`curry.exceptions`
    Contains all non-built-in exceptions Sprite might raise.

The public builders and value classes are described in :doc:`UsingTheAPI`.
The remaining modules here are developer modules outside that surface.

:mod:`curry.icurry`
    A Python implementation of ICurry, which serves as the Sprite IR.

:mod:`curry.inspect`
    A module for inspecting Curry objects: the predicates on nodes, the
    types of a module, the ICurry and the generated code of a symbol.

:mod:`curry.interpreter`
    Defines the Curry interpreter: the class
    :class:`Interpreter <curry.interpreter.Interpreter>`, the flags, and
    the modules that implement its methods.

:mod:`curry.lib`
    A virtual package used as the base for importing Curry modules.

:mod:`curry.objects`
    Implements the modules, terms and converted values returned by the
    public API.

:mod:`curry.show`
    Code for converting Curry expressions to strings.

:mod:`curry.toolchain`
    Contains code for manipulating the :ref:`compilation pipeline
    <compilation-pipeline>`.  Driver functions for external
    programs used by Sprite can be found here, and the translation from
    FlatCurry to ICurry (:mod:`curry.toolchain.flat2icurry`).

:mod:`curry.tools`
    Defines the command-line tools that come with Sprite.  This is where the
    source for :ref:`sprite-make` and the :ref:`REPL <repl>`
    (:mod:`curry.tools.icy`) can be found.  :ref:`sprite-exec` is defined
    in the ``__main__.py`` file for ``curry``.  This, incidentally, means
    that running ``python -m curry`` from a command prompt is a synonym for
    :ref:`sprite-exec`.

:mod:`curry.typecheck`
    The typed boundary between Python and Curry.  The signature table reads
    the type schemes of the loaded symbols from the FlatCurry interfaces
    (``symbol.signature``, ``symbol.scheme``, ``interp.sigtable``).  The
    package also holds the defaulting table and the goals of
    :func:`curry.eval`, the engine and the builder that type the
    terms built with ``curry.term``, and the error catalogue
    (:mod:`curry.typecheck.errors`).

:mod:`curry.utility`
    General-purpose code.

.. note::

   For developers: :mod:`curry.objects` defines the classes behind the
   public API.  :class:`curry.objects.CurryModule` is the object created by
   importing a Curry module, and :class:`curry.objects.CurryNodeInfo` holds
   a symbol's implementation metadata.
