'''
Type inference by unification.

Builds lambda terms in Python, infers their types in Curry, and prints each
term with its type.  A term with no type prints "ill-typed".

Usage: python go.py [TERM ...]

A TERM is a Python literal of nested tuples, for example
"('app', ('lit', 1), ('lit', 2))".  Without arguments the built-in terms run.
'''
import ast
import os
import sys
import curry

# Find Infer.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Infer

# Terms as nested tuples.  The first element names the constructor of Infer.Term.
TERMS = [
    # Well-typed terms.
    ('lam', 'x', ('var', 'x')),
    ('lam', 'x', ('lam', 'y', ('var', 'x'))),
    ('lam', 'f', ('lam', 'x', ('app', ('var', 'f'), ('app', ('var', 'f'), ('var', 'x'))))),
    ('lam', 'f', ('lam', 'g', ('lam', 'x', ('app', ('var', 'f'), ('app', ('var', 'g'), ('var', 'x')))))),
    ('lam', 'b', ('lam', 'x', ('if', ('var', 'b'), ('add', ('var', 'x'), ('lit', 1)), ('var', 'x')))),
    ('app', ('lam', 'x', ('add', ('var', 'x'), ('lit', 1))), ('lit', 41)),
    # Terms with no type.
    ('app', ('lit', 1), ('lit', 2)),
    ('if', ('lit', 1), ('lit', 2), ('lit', 3)),
    ('if', ('bool', True), ('lit', 1), ('bool', False)),
    ('lam', 'b', ('if', ('var', 'b'), ('add', ('var', 'b'), ('lit', 1)), ('lit', 0))),
    ('lam', 'f', ('add', ('app', ('var', 'f'), ('lit', 1)), ('app', ('var', 'f'), ('bool', True)))),
    ('var', 'y'),
  ]

def build(term):
  '''Converts a nested tuple into a Curry term of type Infer.Term.'''
  tag = term[0]
  if tag == 'var':
    return curry.expr(Infer.Var, term[1])
  if tag == 'lam':
    return curry.expr(Infer.Lam, term[1], build(term[2]))
  if tag == 'app':
    return curry.expr(Infer.App, build(term[1]), build(term[2]))
  if tag == 'lit':
    return curry.expr(Infer.Lit, term[1])
  if tag == 'bool':
    return curry.expr(Infer.BoolLit, term[1])
  if tag == 'if':
    return curry.expr(Infer.If, build(term[1]), build(term[2]), build(term[3]))
  if tag == 'add':
    return curry.expr(Infer.Add, build(term[1]), build(term[2]))
  raise ValueError('unknown term: %r' % (term,))

def show(term):
  '''Prints a term in lambda syntax.'''
  tag = term[0]
  if tag == 'var':
    return term[1]
  if tag in ('lit', 'bool'):
    return str(term[1])
  if tag == 'lam':
    return '\\%s -> %s' % (term[1], show(term[2]))
  if tag == 'app':
    return '%s %s' % (wrap(term[1], 'lam', 'if', 'add'),
                      wrap(term[2], 'lam', 'if', 'add', 'app'))
  if tag == 'add':
    return '%s + %s' % (wrap(term[1], 'lam', 'if'),
                        wrap(term[2], 'lam', 'if', 'add'))
  if tag == 'if':
    return 'if %s then %s else %s' % (show(term[1]), show(term[2]), show(term[3]))
  raise ValueError('unknown term: %r' % (term,))

def wrap(term, *tags):
  '''Shows a term, in parentheses when its constructor is one of tags.'''
  s = show(term)
  return '(%s)' % s if term[0] in tags else s

def infer(term):
  '''Returns the types of a term as strings.  An ill-typed term has none.'''
  # The empty list is the empty environment: no variable is in scope.
  # A type with unbound variables prints them as _a, _b, and so on.
  return [str(ty) for ty in curry.eval(Infer.infer, [], build(term))]

def main(terms):
  for term in terms:
    types = infer(term)
    print('%s : %s' % (show(term), ' | '.join(types) if types else 'ill-typed'))

if __name__ == '__main__':
  main([ast.literal_eval(arg) for arg in sys.argv[1:]] or TERMS)
