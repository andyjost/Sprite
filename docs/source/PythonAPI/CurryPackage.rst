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

``curry.compile`` creates modules.  The current session signatures of
``save``, ``load``, ``reset`` and ``reload`` are described in
:doc:`UsingTheAPI`.  ``curry.path`` controls imports, ``curry.flags`` holds
interpreter settings, and ``curry.stats`` reports runtime counters.
The public error tree is rooted at ``curry.CurryError``.

.. _interpreter-flags:

Interpreter flags
=================

An interpreter has a dict of flags.  :data:`curry.flags` is the dict of the
global interpreter; the environment variable ``SPRITE_INTERPRETER_FLAGS``
sets the flags of a process (``interpret:off,rotation:steps:65536``), and
:func:`curry.reload` or ``Interpreter(flags={...})`` sets them for a new
interpreter, over the flags of the environment.  A flag read at the start
of an evaluation takes effect at the next one when it is changed in the
dict.  ``backend`` is read when the interpreter is made, so a change of it
in the dict has no effect; :func:`curry.reload` or a new interpreter
selects a backend.  An assignment to :data:`curry.flags` rebinds the name
in the package and changes nothing.  :mod:`curry.interpreter.flags`
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
                                                    evaluation use; ``None`` disables the guard.
``inline_budget``            ``4``                  The largest function body, in nodes built, that the
                                                    optimizer inlines at a call; a call of a single-case
                                                    function on a constructor becomes the branch.  ``0``
                                                    turns both rules off.
``checker``                  ``False``              The checker mode of the Fair Scheme proofs program: the
                                                    reference backend asserts the run-time invariants of
                                                    the Fair Scheme at every fork, escape, pull-tab,
                                                    instantiation and yield; the C++ backend ignores it.
``debug``                    ``False``              More consistency checks; the C++ backend compiles its
                                                    modules in the debug flavor.
``trace``                    ``False``              Trace the computation.
``telemetry_interval``       ``None``               Seconds between the event reports of the runtime in
                                                    the log; ``None`` turns them off.
``lazycompile``              ``True``               Materialize a function when it is first needed.
``keep_temp_files``          ``False``              Keep the temporary files; a string names the
                                                    directory for them.
``postmortem``               ``False``              Copy the generated code of a failed compile from a
                                                    string to the working directory.
===========================  =====================  ========================================================

.. [1] The default of ``backend`` is the one ``configure --with-default-backend``
   recorded in ``sysconfig/default_backend`` of the installation; ``cxx``
   unless configured otherwise.  The flags of the reference backend,
   ``step_budget`` and ``recursion_limit``, are described in the
   :doc:`developer notes </DeveloperNotes>`.

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
    Defines the objects used to provide Python APIs to Curry objects.  For instance,
    this defines :class:`curry.objects.CurryModule`, which is the object created by importing a
    Curry module, and :class:`curry.objects.CurryNodeInfo`, the object of a
    symbol.

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
