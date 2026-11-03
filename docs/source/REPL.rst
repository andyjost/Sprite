.. _repl:

========
The REPL
========

Sprite has a read-eval-print loop for Curry expressions.  It compiles each
expression with ``curry.parse`` and evaluates it with ``curry.solve``.
It prints each converted answer with ``curry.show``.  The same route
serves ``sprite-exec -g`` and the text goals of the Python API, so the
three agree on every goal.

To start the REPL, run ``sprite`` or ``python -m curry`` with the Python of
the installation. ``sprite-exec`` without a program also starts it. From a checkout,
use ``install/bin/python -m curry``:

.. code-block:: bash

    python -m curry
    Prelude>

``python -m curry.tools.repl`` also starts the same REPL.

Command line
------------

Commands may follow the executable. They run without a banner or prompt;
execution stops at the first error. Arguments after ``--`` are available
through ``System.Environment.getArgs``::

    sprite --nocypm --noreadline :set v0 :load Main :eval main :quit -- one two
    python -m curry :load Main :save :quit
    ./Main -- one two

``:save`` writes an executable with the loaded module's name in the current
directory. It carries compiled objects for imports that have no usable installed
object, including replacement library modules and stale library importers.
Imports with usable installed objects come from the Sprite installation.
The executable can be moved and run from another directory without
``CURRYPATH`` or the original sources.
``getProgName`` returns the executable's basename, including after a rename.
Its default main expression is ``main``; ``:save EXPR`` chooses
another expression. The executable uses the installed Sprite runtime.
``sprite --compiler-name --numeric-version --base-version`` prints the system
name, its three-part version, and its base library version on separate lines.
Each probe also works separately and together with startup options such as
``--nocypm`` and ``--noreadline``.

These PAKCS options are accepted in addition to Sprite's session flags:

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Option
     - Meaning in Sprite
   * - ``--nocypm``
     - Accepted; Sprite does not invoke CPM at startup. CPM supplies CURRYPATH.
   * - ``--noreadline``
     - Accepted; no readline initialization is required.
   * - ``-q``
     - Accepted; command-line execution has no startup banner.
   * - ``:set v0`` through ``:set v4``
     - Record session verbosity. Results and errors print at every level.
       Compilation progress is controlled by Sprite's logging settings.
   * - ``:set -time``, ``:set +time``
     - Record the setting; PAKCS timing output is omitted.
   * - ``:set parser -Wnone``
     - Accepted; no additional parser warning output is requested.
   * - ``:set rts -T``
     - Accepted; GHC runtime statistics do not apply to Sprite.
   * - ``:set path "PATH"``
     - Prepend the search path to the session's Curry path.
   * - ``:set args ARGS``
     - Set the program arguments, using shell quoting.

Unknown options are errors. Successful commands exit 0, errors and suspended
computations exit 1, and evaluation without a value exits 2. At the interactive
prompt, errors keep the session open; ``:quit`` returns the last status.

The prompt names the loaded module.  The Prelude is loaded at the start.
The REPL runs on the C++ runtime with the flags of ``SPRITE_INTERPRETER_FLAGS`` (see
:doc:`CommandLineInterface/EnvironmentVariables`).

Values of a nondeterministic expression may come in another order from
run to run. To pin the order, start in step mode
(:ref:`sprite-interpreter-flags`):

.. code-block:: bash

    SPRITE_ROTATION=steps:65536 python -m curry

Run ``python -m curry.tools.repl --help`` for the commands and exit
statuses. Interpreter flags come from the environment and may be changed
with ``:set``.

Commands of the REPL
====================

A line that starts with a colon is a command.  Any other line is an
expression, which the REPL evaluates as ``:eval`` does.  A command name may
be any unambiguous prefix, for example ``:e`` for ``:eval`` and ``:t`` for
``:type``. Expressions keep their whitespace, including spaces inside
strings.

``:load FILE``
    Compiles and imports the Curry module in ``FILE`` and adds its
    directory to :data:`curry.path`.  The prompt names the module.  The
    expressions of ``:eval`` and ``:type`` see the symbols of that module
    and of the Prelude and nothing else: the imports of the module are
    not in scope at the prompt. To use a library at the prompt, define a
    wrapper or re-export the library from the loaded module. Like
    ``curry.import_``, a second load returns the loaded module and warns
    once per edit. Use ``:reload`` to read an edited source again.

``:reload``
    Loaded modules are served from memory until reload or reset.
    Calls ``curry.reload`` on the current module, replacing its code in
    place. An unsuccessful reload reports its error and keeps the module
    usable with its previous code. Under ``interpret:off`` the runtime can refuse replacement; ``:set interpret new`` resets the session
    in a mode that permits reload.

``:eval EXPR``
    Compiles the expression, evaluates it and prints each value on a line
    of its own.  Class constraints are defaulted as described below.

``:type EXPR``
    Prints the type of the expression as the front end infers it, with its
    class context and before any defaulting: ``1 + 2 :: Num a => a``.

``:set OPTION VALUE``, ``:set [+|-]OPTION``
    Sets a session flag using the same names and validator as
    ``curry.reset``. ``:set`` alone lists all flags and their current
    values. Boolean flags also take ``+`` or ``-``; for example,
    ``:set +checker``. Examples with values are ``:set rotation steps:200``
    and ``:set inline_budget 0``. An unknown flag raises the ``FlagError``
    sentence. Changing a flag resets the interpreter with the current
    settings plus the new value, then loads the session's module again.
    If that load fails, the prompt returns to Prelude and reports the
    error. A later ``:load`` or ``:set`` may retry it.

``:quit``
    Exits with the last evaluation status (initially 0). EOF does the same.

Commands can also be given on the command line. Each starts with its
colon and takes the words that follow it. For example:

.. code-block:: bash

    python -m curry.tools.repl :load Goals.curry :eval main14 :quit
    Just 5

A session with a module
=======================

``Goals.curry`` holds ``double x = x + x`` and ``main14 = Just 5``:

.. code-block:: text

    Prelude> 1 ? 2
    1
    2
    Prelude> :load Goals.curry
    Goals> double 21
    42
    Goals> :t double 21
    double 21 :: Num a => a
    Goals> :reload
    Goals> :quit

Defaulting in the REPL
======================

An expression without a type signature keeps the class constraints the
front end inferred.  ``:type`` prints them.  ``:eval`` defaults them with
the table of the PAKCS REPL: ``Num`` and ``Integral`` to ``Int``,
``Fractional`` and ``Floating`` to ``Float``, ``Monad`` to ``IO`` and a
lone ``Data`` to ``Bool`` (the whole table is under
:ref:`goal-defaulting`).

.. code-block:: text

    Prelude> :type 1 + 2
    1 + 2 :: Num a => a
    Prelude> 1 + 2
    3
    Prelude> :type fromIntegral 3
    fromIntegral 3 :: Num a => a
    Prelude> fromIntegral 3
    3

A constraint outside the table is an error.  The message gives the sentence
of the PAKCS REPL and the inferred type.  A type signature in the
expression resolves it.

.. code-block:: text

    Prelude> toEnum 65
    ERROR: cannot handle the overloaded goal toEnum 65 of type Enum a => a
    Cannot handle arbitrary overloaded top-level expressions
    state the type: curry.term(goal, type='T')
    Prelude> toEnum 65 :: Char
    'A'

An expression that the front end rejects, such as ``show []`` with its
ambiguous type variable, prints the report of the front end, as PAKCS
does.

A goal of a loaded module without a type signature is defaulted the same
way.  With ``main14 = Just 5`` in ``Goals.curry``:

.. code-block:: text

    Goals> :type main14
    main14 :: Num a => Maybe a
    Goals> main14
    Just 5

Free variables in the REPL
==========================

A trailing ``where x free`` declares named variables, as in PAKCS.
The REPL uses ``curry.solve`` and prints every declared variable with each
value.  A variable that remains free is bound to itself; variables that
unify share a name in the answer.

.. code-block:: text

    Prelude> xs ++ [3] =:= [1,2,3] where xs free
    {xs=[1,2]} True
    Prelude> (x :: Int) =:= y where x, y free
    {x=x, y=x} True
    Prelude> x where x free
    {x=x} x
    Prelude> :type x where x free
    x where x free :: Data a => a

Write the trailing clause last to report bindings. To print the value
without bindings, declare the variable in the module instead.  Type annotations belong in Curry text,
before the trailing clause.  A type query does not add the binding tuple:
``:type x =:= y where x, y free`` still fails in the front end with the
ambiguous type ``Data a => Bool``.

IO goals in the REPL
====================

A goal of type ``IO t`` runs during evaluation. The REPL prints the result
with ``curry.show``, except that ``IO ()`` prints no result line. A
``Monad`` constraint defaults to ``IO``, so ``return 5`` prints ``5``.

.. code-block:: text

    Prelude> :type return 5
    return 5 :: (Monad a, Num b) => a b
    Prelude> return 5
    5
    Prelude> putStrLn "x"
    x
    Prelude> mapM_ print [1,2]
    1
    2

Exit statuses
=============

An error prints ``ERROR: msg`` on standard error, without a traceback.
A compile error prints the front end's first error line without a machine
path. A suspension prints ``*** Evaluation suspended!`` on standard error.
Both have status 1. A search without a value prints
``*** No value found!`` on standard output, with status 2. Success has
status 0, including an ``IO ()`` action whose result line is suppressed.

A command-line error ends the process. At the prompt the session continues;
``:quit`` and EOF return the status of the last evaluation. A successful
subsequent evaluation clears an earlier failure. Type and load commands
keep that status. For example:

.. code-block:: bash

    python -m curry.tools.repl :eval 'toEnum 65' :quit
    ERROR: cannot handle the overloaded goal toEnum 65 of type Enum a => a
    Cannot handle arbitrary overloaded top-level expressions
    state the type: curry.term(goal, type='T')

CurryCheck uses the private ``bin/curry`` launcher of the Sprite installation
as this same REPL, and ``bin/cleancurry`` to remove Sprite products of named
modules. With no module arguments, ``cleancurry`` removes Sprite products in
the current directory. Products of other Curry compilers are preserved.
These launchers are installation resources, not wheel console scripts.

The ``frontend-exec`` dependency of CurryCheck also derives
``bin/sprite-frontend`` from the compiler name. This private adapter forwards
to Sprite's configured Curry front end with its normal compatibility flags.
