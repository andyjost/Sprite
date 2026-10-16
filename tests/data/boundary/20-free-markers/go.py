'''
Free variables on the expression route.  A curry.free() marker crosses the
boundary as one Curry variable: every occurrence in one goal is the same
variable, and the binding a goal makes belongs to that evaluation alone.
The text route declares a variable with "where x free" and reports its
binding; an anonymous "_" is never reported.
'''
import curry

P = curry.import_('Prelude')
eq = getattr(P, '=:=')  # an operator is a symbol of the Prelude, looked up by its name

def vals(*goal, **kwds):
  return list(curry.eval(*goal, converter='topython', **kwds))

def texts(*goal, **kwds):
  return [str(value) for value in curry.eval(*goal, **kwds)]

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except Exception as error:
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# One marker is one variable: the constraint binds x, and both x after it
# are read as 1.  The tuple is the one spelling that pairs a value with the
# binding of a Python-made variable (P24).
x = curry.free()
show('(x =:= 1, x, x)', lambda: vals(([eq, x, 1], x, x)))

# The binding belongs to the evaluation.  The same marker is bound to 2 in
# a second goal, and afterwards it is a free variable again, printed as _a.
show('(x =:= 2, x)', lambda: vals(([eq, x, 2], x)))
show('x afterwards', lambda: texts(x))

# A marker types as a type variable; exprtype gives it a type.
show('typeof free', lambda: curry.typeof(curry.free()))
show("typeof free '[Int]'", lambda: curry.typeof(curry.free(exprtype='[Int]')))

# A free Char inside a String.  Without the converter the value prints as
# PAKCS prints it.  The converter joins the characters into a str and meets
# a node, so a plain TypeError escapes (P21).  The message names the node
# class of the backend, so the class alone is printed.
string = curry.typed([curry.free()], 'String')
show('[_] :: String', lambda: texts(string))
try:
  vals(string)
except TypeError as error:
  print('[_] :: String converted !!', type(error).__name__)

# The text route: "where x free" lifts x and reports its binding; the
# anonymous variable _ gets no report and no name.
goal = curry.compile('_ ++ [x] =:= [1,2,3] where x free', mode='expr')
show('_ ++ [x] =:= [1,2,3] where x free', lambda: texts(goal))
