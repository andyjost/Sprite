.. highlight:: bash

Environment Variables
=====================

User Variables
--------------

Sprite's behavior can be controlled by setting certain environment variables.
The following variables are recognized:

``CURRYPATH``
  A colon-separated list of paths used to search for Curry modules.  Sprite
  always appends the path to its own Curry library.

``SPRITE_INTERPRETER_FLAGS``
  Overrides default flags in Sprite's Curry interpreter.  This can be set to a
  comma-separated list of colon-separated pairs (without spaces).  Use the
  following command to see a list of all flags::

      python -c 'import curry; help(curry.interpreter.Interpreter)'

  Example::

     SPRITE_INTERPRETER_FLAGS=trace:True,debug:True

``SPRITE_LOG_FILE``
  The file to which logging output is directed.  The default, ``-``, directs
  output to the standard output stream.

``SPRITE_LOG_LEVEL``
  Set the logging verbosity.  The following values are supported; each
  includes all output from levels listed above it:

  - ``CRITICAL`` Log only critical (usually fatal) problems.
  - ``ERROR``    Log errors.
  - ``WARNING``  (Default) Log warnings.
  - ``INFO``     Log information about what Sprite is doing.
  - ``DEBUG``    Log detailed information about everything.


Developer Variables
-------------------

Additional environment variables aimed at development are recognized.  These
are intended for people developing Sprite itself.  If you plan only to compile
and run Curry programs with Sprite, then you should not need these.  They are:

``SPRITE_CACHE_FILE``
  Specifies the cache database file, which stores the results of slow
  conversions that occur in compiling Curry code.  This is used primarily
  to speed up development, when the same programs are run many times.
  If set to the empty string, caching is disabled.

  The default cache file is ``$HOME/.sprite/cache.db``, though this can be
  changed at configuration time.

  .. note ::
     Caching is disabled by default.  It can be enabled when running
     ``configure`` or by editing ``Make.config`` afterwards.

``SPRITE_CACHE_UPDATE``
  Specifies cache entries to update.  Updates can become necessary when part of
  the build pipeline undergoes a non-backward-compatible change.  For instance,
  if the tool converting Curry to ICurry is updated and gives a new output
  (because, say, the Prelude has changed), then the old cache files will be
  out of date.  It is fine to simply delete the cache file in that case, but
  this variable provides a less extreme option.

  Files matching the pattern will be forced out-of-date and therefore updated
  in the cache.  The value is a glob pattern unless it begins and ends with
  '/', as in ``/pattern/``, in which case it is a regular expression.

  Example:

      To update all intermediate JSON files, set
      ``SPRITE_CACHE_UPDATE='*.json.gz'`` in the environment.

``SPRITE_CATCH_ERRORS``
  Sets a breakpoint whenever a specified error type is created.  The value is a
  comma-separated list of Python exception names.  For example, the value
  ``"AssertionError,RuntimeError"`` will cause an interactive prompt to start
  whenever either of those exceptions occurs.

``SPRITE_DEBUG``
  Enables features to debug internal errors within Sprite itself.  The
  command-line tools ``sprite-exec`` and ``sprite-make`` normally report
  unexpected errors tersely.  Enabling this allows one to see the full stack
  trace when Sprite fails.  Set this to the value ``1`` to enable.
