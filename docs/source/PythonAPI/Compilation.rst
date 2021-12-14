===========
Compilation
===========

Static Compilation
==================

Dynamic Compilation
===================

Curry definitions can be created with ``curry.compile``:

    >>> Fib = curry.compile(
    ...     '''
    ...     fib :: Int -> Int
    ...     fib n | n < 3 = 1
    ...           | True  = (fib (n-1)) + (fib (n-2))
    ...     '''
    ...   , modulename='Fib'
    ...   )

The above is equivalent to to placing the code into a file ``Fib.curry`` and
importing it.

.. note::

    Sprite dedents leading whitespace common to every line, so Curry code can
    be formatted in blocks, as shown above.

