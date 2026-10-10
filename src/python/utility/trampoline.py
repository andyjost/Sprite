'''
A walk over a tree as a generator, run on a stack of its own.

A recursive walk over a deep tree, such as the nest of cons calls of a
literal list of thousands of elements in FlatCurry, exceeds the recursion
limit of Python (issue #125).  A walk written as a generator does not: the
generator of a node yields the generator of each subtree whose result it
needs, and returns its own result.  :func:`trampoline` runs the generators
on a list, so the depth of the tree costs no frame of the stack of Python.
The code of a walk reads as the recursive code does, with ``yield`` in
place of the recursive call::

    def size(tree):
      total = 1
      for child in tree.children:
        total += yield size(child)
      return total

    trampoline(size(tree))

A generator that returns without a yield is a leaf.  A leaf may also be a
plain value: a walk that yields something other than a generator gets that
value back at once, and :func:`trampoline` of a value is the value.  So a
walk dispatched on the type of a node may answer a leaf with its result and
an inner node with a generator (the generic compiler does).  An exception
raised in a generator propagates to the caller of :func:`trampoline`.
'''
import types

__all__ = ['trampoline']

def trampoline(walk):
  '''
  Runs the generator ``walk`` and returns its result.  Each generator it
  yields is run in turn, and the result of that generator is sent back to
  the generator that yielded it.  A value that is not a generator is a
  result.
  '''
  if not isinstance(walk, types.GeneratorType):
    return walk
  stack = [walk]
  value = None
  while stack:
    try:
      child = stack[-1].send(value)
    except StopIteration as stop:
      stack.pop()
      value = stop.value
    else:
      if isinstance(child, types.GeneratorType):
        stack.append(child)
        value = None
      else:
        value = child
  return value
