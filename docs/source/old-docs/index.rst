The Sprite Curry System
=======================

`Sprite`_ is a compiler and runtime for Curry programs.  It is based on the
`Fair Scheme`_, a compilation strategy for transforming declarative,
non-deterministic source programs into imperative, deterministic code.  As the
Fair Scheme emphasizes operational completeness, Sprite aims to produce all
values of Curry programs, subject only to practical limits such as the amount
of memory available.

CurryPy
-------

CurryPy provides access to a complete Curry system from Python.  Curry code can
be embedded in Python or separately compiled and loaded at runtime.  An
instance of Sprite evaluates Curry expressions while Python generators maintain
laziness when crossing the language boundary in either direction.

.. code-block:: python

    import curry
    # Compile Curry code.
    Triples = curry.compile(
        '''
          -- Generate Pythagorean triples.
          getTriples :: (Int, Int, Int)
          getTriples = anyOf (map triple [0..])
            where triple c | a*a + b*b == c*c = (a,b,c) where a,b free

        '''
      , modulename='Triples'
      )
    # Use the results in Python.
    for (a,b,c) in curry.eval(Triples.getTriples):
      print 'Got triple {a}**2 + {b}**2 = {c}**2'.format(locals())
      if c > 10:
        break # Lazy evaluation.

.. _Sprite: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr16/paper.pdf
.. _Fair Scheme: https://web.cecs.pdx.edu/~antoy/homepage/publications/lopstr13/long.pdf
.. _Flask: https://flask.palletsprojects.com/
.. _TensorFlow: https://www.tensorflow.org/

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   quickstart
   currypy
   Technical Documentation <implementation/index>

.. Search
.. ======
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

