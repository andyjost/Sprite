.. highlight:: bash

Step-by-step build
------------------

Use this method for more control over the build process.

Step 1: Initialize submodules
.............................

You must initialize and update the GIT submodules before building::

    git submodule init
    git submodule update

Step 2: Overlay ICurry files
............................

To overlay the pre-built ICurry files of the test programs, say::

    make overlay


If you plan to run the test suite, this step **saves several hours** by
avoiding hundreds of Curry-to-ICurry conversions.  See :ref:`important-notes`.

To use this, your version of PAKCS must match one of the ``overlay*.tgz``
files at the repository root.

Step 3: Build objects and libraries
...................................

To build object files, static libraries, and shared libraries say::

    make objs libs shlibs

Step 4: Stage
.............

To stage Sprite say::

    make stage

This must be done before tests are run.  It creates a mock installation under
``install/``.  This step also builds the necessary objects and libraries, so
you can skip the previous two steps if you like.  Staging also compiles the
Curry library for both backends into the installation, so that the first
import compiles nothing.  Most of that time goes to the Prelude of the C++
backend, about half a minute.  A stage that changes nothing skips it.
``make stage`` runs with the job count of ``configure --jobs``.  Say
``make -jN stage`` to use another count for one run.

Step 5: Test (optional)
.......................

To run the tests, say::

    make test

You can also say ``cd tests && ./run_tests``.  See tests/README for fine
control of testing.

Step 6: Install (optional)
..........................

You can use Sprite directly from the staging area.  If you prefer to install it
elsewhere, use ``make install`` while setting PREFIX to the desired location.

To install Sprite under ``/path/to/sprite`` say::

    make install PREFIX=/path/to/sprite

Refer to the :ref:`install tree layout <install-tree-layout>` for the
directories this creates.


