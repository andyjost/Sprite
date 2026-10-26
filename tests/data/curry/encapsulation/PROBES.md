# Weak encapsulation conformance probes

Measured on 2026-10-25 with front end 3.1.0, Sprite's C++ backend
(compiled and interpreted), PAKCS 3.10.0, and KiCS2 3.5.0.

The specification is [the dissertation](https://andrewjost.wordpress.com/wp-content/uploads/2023/05/jostthesis.final_.10may23.pdf),
chapter 2, equation 2.1, pp. 73-74, with the owner's principle that a
failure decides nothing until demanded. Other systems are evidence.
The named CHRS13 adaptations are from [sections 3.1-3.4 of the paper](https://www.michaelhanus.de/papers/PPDP13.pdf).
They use the public set-function interface rather than its kernel allValues.

Cells are JSON arrays of top-level Curry answers with insignificant spaces
removed. `[]` means no value line; `["[]"]` means one empty-list answer.
Multiplicity is preserved, including within sorted list observations of sets.
KiCS2's `!` and `(!)` failure markers are treated as absence of a value.
For reading questions the dissertation column gives both candidate answers;
unit tests preserve the measured behavior without declaring it correct.
`null` means an unavailable measurement, never a failed computation.

This base has D45 (SETARG2). Both mixed-failure orderings now give no
value on Sprite, compiled and interpreted, agreeing with PAKCS. Their old
Sprite answer was True; KiCS2's measured True answers are retained.
The sharedLookup probe also now returns exactly Short, replacing Long,
Short, Short. Issue #171 remains open and retains its oracle comparison
exemption. No runtime changes were made.

| Goal | Dissertation value | Sprite | PAKCS | KiCS2 | Verdict |
| --- | --- | --- | --- | --- | --- |
| `unusedFailure` | `["[1]"]` | `["[1]"]` | `[]` | `["[1]"]` | documented divergence |
| `neededFailure` | `[]` | `[]` | `[]` | `[]` | Sprite right and oracle right |
| `outsideChoice` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | `["[2]", "[4]"]` | Sprite right and oracle right |
| `sharedChoice` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | `["(1,[2])", "(2,[4])"]` | Sprite right and oracle right |
| `sharedLookup` | `["Short"]` | `["Short"]` | `["Short"]` | `["Long", "Short", "Short"]` | probe passes; issue #171 open |
| `mixedFailure` | `[]` | `[]` | `[]` | `["True"]` | Sprite right and PAKCS right; KiCS2 divergence |
| `mixedFailureReversed` | `[]` | `[]` | `[]` | `["True"]` | Sprite right and PAKCS right; KiCS2 divergence |
| `mixedValue` | `["[2]"]` | `["[2]"]` | `[]` | `["[2]"]` | documented divergence |
| `nestedIndependent` | `["[[2,3]]"]` | `["[[2,3]]"]` | `["[[2,3]]"]` | `["[[2,3]]"]` | Sprite right and oracle right |
| `nestedShared` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | `["(1,[[2]])", "(2,[[4]])"]` | Sprite right and oracle right |
| `nestedUnusedFailure` | `["[[1]]"]` | `["[[1]]"]` | `[]` | `["[[1]]"]` | documented divergence |
| `narrowedBefore` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | `["(A,[A])", "(B,[B])"]` | Sprite right and oracle right |
| `narrowedAfter` | `["[A,A]", "[A,B]"]` | `["[A,A]", "[A,B]"]` | `[]` | `["[A,A]", "[A,B]"]` | documented divergence |
| `bindingEscape` | `["(A,[True])"] or ["(A,[True])", "(B,[])"]` | `["(A,[True])", "(B,[])"]` | `[]` | `["(A,[True])", "(B,[])"]` | reading needed |
| `insideAfterOutside` | `["(A,[7])"] or ["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | `["(A,[7])", "(B,[])"]` | reading needed |
| `emptyIsEmpty` | `[] or ["True"]` | `["True"]` | `["True"]` | `["True"]` | reading needed |
| `emptyNotEmpty` | `[] or ["False"]` | `["False"]` | `["False"]` | `["False"]` | reading needed |
| `infiniteIsEmpty` | `["False"]` | `["False"]` | `["False"]` | `["False"]` | Sprite right and oracle right |
| `chrsInc12` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | `["[2,3]", "[6,7]"]` | Sprite right and oracle right |
| `chrsAllCoins` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | `["[0]", "[1]"]` | Sprite right and oracle right |
| `chrsNumCoinLists` | `["2"]` | `["2"]` | `["2"]` | `["2"]` | Sprite right and oracle right |
| `chrsOutsideFailure` | `[]` | `[]` | `[]` | `[]` | Sprite right and oracle right |
| `chrsFailureChoice` | `["[True]"]` | `["[True]"]` | `[]` | `["[True]"]` | documented divergence |
| `chrsFailureChoiceReversed` | `["[True]"]` | `["[True]"]` | `[]` | `["[True]"]` | documented divergence |

The six PAKCS comparison exemptions are explicit in the driver:
`unusedFailure`, `nestedUnusedFailure`, `mixedValue`, `chrsFailureChoice`,
`chrsFailureChoiceReversed` (strict evaluation discards an unneeded failing
argument), and `narrowedAfter` (the unbound argument suspends when the
capsule starts). The oracle's empty answer is kept in each case.
`bindingEscape` likewise has no PAKCS value line (suspension); it is a
reading question rather than an exemption asserting correctness.

Both mixed-failure goals now run the PAKCS semantic comparison. They have
no defect exemption or expectedFailure marker on Sprite. Their KiCS2
snapshot checks remain active, with named divergence exemptions for the
retained True answers: an inside failure masks the argument failure there.
The sharedLookup unit markers are also removed because this probe now
passes in both modes; its open-issue oracle exemption remains. The other
21 Sprite answers are unchanged.

The four reading questions concern whether an empty value set can be
observed before its value is identified with failure, and whether a
context-variable binding made inside a capsule must escape. In particular,
`insideAfterOutside` separates a total outside B from an outside failure:
its function has no values at B. The owner must distinguish this from the
D45 case whose argument itself has no value.
