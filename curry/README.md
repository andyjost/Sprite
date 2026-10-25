The Curry library
=================

This directory holds the Curry library that ships with Sprite.

`lib/` contains the sources.  They are a copy of the library of PAKCS 3.10.0,
which is version 3.4.0 of the Curry package `base`, plus Sprite's own modules
`Control.SetFunctions` and `Sprite.Stream`.  `lib/LICENSE` is the license
of the origin.
`lib/NOTICE` names the origin, the version, and the changes.  The Prelude
carries a three-line prefix that defines `__KICS2__`; NOTICE explains why.
The same sources compile with front end 2.0.0 (PAKCS macro 304) and
front end 3.1.0 (PAKCS macro 310). No upstream backend files are shipped.

`make stage` copies the sources, LICENSE, and NOTICE to `$(PREFIX)/curry`.
Sprite appends that directory to the Curry path, so the front end and the
toolchain find the library there and never read the PAKCS library.  The
install also runs the front end once over every module.  That writes the
FlatCurry interfaces under `$(PREFIX)/curry/.curry/pakcs-<ver>/`, so the
front end reads them later and never writes into the installation tree.
(The compiled forms of every module are written at install time; see
below.) The overlay archive packs the interfaces from the staged library
for the oracle tests.

The text shim in `oracle/Sprite/Stream.curry` gives PAKCS and KiCS2 the
same module name and signature for stream programs. Put `oracle/` first
on their Curry path. Sprite uses the runtime primitive under `lib/`.

Pinned build products
---------------------

Beside eight of the sources sit committed `.icy` (ICurry) and `.json.z`
(compressed ICurry-JSON) files.  They are build products of the pinned PAKCS
front end 3.1.0 (PAKCS 3.10.0), regenerated with Sprite's port.
In compatibility mode the port is byte-identical to `icurry` 3.3.0; the
independent references are in `overlay-pakcs-3.10.0.tgz`.  `make install` copies them to
`$(PREFIX)/curry/<package>/.curry/sprite-pakcs-<ver>/`.  With front end 3.1.0 the build never
rebuilds a committed `.icy` file unless `SPRITE_REBUILD_ICY` is set.
The legacy pair, front end 2.0.0 with PAKCS 3.4.1, compiles the
library from source at stage time; its pinned products are no longer committed.  A
committed `.icy` file is kept even when its source has a newer time stamp.
The `.json.z` file is derived from the `.icy` file when it is older.

The other modules have no committed products. The build compiles the library
in its staging image: `sprite-make --json` writes the `.icy` and `.json.z`
files of every module, and `sprite-make --so` compiles every supported
module for the C++ runtime. So the first use of Sprite
compiles nothing, and a user without the privileges of the installer needs
no compile.

Thirteen modules are left out of that compile (the `unsupported` list
in `CMakeLists.txt`).  Seven have externals that no backend
implements, or import such a module: `Curry.Compiler.Distribution`,
`Data.IORef`, `Debug.Trace`, `System.CPUTime`, `System.Environment`,
`System.IO`, and `System.IO.Unsafe`.  `Test.Prop` is a module and a package
and imports its own submodule `Test.Prop.Types`, which the importer cannot
load (see TODO). The four `Control.Search.*` modules need strong
encapsulation and search-tree primitives that Sprite does not yet implement.
A program that imports one of them fails when Sprite
compiles it.  Their ICurry and JSON are installed all the same, and the
front end reads their interfaces.

Rebuilding the products
-----------------------

A build with front end 3.1.0 and PAKCS 3.10.0 regenerates the pinned products.
From the project root:

    make stage SPRITE_REBUILD_ICY=1

This writes fresh products in the build's `stage/curry/` image and copies
them into the installation. Copy the eight pinned `.icy` and `.json.z`
files back beside their sources, from their `.curry/sprite-pakcs-3.10.0/`
directories in that image. Check the `.icy` bytes against `icurry` 3.3.0
before replacing the committed products. A build with front end 2.0.0
compiles the library from source and never uses the pinned products.
As with other source modules, an incremental stage keeps valid products.

`sprite-make --icy` compiles a module with the configured route from Curry
to ICurry: the front end plus Sprite's translation by default, or `icurry`
with `SPRITE_CURRY2ICURRY=icurry`.

After a change to the ICurry reader, regenerate the pinned `.json.z` files
as well. The JSON is derived from the ICurry, rather than translated by
the upstream compiler.

Updating the library
--------------------

Copy the `.curry` files of the new PAKCS `lib` directory over `lib/`.  Add
the prefix to `Prelude.curry`.  Update `lib/NOTICE`.  Rebuild the pinned
products and run the tests.  `tests/unit_currylib.py` pins the sources of the
eight modules by hash; update the hashes there.
