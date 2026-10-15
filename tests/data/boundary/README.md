# The boundary corpus

Small Python programs that exercise the Python-Curry boundary of Sprite,
one seam per driver.  The corpus gives the design review of the API real
programs to measure against, and it is the regression suite of the boundary:
`tests/unit_boundary.py` runs every driver and compares its output with the
committed `expected.out`.

Each driver is a directory `NN-name`.  The first digit is the group: 0
values in, 1 symbols and sharing, 2 free variables and bindings, 3 results
out, 4 modules and the loader, 5 set functions and the tools, 6 classic
Curry programs driven from Python.  A directory holds `go.py` (the program,
with comments that say what crosses the boundary and why the output is what
it is), `run` (runs `go.py` with the Python of the staged install), the
`README` of the driver (the seam, the catalogue entries and the issues it
exercises, the expected output explained, and for a driver that pins a
defect the issue number and the output a fixed system would print),
`expected.out`, any Curry module it needs, and `oracle.out` where a goal is
plain Curry: the transcript of the PAKCS 3.4.1 REPL on the same goals.  A
transcript holds the command line, normalized (the path of `pakcs` replaced
by its name, the inner quotes of a goal escaped for the shell), the output
of the REPL verbatim (a last line that PAKCS prints without a newline gets
one), and the line `% exit status N` after a non-zero exit.  To run one
driver:

    cd NN-name && ./run

The run script uses the staged install under `../../../../install` or the
one named by `SPRITE_HOME`, the backend of `SPRITE_INTERPRETER_FLAGS`
(`backend:cxx` unless set) and step mode (`SPRITE_ROTATION=steps:65536`
unless set), so that the order of the values of a search reproduces.

The catalogue entries P1 to P55 and the memo sections named below are those
of the design study of the Python API (the notebook of the owner); the
issues are those of the tracker.

## Coverage

| Driver | Seam | Sources | Backends | Oracle |
|---|---|---|---|---|
| 01-scalars-and-limits | bool, int at the 64-bit edges, float, the polymorphic literal and its defaulting, the arithmetic errors | A2, A3, P3, P10, P40, P42, #105, #106 | py, cxx | yes |
| 02-strings-and-chars | a str is a Char or a String by its length and its slot; the typed escape; a Char out and back in | A2, P1, P11, P23 | py, cxx | yes |
| 03-containers | list, tuple, the unit, the 1-tuple and the 15-tuple limit, range, an iterator and an exhausted one, nested and shared data | A2, P8, P9 | py, cxx | yes |
| 04-rejected-values | what the boundary refuses and what it accepts in silence: None, dict, set, bytes, a function, the generator of eval, unboxed, the converter spellings | A2, A6, P4, P9, P13, P14, #107 | py, cxx | no |
| 10-list-of-symbols | a list whose first element is a symbol is an application; pins #104 | A1, P2, P44, #104 | py, cxx | no |
| 11-application-forms | partial and over-application, a symbol as a value, the arity and class checks | A1, A4, P10, P44 | py, cxx | yes |
| 12-sharing-and-cycles | a term used twice against a symbol used twice, anchors and curry.ref, the anchor trap | A1, A5, P5, P6, P17 | py, cxx | yes |
| 20-free-markers | curry.free on the expression route: one marker is one variable, the binding private to an evaluation, the typed marker, the anonymous variable of the text route | A11, P21, P24, P42 | py, cxx | yes |
| 21-pairing-of-103 | a free variable from Python has no observable pairing with the values of a nondeterministic goal; the escapes and the text route; pins #103 | A11, P20, P24, P42, #103 | py, cxx | yes |
| 22-where-free-text-route | where x free on the text route: the lifted Bindings, the result-type rule against PAKCS, a trailing comment and exprtype, several variables, the two printers | A7, A11, P20, P25, P26 | py, cxx | yes |
| 30-generator-contract | the laziness of curry.eval, next and its default, break and close, failure as no value, an error and a suspension in the stream | A6, A12, P27, P42, P46 | py, cxx | yes |
| 31-values-out | values of user types, functions as values, a Char and a String out, the converter and the flag defaultconverter, curry.topython with and without a type | A6, A9, A10, P18, P21, P23, P54 | py, cxx | yes |
| 32-value-data-model | a Curry value as a Python object: equality, hash, order, truth, len and indexing, the forward node after an evaluation, the trusted annotation | A9, P15, P16, P17, P18, P22 | cxx | no |
| 33-nested-empty-lists | a value that holds the empty list at two types crosses back into a typed call; pins the passing lines of #108 | P19, P22, #108 | py, cxx | no |
| 34-errors-and-messages | the messages of the typed boundary and the classes of the exceptions, as a Python caller meets them | A4, A20, A21, P1, P7, P41, P42, P43, P44, P45 | py, cxx | no |
| 40-import-and-lookup | import by name and by file, the path, curry.modules, what a module offers, curry.symbol, curry.type, curry.module | A13, A14, P33, P34, P39, P54 | py, cxx | no |
| 41-compile-text | curry.compile of text in both modes: names, a reused name, imports, exprtype, a str as a goal | A7, A15, P12, P26, P32, P45 | py, cxx | yes |
| 42-reset-and-stale-symbol | a module of the same name after reset and reload; a symbol that outlives the reset (pins #114) | A13, A17, P30, P35, #114 | cxx | no |
| 43-edited-source | an edited source is not read again by import_ in one process; the running code is not swapped when the source changed | A13, P53, #110 | py, cxx | no |
| 44-save-and-load | curry.save and curry.load of a module and of a program, the saved program run | A16, P31, P39 | py | no |
| 45-load-objects | the compiled object: an object-loaded module saved, a load during and after a background compile, a refused second load | A16, P28, P29, P38, P55, #109, #113, #115 | cxx | no |
| 50-set-functions | set0 to set2 from Python, a captured choice, a failing argument, a nested set, a free argument | A1, P24, #117, D25 to D28 | py, cxx | no |
| 51-tools-parity | sprite-exec and the REPL against curry.eval on the same goals | A22, P46, P47, P48 | py, cxx | yes |
| 60-last-member-nats | narrowing by inversion: Last, Member, Nats; Peano terms built in Python | PAKCS Last, Member, Nats; P5, P7 | py, cxx | yes |
| 61-puzzles | horseman and colormap with two to four free parameters; the (&) difference | PAKCS horseman, colormap; P5, P7, P23 | py, cxx | yes |
| 62-family | the family databases in four styles, the same questions | PAKCS family_rel, family_con, family_fun, family_nd; P5, P7 | py, cxx | yes |
| 63-nondetfunc | choose, insert, permut, three permutation sorts, double coin | PAKCS nondetfunc; P3, P7 | py, cxx | yes |
| 64-infinite-lists | fibs, primes, hamming, first over from, a Python iterator as the lazy list | PAKCS inflists, First; A2, P3, P5 | py, cxx | yes |
| 65-assembler | logic variables as forward references; the program built in Python as constructors | PAKCS assembler; P5, P7, #104 | py, cxx | yes |
| 66-residuation | ensureNotFree, ensureSpine, (&), an active object, arithmetic as a passive constraint | PAKCS rigidadd, rigidor, infresiduate, Account, digit; P5, P7, P21 | py, cxx | yes |

## Programs Sprite cannot compile or run

The programs of PAKCS 3.4.1 that were tried for the classic group and got
no driver, with the message.  "Does not compile" means the pinned front end
(PAKCS 3.4.1's) rejects the source as it is; PAKCS 3.4.1 itself rejects it
the same way, and its own test script does not load it.

| Program | What happens |
|---|---|
| `mergesort.curry` | does not compile: `Type signature too general` for `sort`; the inferred type needs `Data a` for the `=:=` on the elements |
| `colormap_nd.curry` | does not compile: `Missing instance for Prelude.Eq Color` at `correct aColor ...`; the data type derives no `Eq` |

## Values that differ from PAKCS

The concurrent conjunction `(&)` yields `False` in Sprite when one side is
`False`, on both backends (`concurrent_and` of the Python Prelude and the
C++ step function), where PAKCS 3.4.1 has no value: `False & True` prints
`*** No value found!` there (oracle of 61).  PAKCS 3.10.0 and KiCS2 3.5.0
agree with PAKCS 3.4.1.  `colormap.goal` in 61 has 256 values in Sprite,
48 of them `True`, and PAKCS prints 48 rows.  Recorded on 2026-10-15 as
issue #139; the driver pins the counts.

## Attribution

The Curry programs of the group 6 drivers are copied from the examples of
PAKCS 3.4.1 (`examples/NAME.curry` of the distribution), written by Michael
Hanus and distributed under the BSD license of PAKCS.  Each copied program
keeps its header comment and carries one line that names its origin.  The
full text of the license is in `LICENSE-PAKCS` beside this file.
