'''
Free variables on the expression route under the public API.  A
named variable crosses the boundary as one Curry variable: every
occurrence in one goal is the same variable, and the binding a goal makes
belongs to that evaluation alone.  The text route declares a variable with
"where x free" and curry.solve reports its binding; an anonymous "_" is
never reported.
'''
import curry

P = curry.import_('Prelude')
eq = P['=:=']

def show(label, thunk):
  try:
    print(label, '->', repr(thunk()))
  except Exception as error:
    print(label, '!!', type(error).__name__ + ':', str(error).splitlines()[0])

# One variable is one variable: the constraint binds x, and both x after it
# are read as 1.  An anonymous variable is not reported, so eval gives the
# value alone.
x = curry.free('x')
show('(x =:= 1, x, x)', lambda: list(curry.eval((eq(x, 1), x, x))))

# The binding belongs to the evaluation.  The same variable is bound to 2
# in a second goal, and afterwards it is a free variable again, printed as
# _a.
show('(x =:= 2, x)', lambda: list(curry.eval((eq(x, 2), x))))
show('x afterwards', lambda: [str(value) for value in curry.eval(x)])

# A variable types as a type variable; type= gives it a type.
show('typeof free', lambda: curry.typeof(curry.free('x')))
show("typeof free '[Int]'", lambda: curry.typeof(curry.free('xs', type='[Int]')))

# A free Char inside a String.  Shown, it prints as PAKCS prints it;
# converted, it is a list that holds the Var.
string = curry.term([curry.free('x')], type='String')
show('[_] :: String', lambda: [curry.show(value) for value in curry.eval(string)])
show('[_] :: String converted', lambda: list(curry.eval(string)))

# The text route: "where x free" declares x and solve reports its binding;
# the anonymous variable _ gets no report and no name.
goal = curry.parse('_ ++ [x] =:= [1,2,3] where x free')
show('_ ++ [x] =:= [1,2,3] where x free', lambda: [str(answer) for answer in curry.solve(goal)])

# Each anonymous occurrence is independent and absent from bindings.
goal = curry.term((curry.anonymous, curry.anonymous), type='(Int, Int)')
show('anonymous bindings', lambda: [list(a.bindings) for a in curry.solve(goal)])
