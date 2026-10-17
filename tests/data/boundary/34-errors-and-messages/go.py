'''
The errors a Python caller meets at the boundary: the first line of the
messages of the typed boundary, and the classes of the exceptions.  They
derive from CurryError, an Exception, so "except Exception" catches an
evaluation error. CompileError.report retains the front-end diagnostic;
its str is the first error without a machine path (A21). The driver
prints the class and the diagnostic alone.
'''
import os, curry
import curry.typecheck.errors  # the classes of the typed boundary (P42: not exported)

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Err')
P = curry.import_('Prelude')

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except Exception as error:
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# The messages of the typed boundary name the symbol, its scheme, the
# argument and the types (P44).  A str of length 1 built on its own is a
# Char (P1), and length wants a list.
show("length 'a'", lambda: curry.expr(P.length, curry.expr('a')))
show('inc 1 2', lambda: curry.expr(M.inc, 1, 2))
show('succ [succ, pred]', lambda: curry.expr(P.succ, [P.succ, P.pred]))
show('expr(None)', lambda: curry.expr(None))

# A lone class method as a goal: the sentence of the PAKCS REPL, and a hint
# that gives the Python type spelling (P44).
try:
  curry.eval(P.show)
except curry.CurryTypeError as error:
  print('eval(show) !!', type(error).__name__ + ':')
  for line in str(error).splitlines():
    print('   ', line)

# The classes.  The typed errors are TypeErrors; all are Exceptions (A20).
E = curry.typecheck.errors
print('typed errors are CurryTypeError ->', all(
    issubclass(cls, curry.CurryTypeError)
    for cls in (E.MismatchError, E.ArityError, E.NoInstanceError, E.ConversionError)))
print('CurryTypeError is a TypeError ->', issubclass(curry.CurryTypeError, TypeError))
print('EvaluationError is an Exception ->', issubclass(curry.EvaluationError, Exception))
print('CompileError is an Exception ->', issubclass(curry.CompileError, Exception))
print('EvaluationSuspended under EvaluationError ->',
      issubclass(curry.EvaluationSuspended, curry.EvaluationError))

# What that means for a try: "except Exception" catches an EvaluationError.
def attempt(kind):
  try:
    list(curry.eval(M.boom))
  except kind as error:
    return 'caught ' + type(error).__name__
try:
  print('except Exception ->', attempt(Exception))
except BaseException as error:
  print('except Exception -> escaped', type(error).__name__)
print('except BaseException ->', attempt(BaseException))

# Errors beside CurryTypeError leak from the builders (P43).
show("free('x')", lambda: curry.free('x'))

# A syntax error carries the diagnostic, without the command line (A21).
try:
  curry.compile('1 +', mode='expr')
except curry.CompileError as error:
  report = error.report.split('Error:', 1)[-1].strip().splitlines()[0]
  print('compile("1 +") !!', type(error).__name__ + ':', report)
