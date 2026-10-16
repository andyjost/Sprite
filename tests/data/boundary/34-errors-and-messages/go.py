'''
The errors a Python caller meets at the boundary: the first line of the
messages of the typed boundary, and the classes of the exceptions.  They
derive from CurryError, an Exception, so "except Exception" catches an
evaluation error.  A CompileError carries the command line of the front end with the
paths of the installation (P45), so the driver prints its class and the
message line of the front end alone.
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
# that names a Curry signature, which a Python call cannot follow (P44).
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

# A syntax error in a text goal: the report of the front end follows the
# command line in the message (P45).  The line after "Error:" is printed.
try:
  curry.compile('1 +', mode='expr')
except curry.CompileError as error:
  lines = str(error).splitlines()
  report = next(lines[i + 1].strip() for i, line in enumerate(lines) if line.endswith('Error:'))
  print('compile("1 +") !!', type(error).__name__ + ':', report)
