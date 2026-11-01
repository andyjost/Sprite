# Every normal form of a term of a small IR, then a census of the terms of a
# family whose rules disagree.  The times go to standard error.
import sys, time
import curry
curry.path.insert(0, '.')
from curry.lib import Canon as C                  # imports ./Canon.curry

RULES = curry.eval(C.ruleNames).one()             # the goal has exactly one value; .one() takes it
x, k = C.Var('x'), C.Const                        # x is a variable, k(3) the constant 3
e = C.Mul(C.Mul(x, k(3)), k(2))                   # (x * 3) * 2

def show(term):
    return curry.eval(C.render(term)).one()

goal = C.normalForms(RULES, e)
t0 = time.perf_counter()
orders = curry.eval(goal).one()
print(f'normalForms: {(time.perf_counter() - t0) * 1000:.1f} ms', file=sys.stderr)
for used, form, done in orders:
    note = '' if done else '  (no normal form within 32 steps)'
    print(f'{" ".join(used):12} {show(form)}{note}')
forms = [form for _, form, _ in orders]
print(C.Mul(x, k(6)) in forms)                    # a normal form is a term Python can compare

# the same rules, asked of every term of a family
def census(rules):
    goal = C.census(2, rules)
    t0 = time.perf_counter()
    total, found = curry.eval(goal).one()
    print(f'census: {time.perf_counter() - t0:.2f} s', file=sys.stderr)
    for term, forms in found[:3]:
        print(f'{show(term)}: {" or ".join(show(f) for f in forms)}')
    most = max((len(forms) for _, forms in found), default=1)
    print(f'{len(found)} of {total:,} terms have more than one normal form; the most is {most}')

census(RULES)
census([r for r in RULES if r != 'twice'])
