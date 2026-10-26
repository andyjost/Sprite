The Curry library
=================

This directory holds the Curry library that ships with Sprite.

`lib/` contains the sources.  They are a copy of the library of PAKCS 3.10.0,
which is version 3.4.0 of the Curry package `base`, plus Sprite's own modules
`Control.SetFunctions`, `Control.Search.SetFunctions`, and `Sprite.Stream`.  `lib/LICENSE` is the license
of the origin.
`lib/NOTICE` names the origin, the version, and the changes.  The Prelude
carries a three-line prefix that defines `__KICS2__`; NOTICE explains why.
The same sources compile with front end 2.0.0 (PAKCS macro 304) and
front end 3.1.0 (PAKCS macro 310). No upstream backend files are shipped.

`make stage` copies the sources, LICENSE, and NOTICE to `$(PREFIX)/curry`.
Sprite appends that directory to the Curry path, so the front end and the
toolchain find the library there and never read the PAKCS library.  The
install uses shipped interfaces when no front end is available. With a
front end, it also writes FlatCurry under
`$(PREFIX)/curry/.curry/pakcs-<ver>/`, so later compilations can read the
library without writing into the installation. The overlay archive packs
the interfaces from the staged library for the oracle tests.

The text shim in `oracle/Sprite/Stream.curry` gives PAKCS and KiCS2 the
same module name and signature for stream programs. Put `oracle/` first
on their Curry path. Sprite uses the runtime primitive under `lib/`.

Pinned build products
---------------------

Every library module has committed products under its package's
`.curry/sprite-pakcs-3.10.0/` directory: `.icy` (ICurry), `.fint` and
`.icurry` (interfaces), `.icy.imports` (import provenance), and `.icy.source`
(the SHA-256 receipt of its Curry source). They belong to front end 3.1.0
with PAKCS 3.10.0 and base 3.4.0, regenerated with Sprite's runtime route
(`icurry_compat=False`).
In compatibility mode the port is byte-identical to `icurry` 3.3.0; the
independent references are in `overlay-pakcs-3.10.0.tgz`.

The source distribution includes these products. A build needs Python and
a C++ compiler but no Curry front end or PAKCS. CMake uses the current
pair's pins when no front end is found, including with explicit
`-DWITH_PAKCS= -DWITH_CURRY_FRONTEND= -DWITH_ICURRY=`. A missing pin or a
source receipt that differs from its source is a configure error naming
the module. The legacy pair, front end 2.0.0 with PAKCS 3.4.1, still
requires its front end and compiles the library from source at stage time.

Staging derives compressed ICurry-JSON (`.json.z`) from the pins and
compiles every supported library module for the C++ runtime. JSON and
native objects are build outputs, not repository pins. The installed
library runs without a front end; compiling new Curry text needs one.

Ten modules are left out of that compile (the `unsupported` list in
`CMakeLists.txt`): `Curry.Compiler.Distribution`, `Data.IORef`, `Debug.Trace`,
`System.CPUTime`, `System.Environment`, `System.IO`, `System.IO.Unsafe`,
`Test.Prop`, `Test.Prop.Types`, and `Control.Search.SearchTree`.
Their ICurry and JSON are installed, but their native primitives are absent.

`Control.Search.SetFunctions` is Sprite's facade over its native capsules.
It shares the canonical `Control.SetFunctions.Values a = Values [a]` type.
Both surfaces use weak encapsulation: body choices are captured, argument
choices stay outside, and duplicates are kept. The `Strategy` values
`dfsStrategy`, `bfsStrategy`, `idsStrategy`, `idsStrategyWith`, and
`diagStrategy` are advisory; all use Sprite's fair scheduler and value order.
`getSomeValue` and `getSome` select from that same list in IO.

`Control.Search.Unsafe` and `Control.Search.AllValues` also use these weak
capsules. Their upstream interface describes strong encapsulation, including
enumeration of free variables inside the expression. Sprite does not
provide that enumeration: a free variable can remain free or demand an
outside binding. The DFS names are advisory. `rewriteAll` and `rewriteSome`
remain externals that report not implemented when called: capsules cannot
suppress computations that demand bindings of outside variables. Strong
search and `Control.Search.SearchTree` remain future work.

Rebuilding the products
-----------------------

The installed pins are products of Sprite's runtime route
(`icurry_compat=False`), which looks through root type annotations and keeps
completed case order. A build with front end 3.1.0 and PAKCS 3.10.0
regenerates these products.
From the project root:

    make stage SPRITE_REBUILD_ICY=1

This writes fresh products in the build's `stage/curry/` image and copies
them into the installation. Copy every module's `.icy`, `.fint`, `.icurry`,
`.icy.imports`, and `.icy.source` back to the matching
`.curry/sprite-pakcs-3.10.0/` directory under `lib/`. Check the ICurry bytes
by regenerating them with the runtime route before replacing the committed
products. The independent outputs of `icurry` 3.3.0 are the 30 library
oracles in `overlay-pakcs-3.10.0.tgz` at the repository root;
`func_flat2icurry.py::test_library` checks the port's compatibility mode
against those oracles. The installed pins are not compatibility-mode oracles.
A build with front end 2.0.0 never uses the current pair's pins.
As with other source modules, an incremental stage keeps valid products.

`sprite-make --icy` compiles a module with the configured route from Curry
to ICurry: the front end plus Sprite's translation by default, or `icurry`
with `SPRITE_CURRY2ICURRY=icurry`.

After a change to the ICurry reader, rebuild the derived `.json.z` files
as well. The JSON is derived from the ICurry, rather than translated by
the upstream compiler.

Updating the library
--------------------

Copy the `.curry` files of the new PAKCS `lib` directory over `lib/`.  Add
the prefix to `Prelude.curry`.  Update `lib/NOTICE`.  Rebuild the pinned
products and run the tests. `tests/unit_currylib.py` and
`tests/unit_search_library.py` pin the sources of the eleven modules by
hash; update the hashes there.
