# The census of go.py in plain Python, for the time beside it: the rules as
# conditions, a traversal, and a search over the terms that any rewrite order
# can reach, with a visited set.  It prints the count and, on standard error,
# the time.  The run script does not run this file.
import sys, time

def at_root(t):
    op, *args = t
    if op in ('Add', 'Mul'):
        a, b = args
        if op == 'Add' and b == ('Const', 0): yield 'addZero', a
        if op == 'Mul' and b == ('Const', 1): yield 'mulOne', a
        if op == 'Mul' and b == ('Const', 0): yield 'mulZero', b
        if a[0] == b[0] == 'Const':
            yield 'fold', ('Const', a[1] + b[1] if op == 'Add' else a[1] * b[1])
        if a[0] == 'Const' and b[0] != 'Const': yield 'constRight', (op, b, a)
        if a[0] == op and a[2][0] == 'Const' and b[0] == 'Const':
            c = a[2][1] + b[1] if op == 'Add' else a[2][1] * b[1]
            yield 'reassoc', (op, a[1], ('Const', c))
        if op == 'Mul' and b == ('Const', 2): yield 'twice', ('Add', a, a)
    elif op == 'Transpose':
        if args[0][0] == 'Transpose': yield 'transpose', args[0][1]
        if args[0][0] == 'Const': yield 'transpose', args[0]

def steps(t):
    yield from at_root(t)
    op, *args = t
    for i, a in enumerate(args):
        if isinstance(a, tuple):
            for name, a2 in steps(a):
                yield name, (op, *args[:i], a2, *args[i + 1:])

def normal_forms(t):
    seen, todo, forms = {t}, [t], set()
    while todo:
        u = todo.pop()
        nexts = {v for _, v in steps(u)}
        if not nexts:
            forms.add(u)
        todo.extend(v for v in nexts if v not in seen)
        seen.update(nexts)
    return forms

def terms(d):
    yield from (('Var', 'x'), ('Const', 2), ('Const', 3))
    if d > 0:
        sub = list(terms(d - 1))
        yield from (('Transpose', a) for a in sub)
        yield from ((op, a, b) for op in ('Add', 'Mul') for a in sub for b in sub)

t0 = time.perf_counter()
family = list(terms(2))
found = [t for t in family if len(normal_forms(t)) > 1]
print(f'{len(found)} of {len(family):,} terms have more than one normal form')
print(f'python census: {(time.perf_counter() - t0) * 1000:.0f} ms', file=sys.stderr)
