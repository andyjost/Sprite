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

Each interpreter has a private copy of the :mod:`configuration flags
<curry.interpreter.flags>`, Curry search path, list of imported modules, and
more.  It also has a reference to a `Context Object`_, which implements the
backend for whichever target architecture was chosen.

The Global Interpreter
----------------------

As most applications do not require multiple interpreters, Sprite creates a
global interpreter when first imported and lifts its data and methods into the
``curry`` module.  The :ref:`Top-Level API <top-api>` consists mainly of these
objects.  So, for example, :func:`curry.import_` is a method that imports a
Curry module into the global interpreter and :func:`curry.eval` evaluates an
expression according to its settings.


Context Object
==============

A :class:`Context <curry.context.Context>` mediates interactions between an
interpreter and backend.  Each context is a singleton with respect to the
backend it represents, which implies that if multiple interpreters target the
same backend, they share one context object.

A backend implements the target-specific aspects of compilation and evaluation.
The context defines an abstract interface to the backend that includes the
following:

  * **Compiler**

    :class:`Compiler <curry.context.Compiler>` provides an abstract interface
    to a target-specific IR and related functions.  Key members include the
    following:

      - :func:`IR <curry.context.Compiler.IR>`:
        A class that represents the target-specific IR.

      - :func:`compile <curry.context.Compiler.compile>`:
        A function that compiles ICurry to IR.

      - :func:`materialize <curry.context.Compiler.materialize>`:
        A function that converts IR to runnable code.

      - :func:`render <curry.context.Compiler.render>`:
        A function that converts IR to a string or bytes.

  * **Runtime**

    :class:`Runtime <curry.context.Runtime>` provides an abstract interface to
    target-specific classes and functions used to evaluate Curry.  Key member
    include the following:

      - :func:`Node <curry.context.Runtime.Node>`:
        A class that represents a Curry expression graph.

      - :func:`InfoTable <curry.context.Runtime.InfoTable>`:
        A class containing compiler-generated information about a symbol.

      - :func:`evaluate <curry.context.Runtime.evaluate>`:
        A function to evaluate a Curry expression.

      - :func:`lookup_builtin_module <curry.context.Runtime.lookup_builtin_module>`:
        A function to find implementations of external declarations in built-in
        Curry modules.


  * **Runtime State**

    Data associated with the evaluation of a Curry expression.  Each call to
    :func:`curry.interpreter.Interpreter.eval` gives rise to a new, unique
    ``RuntimeState``.  This way, any number of evaluations can occur
    concurrently without interfering with one another.

    This captures the relevant state of the interpreter that
    requested evaluation (such as its configuration flags), and houses the
    necessary data structures, such as the the Fair Scheme Work Queue.


  * **Interpreter State**

    The backend defines a data class to be attached to each interpreter
    instance to track backend-specific information.  For example, this may
    track the choice and free variable IDs used to ensure that no two
    expressions created by the same interpreter have overlaping ones.

