The Curry library
=================

This directory holds the Curry library that ships with Sprite.

`lib/` contains the sources.  They are a copy of the library of PAKCS 3.4.1,
which is version 3.1.0 of the Curry package `base`, plus Sprite's own module
`Control.SetFunctions`.  `lib/LICENSE` is the license of the origin.
`lib/NOTICE` names the origin, the version, and the changes.  The Prelude
carries a three-line prefix that defines `__KICS2__`; NOTICE explains why.

`make install` copies the sources, LICENSE, and NOTICE to `$(PREFIX)/curry`.
Sprite appends that directory to the Curry path, so the front end and the
toolchain find the library there and never read the PAKCS library.  The
install also runs the front end once over every module.  That writes the
FlatCurry interfaces under `$(PREFIX)/curry/.curry/pakcs-<ver>/`, so the
front end reads them later and never writes into the installation tree.
(The compiled forms of every module are written at install time; see
below.)  `make -C curry interfaces` writes the same files under `lib/.curry/`
in the source tree; the overlay archive packs them for the oracle tests.

Pinned build products
---------------------

Beside eight of the sources sit committed `.icy` (ICurry) and `.json.z`
(compressed ICurry-JSON) files.  They are build products of the pinned PAKCS
front end and of `icurry` 3.1.0; Sprite's own translation writes the same
bytes.  `make install` copies them to
`$(PREFIX)/curry/<package>/.curry/sprite-pakcs-<ver>/`.  The build never
rebuilds a committed `.icy` file unless `SPRITE_REBUILD_ICY` is set.  A
committed `.icy` file is kept even when its source has a newer time stamp.
The `.json.z` file is derived from the `.icy` file when it is older.

The other modules are installed as sources only.  The install then compiles
every module for both backends (the `prebuild` target of the Makefile in
this directory): `sprite-make --py` and `sprite-make --so` run over the
installed library, so the first use of Sprite compiles nothing, and a user
without the privileges of the installer needs no compile.  A module shipped
as source only gets its `.icy` and `.json.z` files in the installation at
that point.  `make uninstall` removes the products.

Rebuilding the products
-----------------------

A staged installation is needed, because the rules call
`$(PREFIX)/bin/sprite-make`.  From the project root:

    make stage
    SPRITE_REBUILD_ICY=1 make -C curry icy   # compiles every module to ICurry
    make -C curry json                       # derives the JSON files
    make -C curry clean-currylib             # removes the scratch directories

`sprite-make --icy` compiles a module with the configured route from Curry
to ICurry: the front end plus Sprite's translation by default, or `icurry`
with `SPRITE_CURRY2ICURRY=icurry`.

The targets `icy` and `json` cover every module under `lib/`.  Keep the
products you want to pin and remove the others.  After a change to the
ICurry reader, delete the `.json.z` files and run `make stage`; the JSON is
derived from the committed `.icy` files.

Updating the library
--------------------

Copy the `.curry` files of the new PAKCS `lib` directory over `lib/`.  Add
the prefix to `Prelude.curry`.  Update `lib/NOTICE`.  Rebuild the pinned
products and run the tests.  `tests/unit_currylib.py` pins the sources of the
eight modules by hash; update the hashes there.
