'''
"where x free" on the text route.  curry.compile(text, mode='expr') lifts
a trailing clause into a Bindings value that prints as the PAKCS REPL
prints, {x=1} True.  The variables reported follow Sprite's own rule: a
variable whose type occurs in the type of the result is left in the value
and not reported (P25), where PAKCS reports every variable of the clause.
A trailing comment or an exprtype keeps the clause a local declaration,
and nothing is reported (P26).
'''
import curry

def goal(text, **kwds):
  return curry.compile(text, mode='expr', **kwds)

def texts(goal, **kwds):
  kwds.setdefault('converter', None)
  return [str(value) for value in curry.eval(goal, **kwds)]

def show(text, **kwds):
  note = ''.join(' (%s=%r)' % item for item in kwds.items())
  print(text + note, '->', texts(goal(text, **kwds)))

# One variable, bound by a constraint on an Int and on a list.
show('x =:= 1 where x free')
show('xs ++ [3] =:= [1,2,3] where xs free')

# A pair whose second component is a list: without annotations the type of
# xs is a fresh variable, absent from the type of the result, so xs is
# reported.  With the annotations the type [Int] of xs occurs in the type
# of the result and xs is not reported, where PAKCS prints
# {xs=[1]} (True,[0]) for both (P25; the oracle shows it).
show('(xs =:= [1], [0]) where xs free')
show('(xs =:= [1 :: Int], [0 :: Int]) where xs free')

# A comment after the clause defeats the lift; PAKCS prints True as well
# (P26).  An exprtype keeps the clause local too.
show('x =:= 1 where x free -- comment')
show('x =:= 1 where x free', exprtype='Bool')

# Several variables: one Bindings per solution, in the order of the search
# under step mode.
show('xs ++ ys =:= [1,2] where xs, ys free')

# The two printers of Bindings (P20): the Curry printer spaces a list as
# [1, 2]; the converted Bindings prints its Python values with show_value,
# as [1,2].  The lifted goal records no type, so typeof answers a.
lifted = goal('xs ++ [3] =:= [1,2,3] where xs free')
print('converted ->', texts(lifted, converter='topython'))
item = curry.solve(curry.parse('xs ++ [3] =:= [1,2,3] where xs free')).one()
print('  value:', item.value, ' bindings:', item.bindings)
print('typeof of the lifted goal ->', curry.typeof(lifted))
