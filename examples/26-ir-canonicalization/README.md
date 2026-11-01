# Every normal form of a small expression IR

Eight rewrite rules of a small expression IR are twelve equations in Curry,
the language that Sprite runs inside Python.  The module is sixty lines, the
Python that asks it thirty-seven.

A canonicalizer is a set of rewrite patterns and a driver that applies them
until none matches.  The hard question is whether the patterns agree on an
input: can two orders end at different normal forms?  A greedy driver
answers for the order it took.  Ask Sprite for the normal form of an input
and it follows every order and returns each one, with the rules it used and
the term it reached.

```python
import curry
curry.path.insert(0, '.')                         # Curry's sys.path
from curry.lib import Canon as C                  # imports ./Canon.curry

RULES = curry.eval(C.ruleNames).one()             # the goal has exactly one value; .one() takes it
x, k = C.Var('x'), C.Const                        # x is a variable, k(3) the constant 3
e = C.Mul(C.Mul(x, k(3)), k(2))                   # (x * 3) * 2

def show(term):
    return curry.eval(C.render(term)).one()

orders = curry.eval(C.normalForms(RULES, e)).one()
for used, form, done in orders:
    note = '' if done else '  (no normal form within 32 steps)'
    print(f'{" ".join(used):12} {show(form)}{note}')
forms = [form for _, form, _ in orders]
print(C.Mul(x, k(6)) in forms)                    # a normal form is a term Python can compare
# reassoc      x * 6
# twice        (x * 3) + (x * 3)
# True
```

A driver that tries `twice` first returns the second line and never sees the
first.  The import translates `Canon.curry` with the Curry front end, which
comes with the package.  A Curry expression can have any number of values;
that is nondeterminism.  Each entry is one rewrite order: its rules, the
term it reached, and a flag that is `False` when it has not ended after 32
steps.  Sprite's evaluation strategy is proved sound, complete, and optimal:
it finds exactly the values of an expression in only the steps needed, and
the [dissertation](https://doi.org/10.15760/etd.3564) has the proofs.  So
every order that ends within the bound is in the list.

## The module

`a ? b` has the values of `a` and of `b`.  A function with no equation for
an argument has no value there, which is not an error: it is how a rule says
it does not match.  `set2 f x y` is the set of the values of `f x y`; the
digit counts the arguments.  `anyOf xs` has each element of `xs` as a value;
it is in the Prelude, which every module imports.

```curry
module Canon where
import Control.SetFunctions (set1, set2, isEmpty, chooseValue, sortValues)
import Data.List (nub, sort)

data Expr = Const Int | Var String | Add Expr Expr | Mul Expr Expr | Transpose Expr
  deriving (Eq, Ord)
-- The rules.  A rule has no value on a term it does not rewrite; that absence is the match test.
addZero (Add a (Const 0)) = a
mulOne (Mul a (Const 1)) = a
mulZero (Mul _ (Const 0)) = Const 0
fold (Add (Const m) (Const n)) = Const (m + n)
fold (Mul (Const m) (Const n)) = Const (m * n)
constRight (Add (Const c) a) | notConst a = Add a (Const c)
constRight (Mul (Const c) a) | notConst a = Mul a (Const c)
reassoc (Add (Add a (Const m)) (Const n)) = Add a (Const (m + n))
reassoc (Mul (Mul a (Const m)) (Const n)) = Mul a (Const (m * n))
twice (Mul a (Const 2)) = Add a a
transpose (Transpose (Transpose a)) = a
transpose (Transpose (Const c)) = Const c
notConst e = case e of Const _ -> False; _ -> True
rules = [("addZero", addZero), ("mulOne", mulOne), ("mulZero", mulZero), ("fold", fold),
  ("constRight", constRight), ("reassoc", reassoc), ("twice", twice), ("transpose", transpose)]
ruleNames = map fst rules

-- One rewrite step, by any rule at any position: the name of the rule and the result.
step :: [(String, Expr -> Expr)] -> Expr -> (String, Expr)
step rs e = atRoot rs e ? inside rs e
atRoot rs e = case anyOf rs of (name, rule) -> (name, rule e)
inside rs (Add a b) = under rs (\a' -> Add a' b) a ? under rs (Add a) b
inside rs (Mul a b) = under rs (\a' -> Mul a' b) a ? under rs (Mul a) b
inside rs (Transpose a) = under rs Transpose a
under rs k a = case step rs a of (n, a') -> (n, k a')

-- One rewrite order to a normal form, a term with no step, within 32 steps.  The set
-- of steps exists for isEmpty; chooseValue makes each step a value again.
normalize :: [(String, Expr -> Expr)] -> Expr -> ([String], Expr, Bool)
normalize rs e = go (32 :: Int) e
  where go fuel t = let steps = set2 step rs t in
          if isEmpty steps then ([], t, True)
          else if fuel == 0 then ([], t, False)
          else case chooseValue steps of
            (n, t') -> case go (fuel - 1) t' of (ns, nf, ok) -> (n : ns, nf, ok)
-- Every rewrite order under the named rules, one entry per order, sorted.
normalForms names e = sortValues (set2 normalize active e)
  where active = [r | r@(name, _) <- rules, name `elem` names]

-- The terms of depth at most d over x, 2 and 3, and those with more than one normal form.
terms d = Var "x" ? Const (2 ? 3) ? deeper
  where deeper | d > 0 = Add (terms (d - 1)) (terms (d - 1))
                       ? Mul (terms (d - 1)) (terms (d - 1)) ? Transpose (terms (d - 1))
census d names = (length ts, [(t, forms) | t <- ts, let forms = distinct t, length forms > 1])
  where ts = sortValues (set1 terms d)
        distinct t = nub (sort [form | (_, form, True) <- normalForms names t])

render (Const n) = show n
render (Var v) = v
render (Add a b) = sub a ++ " + " ++ sub b
render (Mul a b) = sub a ++ " * " ++ sub b
render (Transpose a) = "T " ++ sub a
sub e = case e of Const _ -> render e; Var _ -> render e; _ -> "(" ++ render e ++ ")"
```

The IR's five kinds of node carry no shapes or types.  A rule is defined on
the terms it rewrites and on no other: `twice` has a value on `a * 2` and
none anywhere else.

`step` is one rewrite anywhere in a term, so `step rs e` has one value per
rule and position that applies, and `set2 step rs t` is the set of them.  A
set function collects the choices made inside the call it wraps and none
made outside, so the choice of `chooseValue steps` belongs to `normalize`,
and `set2 normalize` collects one value per rewrite order.  Two orders with
the same rules and result give two equal entries.

`step` is the traversal, and we wrote it.  We did not write the search: no
worklist, no visited set, no backtracking code, and no test beside each rule
that says whether it applies.  The test is `step` itself, asked as a set.

## Every input of a family

`terms 2` is every term of depth at most two over `x`, `2` and `3`, one per
value, and `set1 terms 2` collects them; at depth 0 the guard `d > 0` fails
and `deeper` has no value, the same mechanism as a rule that does not match.
`census` asks `normalForms` of each term and keeps those with more than one
normal form:

```python
# the same rules, asked of every term of a family
def census(rules):
    total, found = curry.eval(C.census(2, rules)).one()
    for term, forms in found[:3]:
        print(f'{show(term)}: {" or ".join(show(f) for f in forms)}')
    most = max((len(forms) for _, forms in found), default=1)
    print(f'{len(found)} of {total:,} terms have more than one normal form; the most is {most}')

census(RULES)
census([r for r in RULES if r != 'twice'])
# 2 * (2 * x): (x + x) + (x + x) or x * 4
# 2 * (3 * x): (x * 3) + (x * 3) or x * 6
# 2 * (x * 2): (x + x) + (x + x) or x * 4
# 56 of 1,179 terms have more than one normal form; the most is 2
# 0 of 1,179 terms have more than one normal form; the most is 1
```

With all eight rules, 56 of the 1,179 terms have two normal forms and none
has three.  Without `twice`, no term has two, so every split involves
`twice`.  That rule is a strength reduction a canonicalizer would not ship
beside `fold`; it is in the set to be found, and the two counts find it.

## Times

`./run` sets `SPRITE_INTERPRETER_FLAGS=backend:cxx,interpret:off`, so the
C++ backend compiles the module before it runs, and clocks each
`curry.eval(goal).one()` on standard error.  On an x86-64 workstation on
2026-11-01, on one core, the second run takes 1.8 s of wall time: the query
on `(x * 3) * 2` takes 4.1 ms, the census with all eight rules 0.9 s and the
census without `twice` 0.4 s, each the median of three warm runs.  The first
run also runs the front end and the C++ compiler, and takes 4.2 s.  With
every module interpreted (`interpret:all,jit:off`), the first census takes
1.1 s.

`plain.py` is the same census in fifty-five lines of plain Python: the rules
as conditions and a worklist with a visited set over the reachable terms.
`python plain.py` agrees, 56 of 1,179, and takes 17 ms on the same machine,
the median of five runs.  Sprite follows every order where the worklist visits
each term once; the orders outnumber the terms, and the 0.9 s bought their
traces, each with its rules, which the worklist discards.  For the count
alone, the plain Python is shorter and takes one fiftieth of the time.

## Limits

The answer is per input and per family, which is weaker than confluence.
Orders multiply with independent rewrite sites, so the inputs here have a
few nodes and the family stops at depth two.  A real canonicalizer runs one
order over thousands of operations; this module tests its rule set, as
Maude's search command does for a rewrite theory.  An e-graph, as in egg,
holds the terms the rules equate in one shared structure and never picks an
order; this module keeps the orders.  The IR has no SSA, regions, shapes or
side effects, and the bound of 32 steps is a literal in `normalize`.  Two
rules that undo each other never end, and the bound reports it with the
flag.

Sprite is the implementation, `curry` its package on PyPI and import name,
and Curry the language.  `pip install --pre curry` brings the Curry front
end with it; `--pre` is needed while Sprite is in alpha.  A C++ compiler on
PATH or the extra `curry[jit]` compiles the module as the program runs;
without either it runs interpreted, as the last time above shows.  From a
checkout, run `make stage` at the root, then `./run` here; `expected.out`
records its standard output.

[Curry in ten minutes](https://andyjost.github.io/Sprite/CurryInTenMinutes.html)
teaches the Curry this lesson assumes. Lesson [24](../24-build-system) asks
the rules of a build what a changed header rebuilds, and lesson
[15](../15-dependency-solver) solves package dependencies with no search code
of its own.
