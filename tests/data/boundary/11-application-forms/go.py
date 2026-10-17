'''
The forms of an application at the boundary.

A symbol is a function value where a function is expected, a call with
fewer arguments than the arity is a partial application, and a surplus
argument goes through apply when the result type has the arrow, as in
Curry.  Too many arguments for a symbol whose result is not a function is
refused.  A class method alone, show, cannot be defaulted and is refused
with the REPL's sentence and the spelling that states the type.  With an
argument the constraint is defaulted and the goal runs.  A relation of a
program, rule, passes as a value to a function that takes it.
'''
import curry, os

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = curry.import_('Prelude')
App = curry.import_('App')

def show(label, thunk, lines=1):
  '''Prints the value of one probe, or the class and the first lines of its error.'''
  try:
    print(label, '->', repr(thunk()))
  except Exception as e:
    print(label, '!!', type(e).__name__ + ':', '\n'.join(str(e).splitlines()[:lines]))

# A symbol as a value: map takes inc as its function.
show('map inc [1, 2]', lambda: list(curry.eval(P.map(App.inc, [1, 2]))))
show('typeof inc', lambda: curry.typeof(App.inc))

# A partial application is a function of the remaining parameters.
show("typeof (rule 'a')", lambda: curry.typeof(App.rule('a')))
show("str (rule 'a')", lambda: str(App.rule('a')))
inputs = [['x'], ['y', 'z']]
show("map (rule 'a') inputs", lambda: list(curry.eval(P.map(App.rule('a'), inputs))))

# Over-application: id takes one argument, and its result here is a
# function, so the surplus 1 goes through apply.  The text shows it.
show('str (id inc 1)', lambda: str(P.id(App.inc, 1)))
show('id inc 1', lambda: list(curry.eval(P.id(App.inc, 1))))

# inc returns an Int, which takes no argument: refused.
show('inc 1 2', lambda: list(curry.eval(App.inc(1, 2))))

# A class method alone: Show a stays open, and the goal is refused with
# the three lines.  With an argument, Num a defaults to Int and show runs.
show('typeof show', lambda: curry.typeof(P.show))
show('show', lambda: list(curry.eval(P.show)), lines=3)
show('show 1', lambda: list(curry.eval(P.show(1))))

# A relation as a value: rule has one equation per rule, and usesRel
# applies the relation it is given.
show("rule 'a' ['x']", lambda: list(curry.eval(App.rule('a', ['x']))))
show('usesRel rule', lambda: list(curry.eval(App.usesRel(App.rule))))
