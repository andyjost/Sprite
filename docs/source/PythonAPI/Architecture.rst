===================
System Architecture
===================

It helps to know a few things about how Sprite is designed.  The sections below
discuss a few of the most important aspects.

Interpreter Object
==================

An :class:`Interpreter <curry.interpreter.Interpreter>` represents one instance
of a Curry system.  It coordinates interactions between the API and the various
subsystems so that Curry code can be compiled, imported, and evaluated.

Each interpreter has a private copy of the :ref:`configuration flags
<interpreter-flags>`, Curry search path, list of imported modules,
signature table, and more.  It also has a reference to a `Backend
Object`_, which implements the backend for whichever target was chosen.

The Global Interpreter
----------------------

As most applications do not require multiple interpreters, Sprite creates a
global interpreter when first imported and lifts its data and methods into the
``curry`` module.  The :ref:`Top-Level API <top-api>` consists mainly of these
objects.  So, for example, :func:`curry.import_` is a method that imports a
Curry module into the global interpreter and :func:`curry.eval` evaluates an
expression according to its settings.

A new interpreter, ``Interpreter(flags={...})``, starts from the default
flags, not from the environment variable ``SPRITE_INTERPRETER_FLAGS``; the
global interpreter reads the variable.


Backend Object
==============

An :class:`IBackend <curry.backends.IBackend>` mediates interactions between
an interpreter and a backend.  A backend has one instance, which every
interpreter that targets it shares; the object is stateless, and the state
of an interpreter lives in an interpreter state the backend attaches to
it.  The backend is ``curry.backends.cxx``, the C++ backend; it implements
the interface in its module ``interface``.

A backend implements the target-specific aspects of compilation and evaluation.
The interface includes the following:

  * **Compilation**

      - ``compile``:
        Converts ICurry to the IR of the backend: generated C++ text.

      - ``materialize``:
        Converts IR to runnable code: the functions of a module.

      - ``write_module``, ``load_module``, ``object_file_extension``:
        The form of a module on disk: the C++ source that :func:`curry.save`
        writes, and the shared object (``.so``) that :func:`curry.load`
        reads.

      - ``extend_plan_skeleton``:
        The steps the backend adds to the compilation pipeline of
        :ref:`sprite-make <sprite-make>`.

      - ``compile_pending``, ``module_loaded``:
        The hooks of a load.  The C++ backend queues the background
        compile of a module it interprets in ``module_loaded`` (tiered
        execution; see :mod:`curry.backends.cxx.tiered`).

  * **Evaluation**

      - ``make_node``:
        Creates one node of a Curry expression graph.

      - ``create_evaluation_rts``:
        Creates the runtime state of one evaluation.

      - ``before_evaluation``, ``after_evaluation``:
        The hooks around an evaluation.  The C++ backend applies the
        objects that finished compiling in the background.

      - ``lookup_builtin_module``, ``fundamental_symbols``:
        The implementations of the external declarations of the built-in
        Curry modules, and the symbols every backend provides.

  * **Statistics and inspection**

      - ``num_collections``, ``gc_seconds``, ``gc_counters``,
        ``tiered_counts``, ``scheduler_counters_enabled``:
        What :func:`curry.stats` reports.  A backend without a collector
        of its own answers zeros.

      - ``getimpl``:
        The generated code of a symbol, for :func:`curry.inspect.getimpl`.

  * **Runtime State**

    Data associated with the evaluation of a Curry expression.  Each call to
    :func:`curry.interpreter.Interpreter.eval` gives rise to a new, unique
    runtime state.  This way, any number of evaluations can occur
    concurrently without interfering with one another.

    This captures the relevant state of the interpreter that
    requested evaluation (such as its configuration flags), and houses the
    necessary data structures, such as the work queue of the Fair Scheme.

  * **Interpreter State**

    The backend attaches a state object to each interpreter to track
    backend-specific information, such as the identifiers of choices and
    free variables, so that no two expressions created by the same
    interpreter share one.  :func:`curry.reset` installs a new state.

The scheduler design is the Fair Scheme.  A queue holds the
configurations, each an alternative of the computation with its
fingerprint of the choices it made.  A step rewrites one redex; a choice
at the root forks the configuration; a free variable that reaches a case
suspends it.  The C++ backend runs the scheduler in the runtime library
``libcyrt`` (``src/cyrt``), with compiled step functions or the bytecode
of its ICurry interpreter.
