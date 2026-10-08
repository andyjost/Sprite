.. _repl:

========
The REPL
========

Sprite has a read-eval-print loop for Curry expressions.  It compiles each
expression with the Curry front end, as :func:`curry.compile` with mode
``'expr'`` does, and evaluates it with :func:`curry.eval`.  The same route
serves ``sprite-exec -g`` and the text goals of the Python API, so the
three agree on every goal.

To start the REPL, run the module ``curry.tools.icy`` with the Python of
the installation:

.. code-block:: bash

    % install/bin/python -m curry.tools.icy
    Prelude>

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

    % SPRITE_ROTATION=steps:65536 install/bin/python -m curry.tools.icy

The REPL has no command-line options of its own; ``-h`` is an illegal
argument.  The interpreter flags come from the environment.

Commands of the REPL
====================

A line that starts with a colon is a command.  Any other line is an
expression, which the REPL evaluates as ``:eval`` does.  A command name may
be any unambiguous prefix, for example ``:e`` for ``:eval`` and ``:t`` for
``:type``.

``:load FILE``
    Compiles and imports the Curry module in ``FILE`` and adds its
    directory to :data:`curry.path`.  The prompt names the module.  The
    expressions of ``:eval`` and ``:type`` see the symbols of that module
    and of the Prelude, and nothing else: the imports of the module are
    not in scope at the prompt, and no command imports another module.
    To use a function of a library at the prompt, define a wrapper in the
    loaded module, or re-export the library from it (``module M (module
    M, module Control.SetFunctions) where``).

``:eval EXPR``
    Compiles the expression, evaluates it, and prints each value on a line
    of its own.  Class constraints are defaulted as described below.

``:type EXPR``
    Prints the type of the expression as the front end infers it, with its
    class context and before any defaulting: ``1+2 :: Num a => a``.

``:set OPTION VALUE``, ``:set [+|-]OPTION``
    Sets an option.  ``:set`` alone lists the options and their state.
    The options are:

    ``backend``
        The backend of the session.  ``:set backend NAME`` switches the
        session to that backend: the interpreter is reloaded and the
        module is loaded again.  If that load fails, the session stays on
        the new backend with the Prelude at the prompt, and the next
        ``:load`` or ``:set backend`` loads the module again.

    ``internal-error-details``
        A Boolean option.  ``:set +internal-error-details`` adds the
        Python traceback to the report of an error during an evaluation;
        ``:set -internal-error-details`` removes it again.

    The other settings of the interpreter, such as ``rotation`` and
    ``interpret``, are not options of ``:set``; they come from
    ``SPRITE_INTERPRETER_FLAGS`` and ``SPRITE_ROTATION`` in the
    environment when the REPL starts.

``:quit``
    Exits.

Commands may also be given on the command line.  Each command starts with
its colon and takes the words that follow it.  An error in such a command
ends the REPL with the status 1.  An error at the prompt prints its message
and the loop continues.

.. code-block:: bash

    % install/bin/python -m curry.tools.icy :load Goals.curry :eval main14 :quit
    Just 5

A session with a module
=======================

The transcript below is the part of one session that lists the options
and loads a module.
``Goals.curry`` holds ``double x = x + x`` and ``main14 = Just 5``.  The
sections that follow quote the other exchanges of the same session.

.. code-block:: text

    Prelude> 1 ? 2
    1
    2
    Prelude> :set
    Usage:
        :set <option> <value>
        :set [+/-]<option>        (Boolean options only)

    Options for ":set" command:
        backend                  - The backend of the session.  Setting it reloads the interpreter and the loaded module.
        internal-error-details   - Show detailed information about internal errors.

    Current settings:
    -internal-error-details
    backend : 'cxx'
    Prelude> :load Goals.curry
    Goals> double 21
    42
    Goals> :t double 21
    double 21 :: Num a => a
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
    **** ERROR ****
    cannot handle the overloaded expression 'toEnum 65' of type Enum a => a
      Cannot handle arbitrary overloaded top-level expressions
      add a type annotation (exprtype)
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

A trailing ``where x free`` declares free variables, as in PAKCS.  A
variable whose type is absent from the result type cannot show in a value,
so ``:eval`` prints its binding with each value.  A variable whose type
occurs in the result type is left in the value.

.. code-block:: text

    Prelude> xs ++ [3] =:= [1,2,3] where xs free
    {xs=[1, 2]} True
    Prelude> x =:= y where x, y free
    {x=_a, y=_a} True
    Prelude> x where x free
    _a
    Prelude> :type x where x free
    x where x free :: Data a => a

``:type`` does not lift the variables to parameters, on either system.  So
``:type x =:= y where x, y free`` fails in the front end with an ambiguous
type variable, while ``:eval`` of the same text prints
``{x=_a, y=_a} True``.

IO goals in the REPL
====================

A goal of type ``IO t`` runs during the evaluation.  The REPL prints the
result of the action, so ``putStrLn "x"`` prints ``x`` and then ``()``,
where PAKCS prints ``x`` alone.  A ``Monad`` constraint defaults to ``IO``,
so ``return 5`` runs as ``IO Int`` and prints ``5``.

.. code-block:: text

    Prelude> :type return 5
    return 5 :: (Monad a, Num b) => a b
    Prelude> return 5
    5
    Prelude> putStrLn "x"
    x
    ()
    Prelude> mapM_ print [1, 2]
    1
    2
    ()

Errors in the REPL
==================

An error prints ``**** ERROR ****`` and its message on the standard error.
A compile error shows the command line of the front end and its report.
An error during an evaluation says so; ``:set +internal-error-details``
adds the Python traceback.  On the command line, an error ends the REPL
with the status 1:

.. code-block:: bash

    % install/bin/python -m curry.tools.icy :eval 'toEnum 65' :quit
    **** ERROR ****
    cannot handle the overloaded expression 'toEnum 65' of type Enum a => a
      Cannot handle arbitrary overloaded top-level expressions
      add a type annotation (exprtype)
    % echo $?
    1

Limits of the REPL
==================

* The prompt sees the loaded module and the Prelude alone.  No command
  imports another module; see ``:load`` above for the two ways around it.
* The REPL has no command-line options.  The interpreter flags, among them
  ``rotation`` and ``interpret``, come from the environment, and ``:set``
  has the two options listed above.
* ``:type`` keeps the variables of a trailing ``where x free`` in the
  expression, so a type that depends on them alone is ambiguous there,
  while ``:eval`` of the same text prints the bindings.
