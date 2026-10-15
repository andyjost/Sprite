'''
Constraint puzzles with several free variables, driven from Python.

horseman and colormap of PAKCS cross the boundary as modules.  Each goal has
free parameters; the driver makes one marker per parameter with curry.free()
and puts the goal and the markers in one tuple, so that each value carries
the bindings.  horseman relates men, horses, heads and feet in Peano
arithmetic; colormap colours a map of four regions by generate and test with
the concurrent conjunction (&).  The values come in the order of the
scheduler under step mode.
'''
import os, curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import horseman, colormap

def texts(*goal):
  return [str(v) for v in curry.eval(*goal)]

def peano(term):
  '''The number of a Peano term read back: the count of S in its text.'''
  return str(term).count('S')

# goal1: three heads and eight feet.  One value: two men and one horse.
m, h = curry.free(), curry.free()
print('(goal1 m h, m, h) ->', texts(([horseman.goal1, m, h], m, h)))

# goal2: eight heads and twenty feet.  The Peano terms are long, so the
# driver counts their S constructors.
m, h = curry.free(), curry.free()
for value in curry.eval(([horseman.goal2, m, h], m, h)):
  print('goal2 -> men %d, horses %d' % (peano(value[1]), peano(value[2])))

# goal3: two heads and any number of feet.  Three values: the pairs with
# two heads and the feet each pair has.  A Curry tuple read back indexes by
# an int and not by a slice, so the components are taken one by one.
m, h, hd = curry.free(), curry.free(), curry.free()
for value in curry.eval(([horseman.goal3, m, h, hd], m, h, hd)):
  men, horses, feet = (peano(value[i]) for i in (1, 2, 3))
  print('goal3 -> men %d, horses %d, feet %d' % (men, horses, feet))

# colormap.goal with four markers.  The goal is coloring & correct, and
# correct is False for most colourings.  Sprite's (&) yields False when one
# side is False, so the goal has a value for every one of the 256
# colourings, 48 of them True; PAKCS's (&) has no value there and prints 48
# rows.  The driver prints both counts and the first three True values.
l = [curry.free() for _ in range(4)]
values = list(curry.eval(([colormap.goal] + l, *l)))
correct = [str(v) for v in values if str(v[0]) == 'True']
print('colormap: %d values, %d of them True' % (len(values), len(correct)))
for value in correct[:3]:
  print('  ', value)
