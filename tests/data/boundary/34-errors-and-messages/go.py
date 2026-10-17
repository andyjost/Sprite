'''
The errors a Python caller meets at the boundary, on the public API
surface: one tree under curry.CurryError, an Exception, with the standard class
mixed in; a term is typed at the call that builds it, so a typing failure is
raised there; messages name the rule and the spelling and carry no path.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = curry.import_('Err')
P = curry.import_('Prelude')

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except Exception as error:
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# The messages of the typed boundary name the symbol and its scheme.  A str
# is a String; curry.Char is the character, and length wants a list.
show("length 'a'", lambda: P.length(curry.Char('a')))
show('inc 1 2', lambda: M.inc(1, 2))
show('succ [succ, pred]', lambda: P.succ([P.succ, P.pred]))
show('term(None)', lambda: curry.term(None))

# A lone class method as a goal: the sentence of the PAKCS REPL, and the
# spelling that follows it.
try:
  curry.eval(P.show).one()
except curry.CurryTypeError as error:
  print('eval(show) !!', type(error).__name__ + ':')
  for line in str(error).splitlines():
    print('   ', line)

# The classes: one tree under CurryError, an Exception.
print('typed errors are CurryTypeError ->', all(
    issubclass(cls, curry.CurryTypeError)
    for cls in (
      curry.MismatchError, curry.ArityError, curry.NoInstanceError, curry.ConversionError)))
print('CurryTypeError is a TypeError ->', issubclass(curry.CurryTypeError, TypeError))
print('EvaluationError is an Exception ->', issubclass(curry.EvaluationError, Exception))
print('CompileError is an Exception ->', issubclass(curry.CompileError, Exception))
print('SuspensionError under EvaluationError ->',
      issubclass(curry.SuspensionError, curry.EvaluationError))
print('every error under CurryError ->', all(
    issubclass(cls, curry.CurryError) for cls in (curry.CurryTypeError, curry.CompileError,
        curry.EvaluationError, curry.NoValueError, curry.ManyValuesError)))

# What that means for a try: "except Exception" catches an EvaluationError.
try:
  list(curry.eval(M.boom))
except Exception as error:
  print('except Exception -> caught', type(error).__name__)

# A free variable has a name.
show("free('x')", lambda: curry.free('x'))

# A syntax error in a text goal: the first error line, no path.
try:
  curry.parse('1 +')
except curry.CompileError as error:
  print('parse("1 +") !!', type(error).__name__ + ':', error)
