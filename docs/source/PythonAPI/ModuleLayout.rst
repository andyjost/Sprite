=====================
The ``curry`` Package
=====================

This section gives a high-level view of the ``curry`` package.  The intent
is to give readers some idea of where various bits of Sprite can be located.

Top-Level API
=============

The ``curry`` module itself serves as a collection of classes and functions
intended to carry out the most common tasks.  Many of these are methods of a
singleton Curry interpreter that is created when importing ``curry``.  For many
common use cases, one can simply use these methods without ever thinking about
an interpreter, let alone creating one.

The global interpreter can be obtained by calling :func:`curry.getInterpreter`.

The top-level data and methods fall roughly into the following four categories:

  - **System Control**

    These can be used to manipulate the global interpreter:

        :data:`curry.flags`  : Set options on the global interpreter.

        :data:`curry.path`   : Configure or view the Curry search path.

        :func:`curry.reload` : Discard the global interpreter, then create a new one.

        :func:`curry.reset`  : Soft-reset the global interpreter.

    Also, see the :mod:`curry.config` module.

  - **Symbols & Types**

    These can be used to find Curry objects.

        :func:`curry.module` : Find a module by name.

        :func:`curry.symbol` : Find a symbol by name.

        :func:`curry.type`   : Find a type by name.

        :func:`curry.currytype` : Get the Curry type that corresponds to a Python type.

  - **Curry Modules**

    These can be used to create, transform, load, or save Curry code.

        :func:`curry.compile` : Create Curry modules (with mode 'module').

        :func:`curry.import_` : Import a Curry module by name.

        :func:`curry.load`    : Load a ``.py`` file containing a compiled Curry module.

        :func:`curry.save`    : Save a ``.py`` file containing a compiled Curry module.

        :data:`curry.modules` : Access imported modules.

  - **Expressions & Evaluation**

    These can be used to build and evaluate Curry expressions.

        :func:`curry.compile` : Create Curry expressions (with mode 'expr').

        :func:`curry.eval`    : Evaluate a Curry goal.

        :func:`curry.expr`    : Construct a Curry expression.

Package Structure
=================

The contents of the ``curry`` package are documented in detail in the
:ref:`reference-material`.  The major submodules are described briefly below.

:mod:`curry.backends`
    Implementations of the available compiler and runtime backends.

:mod:`curry.cache`
    Implements caching for Curry-to-ICurry and other conversions.

:mod:`curry.common`
    Contains common definitions used throughout Sprite.

:mod:`curry.config`
    Functions for interacting with Sprite's system configuration.

:mod:`curry.context`
    Defines the context object.

:mod:`curry.exceptions`
    Contains all non-built-in exceptions Sprite might raise.

:mod:`curry.icurry`
    A Python implementation of ICurry, which serves as the Sprite IR.

:mod:`curry.inspect`
    A module for inspecting Curry objects.

:mod:`curry.interpreter`
    Defines the Curry interpreter.

:mod:`curry.lib`
    A virtual package used as the base for importing Curry modules.

:mod:`curry.objects`
    Defines the objects used to provide Python APIs to Curry objects.  For instance,
    this defines :class:`curry.objects.CurryModule`, which is the object created by importing a
    Curry module.

:mod:`curry.show`
    Code for converting Curry expressions to strings.

:mod:`curry.toolchain`
    Contains code for manipulating the :ref:`compilation pipeline
    <Introduction/CompilationPipeline>`.  Driver functions for external
    programs used by Sprite can be found here.

:mod:`curry.tools`
    Defines the command-line tools that come with Sprite.  This is where the
    source for :ref:`sprite-make` can be found.  :ref:`sprite-exec` is defined in the
    ``__main__.py`` file for ``curry``.  This, incidentally, means that running
    ``python -m curry`` from a command prompt is a synonym for :ref:`sprite-exec`.

:mod:`curry.utility`
    General-purpose code.
