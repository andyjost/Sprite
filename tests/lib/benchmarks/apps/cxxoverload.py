'''
Overload resolution in plain Python: the opponent of example 21 in the
applications suite.

The module ranks a call against an overload set with the rules of
CxxOverload.curry (examples/cxx) for the types of the workload of the
suite: the fundamental types, pointers, const, and classes with a
hierarchy.  No references, arrays, functions or pointers to members: the
workload has none.  A type is a tuple: ``('fund', 'Int')``, ``('const', t)``,
``('ptr', t)``, ``('class', 'Base')``; a candidate is ``(name, [types])``;
a hierarchy is a list of ``(derived, base)`` pairs.  ``resolve`` returns the
text of CxxOverload.showResolution, so the two sides compare their answers
as strings.
'''

__all__ = ['resolve', 'show_cxx', 'show_candidate']

EXACT, PROMOTION, CONVERSION = 0, 1, 2
RANKS = ('exact', 'promotion', 'conversion')
SPELLING = {
    'Void': 'void', 'Bool': 'bool', 'Char': 'char', 'SChar': 'signed char'
  , 'UChar': 'unsigned char', 'Short': 'short', 'UShort': 'unsigned short'
  , 'Int': 'int', 'UInt': 'unsigned int', 'Long': 'long'
  , 'ULong': 'unsigned long', 'LLong': 'long long'
  , 'ULLong': 'unsigned long long', 'Float': 'float', 'Double': 'double'
  , 'LDouble': 'long double', 'NullptrT': 'std::nullptr_t'
  }
INTEGRAL = (
    'Bool', 'Char', 'SChar', 'UChar', 'Short', 'UShort', 'Int', 'UInt', 'Long'
  , 'ULong', 'LLong', 'ULLong'
  )
FLOATING = ('Float', 'Double', 'LDouble')
# The types that promote to int ([conv.prom]).
PROMOTES_TO_INT = ('Bool', 'Char', 'SChar', 'UChar', 'Short', 'UShort')
BOOL = ('fund', 'Bool')


def bare(t):
  return t[1] if t[0] == 'const' else t

def is_const(t):
  return t[0] == 'const'

def is_fund(t, names):
  b = bare(t)
  return b[0] == 'fund' and b[1] in names

def is_arithmetic(t):
  return is_fund(t, INTEGRAL + FLOATING)

def is_pointer(t):
  return bare(t)[0] == 'ptr'

def is_class(t):
  return bare(t)[0] == 'class'

def is_void(t):
  return is_fund(t, ('Void',))

def pointer_to(test, t):
  return is_pointer(t) and test(bare(t)[1])

def derives(h, d, b):
  return any(x == d and (y == b or derives(h, y, b)) for x, y in h)

def promotes(a, p):
  return is_fund(a, PROMOTES_TO_INT) and p == ('fund', 'Int') \
      or a == ('fund', 'Float') and p == ('fund', 'Double')

def chain(t):
  '''The constness of each level of a pointer chain, and the type at its end.'''
  levels = []
  while t[0] == 'ptr':
    levels.append(is_const(t[1]))
    t = bare(t[1])
  return levels, t

def qualifies(a, b):
  '''A qualification conversion from a to b ([conv.qual]).'''
  la, enda = chain(a)
  lb, endb = chain(b)
  if enda != endb or len(la) != len(lb):
    return False
  all_const = True
  for c1, c2 in zip(la, lb):
    if (c1 and not c2) or (c1 != c2 and not all_const):
      return False
    all_const = all_const and c2
  return True

def standard(h, a, p):
  '''The rank of the standard conversion sequence from a to p, or None.'''
  if a == p or qualifies(a, p):
    return EXACT
  if promotes(a, p):
    return PROMOTION
  if is_arithmetic(a) and is_arithmetic(p) and p != BOOL:
    return CONVERSION
  if p == BOOL and (is_arithmetic(a) or is_pointer(a)):
    return CONVERSION
  if pointer_to(lambda u: not is_void(u), a) and pointer_to(is_void, p) \
      and (not is_const(a[1]) or is_const(p[1])):
    return CONVERSION
  if pointer_to(is_class, a) and pointer_to(is_class, p) \
      and derives(h, bare(a[1])[1], bare(p[1])[1]) \
      and (not is_const(a[1]) or is_const(p[1])):
    return CONVERSION
  if is_fund(a, ('NullptrT',)) and is_pointer(p):
    return CONVERSION
  if is_class(a) and is_class(p) and derives(h, a[1], p[1]):
    return CONVERSION
  return None

def tie_break(h, a, t1, t2):
  '''The order among two sequences of the same rank ([over.ics.rank]/4).'''
  return is_pointer(a) and t1 != BOOL and t2 == BOOL \
      or is_pointer(a) and pointer_to(is_class, t1) and pointer_to(is_void, t2) \
      or is_pointer(a) and pointer_to(is_class, t1) and pointer_to(is_class, t2) \
         and derives(h, bare(t1[1])[1], bare(t2[1])[1]) \
      or is_class(a) and is_class(t1) and is_class(t2) and derives(h, t1[1], t2[1]) \
      or is_pointer(a) and t1 != t2 and qualifies(t1, t2)

def better(h, a, s1, s2):
  (r1, t1), (r2, t2) = s1, s2
  return r1 < r2 if r1 != r2 else tie_break(h, a, t1, t2)

def better_candidate(h, args, v, w):
  seqs = lambda c: list(zip(c[1], [bare(p) for p in c[0][1]]))
  pairs = list(zip(args, seqs(v), seqs(w)))
  return all(not better(h, a, s2, s1) for a, s1, s2 in pairs) \
      and any(better(h, a, s1, s2) for a, s1, s2 in pairs)

def resolve(h, candidates, args):
  '''The result of overload resolution, as CxxOverload prints it.'''
  args = [bare(a) for a in args]
  viable = []
  for cand in candidates:
    if len(cand[1]) == len(args):
      ranks = [standard(h, a, bare(p)) for a, p in zip(args, cand[1])]
      if None not in ranks:
        viable.append((cand, ranks))
  if not viable:
    return 'no viable function'
  best = [
      v for v in viable
        if all(w == v or better_candidate(h, args, v, w) for w in viable)
    ]
  if len(best) == 1:
    (cand, ranks), = best
    return '%s [%s]' % (show_candidate(cand), ', '.join(RANKS[r] for r in ranks))
  maximal = [
      v for v in viable
        if not any(better_candidate(h, args, w, v) for w in viable)
    ]
  return 'ambiguous: ' + ', '.join(show_candidate(c) for c, _ in maximal)

def show_candidate(cand):
  return '%s(%s)' % (cand[0], ', '.join(show_cxx(p) for p in cand[1]))

def show_cxx(t):
  '''A type in C++ syntax, as CxxType.showCxx writes it.'''
  return _declare(t, '')

def _declare(t, d):
  if t[0] == 'fund':
    return _join(SPELLING[t[1]], d)
  if t[0] == 'class':
    return _join(t[1], d)
  if t[0] == 'ptr':
    return _declare(t[1], _prefix('*', d))
  u = t[1]
  if u[0] == 'ptr':
    return _declare(u[1], _prefix('* const', d))
  return _join((SPELLING[u[1]] if u[0] == 'fund' else u[1]) + ' const', d)

def _prefix(op, d):
  gap = ' ' if d and (d[0] == '(' or d[0].isalnum() or d[0] == '_') else ''
  return op + gap + d

def _join(base, d):
  if not d:
    return base
  return base + d if d[0] in '*&[' else base + ' ' + d
