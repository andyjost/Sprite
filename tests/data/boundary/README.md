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
| 01-scalars-and-limits | Booleans, integers, floats, numeric defaulting and arithmetic errors. | A2, A3, P3, P10, P40, P42, #105, #106 | cxx | yes |
| 02-strings-and-chars | A Python str is a String; curry.Char spells a character. | A2, P1, P11, P23 | cxx | yes |
| 03-containers | Lists, tuples, ranges and lazy iterators enter typed terms. | A2, P8, P9 | cxx | yes |
| 04-rejected-values | Unsupported Python values and a Results argument are refused. | A2, A6, P4, P9, P13, P14, #107 | cxx | no |
| 10-list-of-symbols | A Python list of symbols is a list value; a call is an application. | A1, P2, P44, #104 | cxx | no |
| 11-application-forms | Symbols, partial applications, surplus arguments and class methods. | A1, A4, P10, P44 | cxx | yes |
| 12-sharing-and-cycles | One held Python term shares a choice; separate reads are independent. | A1, A5, P5, P6, P17 | cxx | yes |
| 20-free-markers | curry.free(name) creates one Var; curry.anonymous is fresh per occurrence. | A11, P21, P24, P42 | cxx | yes |
| 21-pairing-of-103 | curry.eval yields values; curry.solve pairs values with bindings. | A11, P20, P24, P42, #103 | cxx | yes |
| 22-where-free-text-route | curry.parse reads goals with a trailing where x free clause. | A7, A11, P20, P25, P26 | cxx | yes |
| 30-generator-contract | Results is lazy and supports next, break, close, one and a context manager. | A6, A12, P27, P42, P46 | cxx | yes |
| 31-values-out | Data, Function, Values, Char, Python containers and variables come back. | A6, A9, A10, P18, P21, P23, P54 | cxx | yes |
| 32-value-data-model | Converted scalars and containers obey the Python data model. | A9, P15, P16, P17, P18, P22 | cxx | no |
| 33-nested-empty-lists | Converted values containing empty lists enter new typed calls. | P19, P22, #108 | cxx | no |
| 34-errors-and-messages | The public error tree descends from curry.CurryError, an Exception. | A4, A20, A21, P1, P7, P41, P42, P43, P44, P45 | cxx | no |
| 40-import-and-lookup | Imports, path, the registry, item lookup and curry.info metadata. | A13, A14, P33, P34, P39, P54 | cxx | no |
| 41-compile-text | curry.compile builds modules; curry.parse reads expressions. | A7, A15, P12, P26, P32, P45 | cxx | yes |
| 42-reset-and-stale-symbol | A reset makes old modules stale; new modules use their own code. | A13, A17, P30, P35, #114 | cxx | no |
| 43-edited-source | Repeated import returns the loaded module after a source edit. | A13, P53, #110 | cxx | no |
| 44-save-and-load | A saved Python module round-trips; a saved program runs its named goal. | A16, P31, P39 | cxx | no |
| 45-load-objects | An object-loaded module saves; evaluation survives background compilation. | A16, P28, P29, P38, P55, #109, #113, #115 | cxx | no |
| 50-set-functions | set0 through set2, captured choices, free arguments and nested sets. | A1, P24, #117, D25 to D28 | cxx | no |
| 51-tools-parity | The tools and API print converted values through curry.show. | A22, P46, P47, P48 | cxx | yes |
| 60-last-member-nats | Narrowing by inversion, Peano constructor calls and named variables. | PAKCS Last, Member, Nats; P5, P7 | cxx | yes |
| 61-puzzles | Horseman and colormap use named variables and solve answers. | PAKCS horseman, colormap; P5, P7, P23 | cxx | yes |
| 62-family | Four database styles ask corresponding questions through typed calls. | PAKCS family_rel, family_con, family_fun, family_nd; P5, P7 | cxx | yes |
| 63-nondetfunc | Choose, insert, permutations, sorting and call-time choice. | PAKCS nondetfunc; P3, P7 | cxx | yes |
| 64-infinite-lists | Finite prefixes of fibs, primes and hamming; a lazy Python iterator. | PAKCS inflists, First; A2, P3, P5 | cxx | yes |
| 65-assembler | A program is a Python list of constructor applications. | PAKCS assembler; P5, P7, #104 | cxx | yes |
| 66-residuation | Rigid addition, concurrent conjunction and active-object messages. | PAKCS rigidadd, rigidor, infresiduate, Account, digit; P5, P7, P21 | cxx | yes |

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
