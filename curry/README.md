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

`make stage` copies the sources, LICENSE, and NOTICE to `$(PREFIX)/curry/lib`.
Sprite appends that directory to the Curry path, so the front end and the
toolchain find the library there and never read the PAKCS library.  The
install uses shipped interfaces when no front end is available. With a
front end, it also writes FlatCurry under
`$(PREFIX)/curry/lib/.curry/pakcs-<ver>/`, so later compilations can read the
library without writing into the installation. The overlay archive packs
the interfaces from the staged library for the oracle tests.

`Distribution.installDir` returns `$(PREFIX)/curry`, with private tool
launchers in `bin/` and sources in `lib/`. Native runtime libraries remain
in `$(PREFIX)/lib`. Stock CPM readers find raw `.fcy`, `.fint` and `.acy`
products under `$(PREFIX)/curry/lib/.curry/sprite-<version>/`. The private
`sprite-frontend` serves ordinary library requests from these shipped files,
without writing to the installation or requiring a front end.

The text shim in `oracle/Sprite/Stream.curry` gives PAKCS and KiCS2 the
same module name and signature for stream programs. Put `oracle/` first
on their Curry path. Sprite uses the runtime primitive under `lib/`.

Pinned build products
---------------------

Every library module has committed products under its package's
`.curry/sprite-pakcs-3.10.0/` directory: `.icy` (ICurry), `.fint` and
`.icurry` (interfaces), `.icy.imports` (import provenance), and `.icy.source`
(the SHA-256 receipt of its Curry source). Raw `.fcy` and `.acy` pins
also preserve the stock-reader products for builds without a front end.
They belong to front end 3.1.0 with PAKCS 3.10.0 and base 3.4.0. ICurry
uses Sprite's runtime route (`icurry_compat=False`); the analysis pins
are the front end's unmodified output.
In compatibility mode the port is byte-identical to `icurry` 3.3.0; the
independent references are in `overlay-pakcs-3.10.0.tgz`.

The source distribution includes these products. A build needs Python and
a C++ compiler but no Curry front end or PAKCS. CMake uses the current
pair's pins when no front end is found, including with explicit
`-DWITH_PAKCS= -DWITH_CURRY_FRONTEND= -DWITH_ICURRY=`. A missing pin or a
source receipt that differs from its source is a configure error naming
the module. The legacy pair, front end 2.0.0 with PAKCS 3.4.1, still
requires its front end and compiles the library from source at stage time.

Staging derives the module image (`.img`) from the pins and
compiles every library module for the C++ runtime. Images and
native objects are build outputs, not repository pins. The installed
library runs without a front end; compiling new Curry text needs one.

Every module compiles and ships with an image, plus a native object when
the stage has a C++ compiler. Strong-search operations described below remain
unsupported and raise `not implemented` at their call.

The primitives of `Curry.Compiler.Distribution`, `System.CPUTime`,
`System.Environment`, `Data.IORef` and `System.IO` are implemented.
System.IO owns UTF-8 file handles; standard handles use Python's current
standard streams, including redirected streams. `Debug.Trace.traceIO` works
through these handles; pure `trace` runs through
`System.IO.Unsafe.unsafePerformIO`. The CPM packages `directory` and `process`
resolve their externals through the same registry (the packages are installed
separately). Distribution reports Sprite's build version and Curry home;
CPUTime reports milliseconds.
Environment uses native environment operations and registered Python functions
for arguments, the program name and hostname. IORef stores lazy graph values
in cells displayed as `<IORef>`; writes go through `Variable::set_successor`.

`System.IO.Unsafe` has all nine primitives. `unsafePerformIO` runs an action
when its shared expression is evaluated. `spawnConstraint c x` evaluates `c`
first, evaluates `x` when `c` suspends, and returns `x` only after `c` is
`True`. A false constraint fails; a diverging constraint need not let `x`
run. This uses the suspension rule of Sprite's `&`.

`isVar`, `identicalVar`, and `isGround` observe the bindings of the evaluating
configuration. Their results can differ between alternatives of one search.
`compareAnyTerm` evaluates demanded expressions and orders unbound variables
before partial functions, and partial functions before data. Variables use
internal configuration group identifiers. Functions compare by qualified
head name, missing argument count and supplied arguments. Data of one type
compare by constructor declaration order and then lexicographically by
fields; integers (including large integers), characters and finite floats
compare by value. NaN compares after all other floats; NaNs compare equal
to each other, as do signed zeros. Different data types compare by qualified
type name.
The variable order is internal and is not stable between evaluations.

`showAnyTerm` normalizes its term, retaining free variables named `_a`, `_b`,
and so on, as `curry.show` does. `showAnyExpression` prints the expression
without reducing its functions, resolving configuration bindings. Both use
unqualified constructor names and Curry list, tuple and string notation.
`readsAnyUnqualifiedTerm` reads that data syntax, including prefix constructor
applications (with bare or parenthesized symbolic heads), numeric and
character literals, lists, tuples and repeated variable names. It resolves constructors in the supplied modules in order;
those modules must already be imported. It returns one term and the unused
suffix, or `[]` on invalid syntax. Function expressions and cyclic display
abbreviations are not readable data terms.

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

This writes fresh products in the build's `stage/curry/lib/` image and copies
them into the installation. Copy every module's `.icy`, `.fint`, `.icurry`,
`.icy.imports`, and `.icy.source` back to the matching
`.curry/sprite-pakcs-3.10.0/` directory under `lib/`. Copy the raw `.fcy` and
`.acy` from the image's `curry/lib/.curry/sprite-<version>/` hierarchy to
those same per-module pin directories. Check the ICurry bytes
by regenerating them with the runtime route before replacing the committed
products. The independent outputs of `icurry` 3.3.0 are the 30 library
oracles in `tests/overlay/overlay-pakcs-3.10.0.tgz`;
`func_flat2icurry.py::test_library` checks the port's compatibility mode
against those oracles. The installed pins are not compatibility-mode oracles.
A build with front end 2.0.0 never uses the current pair's pins.
As with other source modules, an incremental stage keeps valid products.

`sprite-make --icy` compiles a module with the configured route from Curry
to ICurry: the front end plus Sprite's translation by default, or `icurry`
with `SPRITE_CURRY2ICURRY=icurry`.

After a change to the ICurry reader, rebuild the module images (`.img`)
as well. The module image is derived from the ICurry, rather than translated
by the upstream compiler.

Updating the library
--------------------

Copy the `.curry` files of the new PAKCS `lib` directory over `lib/`.  Add
the prefix to `Prelude.curry`.  Update `lib/NOTICE`.  Rebuild the pinned
products and run the tests. `tests/unit_currylib.py` and
`tests/unit_search_library.py` pin the sources of the eleven modules by
hash; update the hashes there.
