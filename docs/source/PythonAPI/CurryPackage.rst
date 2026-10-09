=====================
The ``curry`` Package
=====================

This section gives a high-level view of the ``curry`` package.  The intent
is to give readers some idea of where various bits of Sprite can be located.

.. _top-api:

Top-Level API
=============

The ``curry`` module itself serves as a collection of classes and functions
intended to carry out the most common tasks.  Many of these are methods of a
singleton Curry interpreter that is created when importing ``curry``.  For many
common use cases, one can simply use these methods without ever thinking about
an interpreter, let alone creating one.

The global interpreter can be obtained by calling :func:`curry.getInterpreter`.

The top-level data and methods fall roughly into the following categories:

  - **System Control**

    These can be used to manipulate the global interpreter:

        :data:`curry.flags`  : The flags of the global interpreter, a dict;
        see :ref:`interpreter-flags`.

        :data:`curry.path`   : Configure or view the Curry search path.

        :func:`curry.reload` : Discard the global interpreter, then create a
        new one, with the flags given and those of the environment.

        :func:`curry.reset`  : Soft-reset the global interpreter: unload
        every module but the Prelude and the packages, reset the path,
        clear the signature table.

        :func:`curry.stats`  : Report the statistics of the run: time, steps,
        forks, collections, memory, compile time, collector time, the
        counts of tiered execution, and the counters of the collector.

    Also, see the :mod:`curry.config` module.

  - **Symbols & Types**

    These can be used to find Curry objects.

        :func:`curry.module` : Find a loaded module by name.  A module of
        the Curry library of the installation is imported on demand; any
        other module must be imported first.

        :func:`curry.symbol` : Find a symbol by name.

        :func:`curry.type`   : Find a type by name.

        :func:`curry.currytype` : Get the Curry type that corresponds to a Python type.

  - **Curry Modules**

    These can be used to create, transform, load, or save Curry code.

        :func:`curry.compile` : Create Curry modules (with mode 'module').

        :func:`curry.import_` : Import a Curry module by name.

        :func:`curry.load`    : Load a compiled Curry module from its
        shared object.

        :func:`curry.save`    : Write the generated code of a module to a
        file, a program with a goal or a module alone
        (``module_main=False``).  The form is the one of the backend.

        :data:`curry.modules` : Access imported modules.

  - **Expressions & Evaluation**

    These can be used to build and evaluate Curry expressions.

        :func:`curry.compile` : Create Curry expressions (with mode 'expr').

        :func:`curry.eval`    : Evaluate a Curry goal; the arguments of
        :func:`curry.expr`, with the keyword ``converter``.

        :func:`curry.expr`    : Construct a Curry expression, typed (see :ref:`typed-expressions`).

        :func:`curry.raw_expr` : Construct a Curry expression without types.

        :func:`curry.typeof`  : The type of an expression or of a symbol.

        :func:`curry.describe` : Describe an expression, to be typed as a whole later.

        :func:`curry.topython` : Convert a Curry value to Python.

        :func:`curry.show_value` : The text of a converted value in Curry
        format.

  - **Markers of expressions**

    These objects stand for the parts of an expression that are no Python
    value (:mod:`curry.expressions`).

        :class:`curry.free` : A free variable; one marker is one variable.

        :class:`curry.choice` : A non-deterministic choice between two
        expressions.

        :class:`curry.typed` : A part with its type stated in Curry syntax.

        :class:`curry.ref` : A reference to a named subexpression (a
        keyword argument of :func:`curry.expr`).

        :class:`curry.cons`, :data:`curry.nil` : The cells of a cons-style
        list.

        :data:`curry.fail` : A failure.

        :class:`curry.unboxed` : The unboxed payload of an ``Int``,
        ``Char`` or ``Float``, as in ``[Prelude.Int, curry.unboxed(3)]``.
        A payload that does not fit the primitive, and the marker anywhere
        else, is an error at construction; an item of an iterator is
        refused when the list is demanded.

The errors the package raises are in :mod:`curry.exceptions`.  The errors
of the typed boundary are subclasses of
:class:`curry.exceptions.CurryTypeError`, a ``TypeError``, listed with an
example each under :ref:`the error catalogue <typed-errors>`.  The errors
of an evaluation are subclasses of
:class:`curry.exceptions.EvaluationError`.  ``EvaluationError`` and
:class:`curry.exceptions.CompileError` derive from ``BaseException``, not
from ``Exception``, so ``except Exception`` does not catch them; name the
class in the ``except`` clause.

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
``typed_expr``               ``True``               Whether :func:`curry.expr` types the expression it
                                                    builds.  ``False`` makes it the untyped builder with
                                                    the markers of ``expr``.
``inline_budget``            ``4``                  The largest function body, in nodes built, that the
                                                    optimizer inlines at a call; a call of a single-case
                                                    function on a constructor becomes the branch.  ``0``
                                                    turns both rules off.
``defaultconverter``         ``None``               The converter of :func:`curry.eval` when the call
                                                    names none: ``None`` or ``'topython'``.
``setfunction_strategy``     ``'lazy'``             How set functions evaluate: ``'lazy'`` with set
                                                    guards, ``'eager'`` with the arguments in ground
                                                    normal form first.
``setfunction_failures``     ``'encapsulate'``      What a failure that comes from an argument of a set
                                                    function does when the capsule demands it:
                                                    ``'encapsulate'`` drops its alternative, ``'escape'``
                                                    fails the set function.
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

:mod:`curry.expressions`
    The builders :func:`curry.expr`, :func:`curry.raw_expr`,
    :func:`curry.typeof` and :func:`curry.describe`, and the markers of an
    expression.

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
    expressions of :func:`curry.expr`, and the error catalogue
    (:mod:`curry.typecheck.errors`).

:mod:`curry.utility`
    General-purpose code.
