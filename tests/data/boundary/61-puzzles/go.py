'''
Constraint puzzles with several free variables, driven from Python (the
public API).

horseman and colormap of PAKCS cross the boundary by import.  Each goal has
free parameters; the driver makes one named variable per parameter with
curry.free(name) and applies the goal to them; curry.solve yields an Answer
per value, the value and the bindings by name.  horseman relates men, horses,
heads and feet in Peano arithmetic; colormap colours a map of four regions by
generate and test with the concurrent conjunction (&).  The values come in
the order of the scheduler under step mode.
'''
import os
import curry

curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
horseman, colormap = curry.import_('horseman'), curry.import_('colormap')

def peano(value):
  '''The number of a Peano value read back: the count of S in its text.'''
  return str(value).count('S')

# goal1: three heads and eight feet.  One value: two men and one horse.
m, h = curry.free('m'), curry.free('h')
print('goal1 m h ->', [str(a) for a in curry.solve(horseman.goal1(m, h))])

# goal2: eight heads and twenty feet.  The Peano terms are long, so the
# driver counts their S constructors.
for value, b in curry.solve(horseman.goal2(m, h)):
  print('goal2 -> men %d, horses %d' % (peano(b['m']), peano(b['h'])))

# goal3: two heads and any number of feet.  Three values: the pairs with
# two heads and the feet each pair has.
hd = curry.free('hd')
for value, b in curry.solve(horseman.goal3(m, h, hd)):
  men, horses, feet = (peano(x) for x in b.values())
  print('goal3 -> men %d, horses %d, feet %d' % (men, horses, feet))

# colormap.goal with four named variables.  The goal is coloring & correct,
# and correct is False for most colourings.  Sprite's (&) yields False when
# one side is False, so the goal has a value for every one of the 256
# colourings, 48 of them True; PAKCS's (&) has no value there and prints 48
# rows (#139).  The driver prints both counts and the first three True values.
l = [curry.free('l%d' % i) for i in (1, 2, 3, 4)]
answers = list(curry.solve(colormap.goal(*l)))
correct = [a for a in answers if a.value]
print('colormap: %d values, %d of them True' % (len(answers), len(correct)))
for answer in correct[:3]:
  print('  ', answer)
