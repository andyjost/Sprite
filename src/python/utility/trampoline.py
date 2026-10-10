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

A generator that returns without a yield is a leaf.  An exception raised in
a generator propagates to the caller of :func:`trampoline`.
'''

__all__ = ['trampoline']

def trampoline(walk):
  '''
  Runs the generator ``walk`` and returns its result.  Each generator it
  yields is run in turn, and the result of that generator is sent back to
  the generator that yielded it.
  '''
  stack = [walk]
  value = None
  while stack:
    try:
      child = stack[-1].send(value)
    except StopIteration as stop:
      stack.pop()
      value = stop.value
    else:
      stack.append(child)
      value = None
  return value
