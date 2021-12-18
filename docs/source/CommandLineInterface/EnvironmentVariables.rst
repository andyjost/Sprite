.. highlight:: bash

Environment Variables
=====================

User Variables
--------------

Sprite's behavior can be controlled by setting certain environment variables.
The following are recognized:

``CURRYPATH``
  A colon-separated list of paths used to search for Curry modules.  Sprite
  silently appends to this the path to its system libraries.

``SPRITE_INTERPRETER_FLAGS``
  Overrides default flags in Sprite's Curry interpreter.  This can be set to a
  comma-separated list of colon-separated pairs (without spaces).

  See the :mod:`list of flags <curry.interpreter.flags>` for details.

  For example, to have Sprite generate debug code and print execution traces,
  set the following::

     SPRITE_INTERPRETER_FLAGS=trace:True,debug:True

``SPRITE_LOG_FILE``
  The file to which logging output is directed.  The default, ``-``, directs
  this to standard output.

``SPRITE_LOG_LEVEL``
  Sets the logging verbosity.  The **default** level is ``WARNING``.  Supported
  values are:

  - ``CRITICAL`` Log only critical (usually fatal) problems.
  - ``ERROR``    Log errors.
  - ``WARNING``  Log warnings.
  - ``INFO``     Log information about what Sprite is doing.
  - ``DEBUG``    Log detailed information about everything.

  Each of these includes all output from levels listed above it.

Development Variables
---------------------

Additional environment variables are recognized.  These are intended for people
developing Sprite itself.  If you plan only to compile and run Curry programs
with Sprite, then you should not need these.

``SPRITE_CACHE_FILE``
  Specifies the cache database file.  The cache database stores the results of
  slow conversions that occur when compiling Curry, especially the conversions
  from :ref:`Curry to ICurry <Introduction/CompilationPipeline:Curry to
  ICurry>` and :ref:`ICurry to Sprite's in-memory IR
  <Introduction/CompilationPipeline:JSON to Sprite IR>`.  This aims to
  shorten the development cycle when the same programs are compiled and run
  many times.  If set to the empty string, caching is disabled.

  The default cache file is ``$HOME/.sprite/cache.db``, though this can be
  changed at configuration time.

  .. note ::
     Caching is disabled by default.  It can be enabled when running
     ``configure`` or by editing ``Make.config`` afterwards.

``SPRITE_CACHE_UPDATE``
  Specifies cache entries to update.  Updates can become necessary when part of
  the build pipeline undergoes a non-backward-compatible change.  If, for
  instance, the tool converting Curry to ICurry is updated and gives a new
  output (because, say, the Prelude has changed), then the old cache files will
  be out of date.  It is fine to simply delete the cache file in that case, but
  this method provides a more conservative option.

  Files matching the given pattern are updated in the cache database.  The
  pattern is interpreted as a glob unless it begins and ends with '/', as in
  ``/pattern/``, in which case it is considered a regular expression.

  Example:

      To update all compressed JSON files, set
      ``SPRITE_CACHE_UPDATE='*.json.gz'`` in the environment.

``SPRITE_DEBUG``
  Enables debugging for Sprite internal errors.  The command-line tools
  :ref:`sprite-exec` and :ref:`sprite-make` normally report unexpected errors
  tersely.  Enabling this allows one to see the full stack trace when Sprite
  fails.  Set this to the value ``1`` to enable debugging.
