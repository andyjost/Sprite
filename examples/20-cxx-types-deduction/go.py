'''
Template argument deduction over an algebraic model of C++ types.

Builds C++ types and parameter patterns in Python with the constructors of
CxxType, calls one Curry goal per row, and prints the text that comes back.

Usage: python go.py
'''
import os
import curry

# Find Deduction.curry next to this file and the shared modules under ../cxx,
# whatever the working directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, os.path.join(HERE, '..', 'cxx'))
curry.path.insert(0, HERE)
from curry.lib import CxxLimits, CxxType, Deduction

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

def rref(t):
  return curry.expr(CxxType.RRef, t)

def arr(t, n):
  return curry.expr(CxxType.Arr, t, n)

def fun(result, params):
  return curry.expr(CxxType.Fun, result, params)

def cls(name, args=()):
  return curry.expr(CxxType.Class, list(name), list(args))

# The function parameters of a template: by value (p), by lvalue reference
# (p&) and by rvalue reference (p&&).
def by_value(p):
  return curry.expr(CxxType.ByValue, p)

def by_lref(p):
  return curry.expr(CxxType.ByLRef, p)

def by_rref(p):
  return curry.expr(CxxType.ByRRef, p)

# A partial specialization of a class template S, with the names of its
# template parameters: S<T const*> is template(['T'], ptr(const(T))).
def template(names, pattern):
  return curry.expr(CxxType.Template, [list(n) for n in names], pattern)

VOID, CHAR, INT, LONG, DOUBLE = (
    fund('Void'), fund('Char'), fund('Int'), fund('Long'), fund('Double')
  )

# The template parameters.  A pattern refers to one as the class of its
# name.
T, U = cls('T'), cls('U')

def text(goal, *args):
  '''The one value of a goal that returns a String, as a str.'''
  return next(curry.eval(goal, *args, converter='topython'))

def show(t):
  '''A type in C++ syntax, printed by CxxType.showCxx.'''
  return text(CxxType.showCxx, t)

def table(title, rows):
  '''Prints a title and the rows, with every column but the last aligned.'''
  print(title)
  widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]) - 1)]
  for row in rows:
    cells = ['%-*s' % (w, c) for w, c in zip(widths, row)] + [row[-1]]
    print('  ' + '  '.join(cells))

def call(name, names, params, args):
  '''
  One row of (a) or (b): the parameters of the template in C++ spelling,
  the argument types of the call, and the deduction.
  '''
  return (
      text(Deduction.signature, list(name), params)
    , ', '.join(show(a) for a in args)
    , text(Deduction.call, [list(n) for n in names], params, args)
    )

def ordering(specs, targets):
  '''One section of (c): the most specialized of specs for each target.'''
  names = ', '.join(text(Deduction.specName, s) for s in specs)
  table(
      '(c) the most specialized of %s for S<...> with' % names
    , [(show(t), text(Deduction.ordering, specs, t)) for t in targets]
    )

def main():
  # (a) One template parameter T.  The model has types only, so an argument
  # type int& denotes an lvalue of type int, int&& an xvalue, and int a
  # prvalue.  The const of an array is the const of its elements, so
  # int const[3] deduces T = int[3] from f(T const&).
  const_ref = [by_lref(const(T))]
  forward = [by_rref(T)]
  value = [by_value(T)]
  rows = [
      (const_ref, [INT])
    , (const_ref, [lref(const(INT))])
    , (const_ref, [arr(INT, 3)])
    , (const_ref, [arr(const(INT), 3)])
    , (const_ref, [fun(VOID, [INT])])
    , (forward, [lref(INT)])
    , (forward, [rref(INT)])
    , (forward, [INT])
    , (value, [const(INT)])
    , (value, [lref(const(INT))])
    , (value, [arr(INT, 3)])
    , (value, [fun(VOID, [INT])])
    , ([by_value(ptr(const(T)))], [ptr(CHAR)])
    , ([by_value(ptr(T))], [arr(INT, 3)])
    , ([by_value(T), by_value(T)], [INT, DOUBLE])
    , ([by_value(T), by_value(T)], [INT, lref(const(INT))])
    ]
  table(
      '(a) deduce T from the parameters of f and the argument types of a call'
    , [call('f', ['T'], params, args) for params, args in rows]
    )

  # (b) Several parameters, or a parameter inside a class template argument.
  # T occurs in both parameters of g(pair<T, U*>, T), so the two deductions
  # of T must agree.
  pair = [by_value(cls('pair', [T, ptr(U)])), by_value(T)]
  rows = [
      (['T', 'U'], pair, [cls('pair', [INT, ptr(CHAR)]), INT])
    , (['T', 'U'], pair, [cls('pair', [INT, ptr(CHAR)]), LONG])
    , ( ['T'], [by_value(cls('vector', [T]))]
      , [cls('vector', [ptr(const(INT))])]
      )
    ]
  table(
      '(b) deduce the template parameters from the parameters of g and the '
          'argument types of a call'
    , [call('g', names, params, args) for names, params, args in rows]
    )

  # (c) Partial ordering of partial specializations.
  ordering(
      [ template(['T'], T), template(['T'], ptr(T))
      , template(['T'], ptr(const(T)))
      ]
    , [INT, ptr(INT), ptr(const(INT)), const(ptr(const(CHAR)))]
    )
  ordering(
      [ template(['T'], cls('pair', [T, INT]))
      , template(['T'], cls('pair', [INT, T]))
      ]
    , [ cls('pair', [INT, INT]), cls('pair', [CHAR, INT])
      , cls('pair', [CHAR, CHAR])
      ]
    )
  ordering([template(['T'], T), template(['T'], ptr(T))], [ptr(INT)])
  ordering(
      [template(['T'], lref(T)), template(['T'], lref(const(T)))]
    , [lref(INT), lref(const(INT))]
    )
  ordering(
      [ template(['T'], cls('vector', [T]))
      , template(['T'], cls('vector', [ptr(T)]))
      ]
    , [cls('vector', [ptr(INT)]), cls('vector', [INT])]
    )

  # (d) The inverse questions: which types decay to int*, and from which
  # types does f(T const&) deduce T = int?
  depth = 2
  print('(d) the types of depth at most %d that decay to int*: %s'
        % (depth, text(Deduction.inverseDecay, depth, ptr(INT))))
  depth = 1
  print('(d) the types of depth at most %d from which %s deduces T = int: %s'
        % (depth, text(Deduction.signature, list('f'), const_ref)
           , text(Deduction.inverseDeduction, depth, const_ref, INT)))

if __name__ == '__main__':
  main()
