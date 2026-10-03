# Probe modules for the FlatCurry-to-ICurry port

These modules hold the constructs that the rest of the test corpus does
not use.  Their ICurry files were written by `icurry` 3.1.0 under the
pinned PAKCS and sit in the overlay archive at the root of the repository.
The unit test `unit_flat2icurry.py` (class `TestProbes`) compares the
output of `curry.toolchain.flat2icurry` with them byte for byte.

| Module | Constructs |
|---|---|
| `Literals` | negative numbers, float exponents, characters outside ASCII, literal cases of every kind |
| `Lets` | recursive and mutually recursive lets (`INodeAssign`), lets in nested positions |
| `Partials` | partial applications of constructors (`ICPCall`) and of functions, the choice operator |
| `Newtypes` | newtype declarations and uses, an imported newtype, class instances for a newtype |
| `Lifting` | nested and complex cases, free variables and lets in branches, a name that collides with a generated one, many variables |
| `Classes` | type classes, instances, derived instances, records, local functions, lambdas, sections, comprehensions, do notation, a hierarchical import |
| `Externals` | external declarations, operator declarations, type synonyms between data types, calls of `failed` |
| `TypedRoot` | type annotations at the root of a rule, where `icurry` 3.1.0 loses the bindings of a let or free declaration; see below |
| `Sub/Deep` | a hierarchical module imported by `Classes` |

To regenerate the products after a change to a module, run `sprite-make
--icy --curry2icurry icurry` and `sprite-make --json --zip` on it from this
directory, with `CURRYPATH` set to this directory.  Then rebuild the overlay
archive with `make overlay-archive` at the root.  The products must come
from `icurry` 3.1.0, because they are the oracle of the port.  A module must
compile under `icurry`.  A type annotation around a case at the root of a
rule does not compile there.  A float literal that the front end turns into
`Infinity` does not either.

`TypedRoot` and `Externals` are the two modules on which the two routes
differ.  The oracle files in the archive are the output of `icurry`.  For
`TypedRoot` it loses the bindings, and the program it describes fails at
run time.  The route through the front end (`sprite-make --icy`, or the
import of the module) looks through the annotation and writes a different
`.icy` file, so the program runs.  For `Externals` the route turns
`typedFailed = (failed :: Int)` into `IExempt`, as it does for a bare
`failed`, where `icurry` keeps the call; both fail.  `unit_flat2icurry.py`
checks both modules against the archive, and `unit_curry2icurry.py` runs
`TypedRoot`.  `func_flat2icurry.py` leaves the on-disk products of these two
modules out of its comparison.
