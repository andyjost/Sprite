# Source patches

CI run 1 reached GHC 9.6.7 on aarch64 and established these failures:

* `0001-explicit-liftM-import.patch`: with mtl 2.3.1 the existing imports
  no longer bring `liftM` into scope. Import it from `Control.Monad`.
* `0002-as-pattern-whitespace.patch`: GHC rejects `f@ (Field _ _ _)`.
  Remove the space after `@` to retain the original as-pattern.

CI run 2 confirmed both patches apply and x86-64 still passes byte parity.
It established one further missing import under GHC 9.6.7 / mtl 2.3.1:

* `0003-syntax-utils-liftM-imports.patch`: `Curry.Syntax.Utils` uses
  `liftM2` and `liftM3`, formerly re-exported by `Control.Monad.State`.
  Import those same functions from `Control.Monad`.

CI run 3 applied all three patches on both architectures. The full ARM
compile reported two distinct errors (each repeated by the dynamic retry):

* `0004-warn-check-either-fallback.patch`: `Checks.WarnCheck:835` relied
  on the old orphan `Alternative (Either String)` instance, absent with
  mtl 2.3.1. A local `orElse` preserves its lazy first-success behavior,
  the lookup order, and the final error if every lookup fails. Remove the
  unused `Control.Applicative` import; do not add an orphan instance.
* `0005-abstract-curry-when-import.patch`: `Generators.GenAbstractCurry:25`
  imports `when` from `Control.Monad.State`, which no longer exports it.
  Import it qualified as `S` from `Control.Monad` instead, preserving the
  existing `S.when` call.

All five changes preserve the 2.0.0 program and are valid under GHC 8.8.3 too.
The build applies them on both architectures in name order using
`patch --batch --forward --fuzz=0 -p1` from the source root. Their application
was checked against the archive whose checksum CI established; compilation
and byte parity remain CI checks. Each future patch must name the failing
GHC version, the error, and why the change preserves the program.
Dependency bound relaxation on aarch64 remains a Cabal command-line option.

## Audit for 3.1.0 (tag v3.1.0)

The 3.1.0 build applies none of the five 2.0.0 patches. The source already
supports mtl ^>=2.3 and base ^>=4.19; no bounds are relaxed. Audited outcomes:

| Patch | Disposition | Upstream evidence |
| --- | --- | --- |
| 0001 | Dropped | `Curry.Base.Monad` no longer calls `liftM`. |
| 0002 | Dropped | `Curry.Syntax.Type` already spells `f@(Field _ _ _)`. |
| 0003 | Dropped | `Curry.Syntax.Utils` no longer calls `liftM2` or `liftM3`. |
| 0004 | Dropped | `Curry.Frontend.Checks.WarnCheck` defines a local `<||>` on `Either` that keeps the first `Right` or last `Left`. |
| 0005 | Dropped | `Curry.Frontend.Generators.GenAbstractCurry` imports `when` from `Control.Monad` and calls it unqualified. |

The namespace of checks and generators is now `Curry.Frontend`. The base
and syntax modules above retain their paths. These are source audit
results; both native source builds and parity still require CI dispatch.
