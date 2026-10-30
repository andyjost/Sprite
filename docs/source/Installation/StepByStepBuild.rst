.. highlight:: bash

Step-by-step build
------------------

Initialize the two submodules the build needs, the Python binding and the
big-integer library::

    git submodule update --init extern/pybind11 extern/libtommath

Configure and build with CMake, or use the thin wrapper::

    make stage

This configures ``object-root/cmake`` with Ninja, builds the runtime and
extension, prepares the Curry library with the package's own tools, and
installs into ``install/``. The library includes its pinned ICurry,
interfaces, JSON and runtime products. Pinned ICurry is rebuilt
only when ``SPRITE_REBUILD_ICY`` is enabled for the default pair, front end
3.1.0 with PAKCS 3.10.0. The legacy pair (2.0.0 with 3.4.1) builds its
library products from source. See :doc:`ConfiguringSprite`
for options. ``make stage JOBS=4`` or ``make -j4 stage`` limits parallelism.

Extract the test products after staging::

    make overlay

The extracted products must be newer than the installed interfaces. A plain
``make`` stages and then extracts them. ``make overlay V=1`` lists members.
See :ref:`important-notes` for the archive and the test oracle.

Run the tests::

    cd tests
    ./run_tests --prepare-only --backend cxx
    ./run_tests --backend cxx

To install the prepared tree elsewhere::

    cmake --install object-root/cmake --prefix /path/to/sprite

``make install PREFIX=/path/to/sprite`` also builds first. See the
:ref:`install tree layout <install-tree-layout>` for the resulting tree.
