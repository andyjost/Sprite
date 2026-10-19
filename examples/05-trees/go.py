# A tree built by Curry comes to Python as an instance of its constructor's
# class; Python takes it apart with match, builds one of its own, and hands
# it back.  Then Curry generates trees.
import os
import curry
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Tree as T

t = curry.eval(T.fromList([5, 3, 8, 1, 4])).one()
print(curry.show(t))
print(curry.eval(T.size(t)).one(), curry.eval(T.depth(t)).one(), curry.eval(T.leaves(t)).one())

# The same functions in Python, by match on the constructors.
def size(tree):
  match tree:
    case T.Leaf: return 0
    case T.Node(l, _, r): return size(l) + 1 + size(r)

def depth(tree):
  match tree:
    case T.Leaf: return 0
    case T.Node(l, _, r): return 1 + max(depth(l), depth(r))

print(size(t), depth(t))
assert size(t) == curry.eval(T.size(t)).one()

# A tree built in Python is a term of Curry; Curry reads it as a value.
u = T.Node(T.Leaf, 7, T.Node(T.Leaf, 9, T.Leaf))
print(u, curry.eval(T.toList(u)).one(), curry.eval(T.member(9, u)).one())

# The class of the type, and the class of a constructor.
Tree = curry.info(T).types['Tree']
print(type(t).__name__, isinstance(t, Tree.cls), [c.name for c in Tree.constructors])

# Generation: every shape with three nodes, then one pseudo-random tree.
shapes = list(curry.eval(T.shapes(3)))
print(len(shapes))
for s in shapes:
  print(' ', s)
r = curry.eval(T.randomTree(42, 7)).one()
print(r)
print(curry.eval(T.toList(r)).one(), depth(r))
