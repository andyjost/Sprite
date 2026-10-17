'''
"where x free" on the text route under the public API.
curry.parse(text) reads a goal as the REPL reads it; a trailing clause
declares named variables, and curry.solve yields an Answer per value that
prints as the PAKCS REPL prints, {x=1} True.  Every declared variable is
reported.  A type annotation is written in Curry before the clause.  A
trailing comment keeps the clause a local declaration, and nothing is
reported.
'''
import curry

def show(text):
  print(text, '->', [str(answer) for answer in curry.solve(curry.parse(text))])

# One variable, bound by a constraint on an Int and on a list.
show('x =:= 1 where x free')
show('xs ++ [3] =:= [1,2,3] where xs free')

# A pair whose second component is a list: xs is reported with and without
# the annotations, as PAKCS prints {xs=[1]} (True,[0]) for both.
show('(xs =:= [1], [0]) where xs free')
show('(xs =:= [1 :: Int], [0 :: Int]) where xs free')

# A comment after the clause defeats the lift; PAKCS prints True as well.
# A type annotation is written in Curry and keeps the report.
show('x =:= 1 where x free -- comment')
show('(x =:= 1) :: Bool where x free')

# Several variables: one Answer per solution, in the order of the search
# under step mode.
show('xs ++ ys =:= [1,2] where xs, ys free')

# One printer: the Answer prints its Python values as PAKCS spaces them,
# and holds the value and the bindings.  typeof of the goal is its type.
lifted = curry.parse('xs ++ [3] =:= [1,2,3] where xs free')
item, = curry.solve(lifted)
print('  value:', item.value, ' bindings:', item.bindings)
print('typeof of the lifted goal ->', curry.typeof(lifted))
