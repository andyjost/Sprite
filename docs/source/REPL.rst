.. _repl:

========
The REPL
========

Sprite has a read-eval-print loop for Curry expressions.  It compiles each
expression with ``curry.parse`` and evaluates it with ``curry.solve``.
It prints each converted answer with ``curry.show``.  The same route
serves ``sprite-exec -g`` and the text goals of the Python API, so the
three agree on every goal.

To start the REPL, run ``python -m curry`` with the Python of the
installation, or run ``sprite-exec`` without a program:

.. code-block:: bash

    % install/bin/python -m curry
    Prelude>

``python -m curry.tools.icy`` also starts the same REPL.

The prompt names the loaded module.  The Prelude is loaded at the start.
The REPL runs on the default backend of the installation, the C++ backend,
with the flags of ``SPRITE_INTERPRETER_FLAGS`` (see
:doc:`CommandLineInterface/EnvironmentVariables`).

The REPL runs in time mode by default: the scheduler
rotates its alternatives every 10 ms of wall time, so a diverging
alternative beside a value costs a quantum, not a count of steps.  The
values of a non-deterministic expression may then come in a different
order from one evaluation to the next.  To pin the order, start the REPL in
step mode, where the schedule depends on the expression alone:

.. code-block:: bash

    % SPRITE_ROTATION=steps:65536 install/bin/python -m curry

Run ``python -m curry.tools.icy --help`` for the commands and exit
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
    and of the Prelude, and nothing else: the imports of the module are
    not in scope at the prompt. To use a library at the prompt, define a
    wrapper or re-export the library from the loaded module. Like
    ``curry.import_``, a second load returns the loaded module and warns
    once per edit. Use ``:reload`` to read an edited source again.

``:reload``
    Calls ``curry.reload`` on the current module, replacing its code in
    place. An unsuccessful reload reports its error and keeps the module
    usable with its previous code. The C++ session can refuse replacement
    under ``off``; ``:set interpret new`` resets the session
    in a mode that permits reload.

``:eval EXPR``
    Compiles the expression, evaluates it, and prints each value on a line
    of its own.  Class constraints are defaulted as described below.

``:type EXPR``
    Prints the type of the expression as the front end infers it, with its
    class context and before any defaulting: ``1+2 :: Num a => a``.

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

Commands may also be given on the command line.  Each command starts with
its colon and takes the words that follow it. An error in such a command
ends the REPL with status 1; no value ends it with status 2.  An error at the prompt prints its message
and the loop continues.

.. code-block:: bash

    % install/bin/python -m curry.tools.icy :load Goals.curry :eval main14 :quit
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

An expression without a type annotation keeps the class constraints the
front end inferred.  ``:type`` prints them.  ``:eval`` defaults them with
the table of the PAKCS REPL: ``Num`` and ``Integral`` to ``Int``,
``Fractional`` and ``Floating`` to ``Float``, ``Monad`` to ``IO``, and a
lone ``Data`` to ``Bool`` (the whole table is under
:ref:`goal-defaulting`).

.. code-block:: text

    Prelude> :type 1+2
    1+2 :: Num a => a
    Prelude> 1+2
    3
    Prelude> :type fromIntegral 3
    fromIntegral 3 :: Num a => a
    Prelude> fromIntegral 3
    3

A constraint outside the table is an error.  The message gives the sentence
of the PAKCS REPL and the inferred type.  A type annotation in the
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
    Prelude> x =:= y where x, y free
    {x=x, y=x} True
    Prelude> x where x free
    {x=x} x
    Prelude> :type x where x free
    x where x free :: Data a => a

A comment after ``free`` keeps the variables local to the expression, so
that form prints the value alone.  Write the trailing clause last when
bindings should be reported.  Type annotations belong in Curry text,
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
    Prelude> mapM_ print [1, 2]
    1
    2

Errors in the REPL
==================

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

    % install/bin/python -m curry.tools.icy :eval 'toEnum 65' :quit
    ERROR: cannot handle the overloaded goal toEnum 65 of type Enum a => a
    Cannot handle arbitrary overloaded top-level expressions
    state the type: curry.term(goal, type='T')
    % echo $?
    1

Limits of the REPL
==================

* The prompt sees the loaded module and the Prelude alone.  No command
  imports another module; see ``:load`` above for the two ways around it.
* The REPL imports one module into the prompt at a time.
* ``:type`` keeps the variables of a trailing ``where x free`` in the
  expression, so a type that depends on them alone is ambiguous there,
  while ``:eval`` of the same text prints the bindings.
