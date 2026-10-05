'''
Overload resolution as search over an algebraic model of C++ types.

Builds overload sets, a class hierarchy and calls in Python, asks Curry for
the viable candidates of each call and for the best one, and prints the
answers.  The last scenario asks the inverse question: which argument types
make a call ambiguous.

Usage: python go.py
'''
import os
import curry

# Find Overloads.curry next to this file and the shared modules under ../cxx,
# whatever the working directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, os.path.join(HERE, '..', 'cxx'))
curry.path.insert(0, HERE)
from curry.lib import CxxLimits, CxxType, Overloads

# The constructors of CxxType.Type, applied with curry.expr.  A class name is
# passed as a list of characters: a str of length one would become a Char.
def fund(name):
  return curry.expr(CxxType.Fund, getattr(CxxLimits, name))

def const(t):
  return curry.expr(CxxType.Const, t)

def ptr(t):
  return curry.expr(CxxType.Ptr, t)

def lref(t):
  return curry.expr(CxxType.LRef, t)

def arr(t, n):
  return curry.expr(CxxType.Arr, t, n)

def cls(name):
  return curry.expr(CxxType.Class, list(name), [])

VOID, BOOL, CHAR, INT = fund('Void'), fund('Bool'), fund('Char'), fund('Int')
LONG, FLOAT, DOUBLE, NULLPTR = fund('Long'), fund('Float'), fund('Double'), fund('NullptrT')
BASE, DERIVED = cls('Base'), cls('Derived')

# A class hierarchy is a list of (derived, base) pairs.  An overload set is a
# list of candidates (name, [parameter types]).  curry.eval turns a Python
# tuple into a Curry tuple and a Python list into a Curry list.  The names
# are lists of characters for the same reason as the class names above.
HIERARCHY = [(list('Derived'), list('Base'))]

def candidate(name, *params):
  return (list(name), list(params))

def text(goal, *args):
  '''The one value of a goal that returns a String, as a str.'''
  return next(curry.eval(goal, *args, converter='topython'))

def show(t):
  '''A type in C++ syntax, printed by CxxType.showCxx.'''
  return text(CxxType.showCxx, t)

def signature(name, types):
  '''A declaration or a call in C++ syntax: "f(int, char const*)".'''
  return '%s(%s)' % (name, ', '.join(show(t) for t in types))

def section(title, name, overloads, hierarchy, calls):
  '''Prints the overload set and, for each call, the viable candidates with
  their ranks and the result of overload resolution.'''
  print('%s %s' % (title, ', '.join(signature(name, params) for _, params in overloads)))
  labels = [signature(name, args) for args in calls]
  width = max(len(label) for label in labels)
  for label, args in zip(labels, calls):
    viable = text(Overloads.viableLine, hierarchy, overloads, args)
    result = text(Overloads.resultLine, hierarchy, overloads, args)
    print('  %-*s  viable: %s' % (width, label, viable))
    print('  %-*s  result: %s' % (width, '', result))

def main():
  # (a) The three ranks: exact match, promotion, conversion.
  f3 = [candidate('f', INT), candidate('f', LONG), candidate('f', DOUBLE)]
  section('(a) overloads', 'f', f3, [], [[INT], [CHAR], [FLOAT], [BOOL], [ptr(INT)]])

  # (b) The classic ambiguity: two conversions of the same rank.
  f2 = [candidate('f', LONG), candidate('f', DOUBLE)]
  section('(b) overloads', 'f', f2, [], [[INT], [FLOAT]])

  # (c) Pointers, with the class Derived derived from Base.
  g3 = [candidate('g', ptr(VOID)), candidate('g', ptr(BASE)), candidate('g', ptr(DERIVED))]
  section('(c) class Derived : Base; overloads', 'g', g3, HIERARCHY,
          [[ptr(DERIVED)], [NULLPTR], [ptr(const(DERIVED))]])
  # Sequences of the same rank, ordered by the rules of [over.ics.rank]/4.
  # std::nullptr_t converts to every pointer, and not to bool.
  k5 = [candidate('k', ptr(INT)), candidate('k', ptr(const(INT))), candidate('k', ptr(VOID))
        , candidate('k', ptr(BASE)), candidate('k', BOOL)]
  section('(c) class Derived : Base; overloads', 'k', k5, HIERARCHY,
          [[ptr(DERIVED)], [ptr(INT)], [NULLPTR]])
  # A reference to const of array type binds an array lvalue directly, with
  # no array-to-pointer conversion, and only an array of the same bound.
  h2 = [candidate('h', lref(const(arr(INT, 3)))), candidate('h', ptr(INT))]
  section('(c) overloads', 'h', h2, [], [[arr(INT, 3)], [arr(const(INT), 3)], [arr(INT, 4)]])

  # (d) The inverse question: which argument types make the call ambiguous?
  depth = 2
  fi = [candidate('f', LONG), candidate('f', DOUBLE), candidate('f', ptr(const(INT)))]
  print('(d) the argument types of depth at most %d that make the call ambiguous for %s'
        % (depth, ', '.join(signature('f', params) for _, params in fi)))
  print('  %s' % text(Overloads.ambiguousArgs, depth, fi))

if __name__ == '__main__':
  main()
