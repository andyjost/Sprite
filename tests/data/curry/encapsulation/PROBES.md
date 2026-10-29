# Weak encapsulation conformance probes

Measured on 2026-10-25 with front end 3.1.0, Sprite's C++ backend
(compiled and interpreted), PAKCS 3.10.0, and KiCS2 3.5.0.

The specification is [the dissertation](https://doi.org/10.15760/etd.3564),
chapter 2, equation 2.1, pp. 73-74, with the owner's principle that a
failure decides nothing until demanded. Other systems are evidence.
The named CHRS13 adaptations are from [sections 3.1-3.4 of the paper](https://www.michaelhanus.de/papers/PPDP13.pdf).
They use the public set-function interface rather than its kernel allValues.

Cells are JSON arrays of top-level Curry answers with insignificant spaces
removed. `[]` means no value line; `["[]"]` means one empty-list answer.
Multiplicity is preserved, including within sorted list observations of sets.
KiCS2's `!` and `(!)` failure markers are treated as absence of a value.
The four former readings (`emptyIsEmpty`, `emptyNotEmpty`,
`insideAfterOutside`, `bindingEscape`) were decided by D54 on 2026-10-25;
the dissertation column and unit tests now specify their decided answers.
`null` means an unavailable measurement, never a failed computation.

This base has D45 (SETARG2). Both mixed-failure orderings now give no
value on Sprite, compiled and interpreted, agreeing with PAKCS. Their old
Sprite answer was True; KiCS2's measured True answers are retained.
The sharedLookup probe also now returns exactly Short, replacing Long,
Short, Short. Issue #171 is closed; its PAKCS comparison now runs, while
KiCS2's Long, Short, Short remains a named divergence. No runtime changes
were made.

| Goal | Dissertation value | Sprite | PAKCS | KiCS2 | Verdict |
| --- | --- | --- | --- | --- | --- |
| `unusedFailure` | `["[1]"]` | `["[1]"]` | `[]` | `["[1]"]` | documented divergence |
| `neededFailure` | `[]` | `[]` | `[]` | `[]` | Sprite right and oracle right |
| `outsideChoice` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | Sprite right and oracle right |
| `sharedChoice` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | Sprite right and oracle right |
| `sharedLookup` | `["Short"]` | `["Short"]` | `["Short"]` | `["Long", "Short", "Short"]` | Sprite right and PAKCS right; KiCS2 divergence |
| `mixedFailure` | `[]` | `[]` | `[]` | `["True"]` | Sprite right and PAKCS right; KiCS2 divergence |
| `mixedFailureReversed` | `[]` | `[]` | `[]` | `["True"]` | Sprite right and PAKCS right; KiCS2 divergence |
| `mixedValue` | `["[2]"]` | `["[2]"]` | `[]` | `["[2]"]` | documented divergence |
| `nestedIndependent` | `["[[2,3]]"]` | `["[[2,3]]"]` | `["[[2,3]]"]` | `["[[2,3]]"]` | Sprite right and oracle right |
| `nestedShared` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | Sprite right and oracle right |
| `nestedUnusedFailure` | `["[[1]]"]` | `["[[1]]"]` | `[]` | `["[[1]]"]` | documented divergence |
| `narrowedBefore` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | Sprite right and oracle right |
| `narrowedAfter` | `["[A,A]", "[A,B]"]` | `["[A,A]", "[A,B]"]` | `[]` | `["[A,A]", "[A,B]"]` | documented divergence |
| `bindingEscape` | `["(A,[True])", "(B,[])"]` | `["(A,[True])", "(B,[])"]` | `[]` | `["(A,[True])", "(B,[])"]` | documented divergence |
| `insideAfterOutside` | `["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | Sprite right and oracle right |
| `emptyIsEmpty` | `["True"]` | `["True"]` | `["True"]` | `["True"]` | Sprite right and oracle right |
| `emptyNotEmpty` | `["False"]` | `["False"]` | `["False"]` | `["False"]` | Sprite right and oracle right |
| `infiniteIsEmpty` | `["False"]` | `["False"]` | `["False"]` | `["False"]` | Sprite right and oracle right |
| `chrsInc12` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | Sprite right and oracle right |
| `chrsAllCoins` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | Sprite right and oracle right |
| `chrsNumCoinLists` | `["2"]` | `["2"]` | `["2"]` | `["2"]` | Sprite right and oracle right |
| `chrsOutsideFailure` | `[]` | `[]` | `[]` | `[]` | Sprite right and oracle right |
| `chrsFailureChoice` | `["[True]"]` | `["[True]"]` | `[]` | `["[True]"]` | documented divergence |
| `chrsFailureChoiceReversed` | `["[True]"]` | `["[True]"]` | `[]` | `["[True]"]` | documented divergence |

The seven PAKCS comparison exemptions are explicit in the driver:
`unusedFailure`, `nestedUnusedFailure`, `mixedValue`, `chrsFailureChoice`,
`chrsFailureChoiceReversed` (strict evaluation discards an unneeded failing
argument), `narrowedAfter`, and `bindingEscape` (the unbound argument
suspends when the capsule starts). The oracle's absence of a value line
is kept in each case. For `bindingEscape` this is a suspension, not a value;
its named divergence exemption leaves the KiCS2 semantic comparison active.

Both mixed-failure goals now run the PAKCS semantic comparison. They have
no defect exemption or expectedFailure marker on Sprite. Their KiCS2
snapshot checks remain active, with named divergence exemptions for the
retained True answers: an inside failure masks the argument failure there.
The sharedLookup unit markers are also removed because this probe now
passes in both modes; its PAKCS comparison now runs. Its KiCS2 snapshot
check remains active before the named divergence exemption. The other
21 Sprite answers are unchanged.

D54 applies D45's failure rule: an empty capsule without an outside failure
is an observable empty set, so `emptyIsEmpty` is True and `emptyNotEmpty`
is False. `insideAfterOutside` separates total outside B from outside
failure: its function has no values at B, yielding `(B,[])` alongside
`(A,[7])`. Under D48's wider escape condition, `bindingEscape` likewise
has `(A,[True])` and `(B,[])`. This last reading follows D48 if that rule
ever changes.
