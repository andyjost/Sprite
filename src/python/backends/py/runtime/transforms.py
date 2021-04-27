from __future__ import absolute_import

from .graph import *
from .misc import *

__all__ = [
    'clone_generator'
  , 'get_generator'
  , 'instantiate'
  , 'lift_choice'
  , 'lift_constr'
  , 'replace'
  , 'replace_copy'
  , 'Replacer'
  , 'rewrite'
  ]

def rewrite(node, info, *args):
  return node.rewrite(info, *args)

class Replacer(object):
  '''
  Performs replacements in a context.

  For context C and path p, this object returns shallow copies of C in which
  the target, C[p], is replaced.  Given replacer R with getter g, the
  expression R[i] returns C[p] <- g(C[p], i).  The copy is minimal, meaning
  new nodes are allocated only along the spine.

  The default getter is just getitem, so it will return a successor of the
  target.  This is handy when the target is a choice, since R[1], R[2] will
  return a copy of the expression with the left and right alternatives,
  respectively, in place (note: the zeroth successor is the choice ID).

  A custom getter can be used to construct any replacement desired.
  '''
  def __init__(self, context, path, getter=Node.__getitem__):
    self.context = context
    self.path = path
    self.target = None # has value after first __getitem__
    self.getter = getter

  def _a_(self, node, depth=0):
    '''Recurse along the spine.  At the target, call the getter.'''
    if depth < len(self.path):
      return Node(*self._b_(node, depth))
    else:
      assert self.target is None or self.target is node
      self.target = node
      return self.getter(node, self.index)

  def _b_(self, node, depth):
    '''
    Perform a shallow copy at one node.  Recurse along the spine; reference
    subexpressions not on the spine.
    '''
    pos = self.path[depth]
    yield node.info
    for j,_ in enumerate(node.successors):
      if j == pos:
        yield self._a_(node[j], depth+1) # spine
      else:
        yield node[j] # not spine

  def __getitem__(self, i):
    self.index = i
    return self._a_(self.context)

def replace(interp, context, path, replacement):
  replacer = Replacer(context, path, lambda _a, _b: replacement)
  replaced = replacer[None]
  # assert replacer.target.info.tag == T_FREE
  # assert context.info == replaced.info
  context.successors[:] = replaced.successors

def replace_copy(interp, context, path, replacement):
  copy = context.copy()
  replace(interp, copy, path, replacement)
  return copy

def lift_choice(interp, source, path):
  '''
  Executes a pull-tab step with source ``source`` and choice-rooted target
  ``source[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``source``
      The pull-tab source.  This node will be overwritten with a choice symbol.

    ``path``
      A sequence of integers giving the path from ``source`` to the target
      choice or constraint.
  '''
  assert source.info.tag < T_CTOR
  assert path
  # if source.info is interp.prelude.ensureNotFree.info:
  #   raise RuntimeError("non-determinism in I/O actions occurred")
  replacer = Replacer(source, path)
  left = replacer[1]
  right = replacer[2]
  assert replacer.target.info.tag == T_CHOICE
  Node(
      interp.prelude._Choice
    , replacer.target[0] # choice ID
    , left
    , right
    , target=source
    )


def lift_constr(interp, source, path):
  '''
  Executes a pull-tab step with source ``source`` and constraint-rooted target
  ``source[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``source``
      The pull-tab source.  This node will be overwritten with a constraint
      symbol.

    ``path``
      A sequence of integers giving the path from ``source`` to the target
      choice or constraint.
  '''
  assert source.info.tag < T_CTOR
  assert path
  replacer = Replacer(source, path)
  value = replacer[0]
  assert replacer.target.info.tag == T_BIND
  Node(
      replacer.target.info
    , value
    , replacer.target[1] # binding
    , target=source
    )


def instantiate(interp, context, path, typedef):
  '''
  Instantiates a free variable at ``context[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``context``
      The context in which the free variable appears.

    ``path``
      A sequence of integers giving the path in ``context`` to the free
      variable.
  '''
  replacer = Replacer(context, path
    , lambda node, _: get_generator(interp, node, typedef)
    )
  replaced = replacer[None]
  assert replacer.target.info.tag == T_FREE
  assert context.info == replaced.info
  context.successors[:] = replaced.successors
  return replacer.target[1]

def _createGenerator(interp, ctors, vid=None, target=None):
  '''
  Creates a generator tree.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``ctors``
      A sequence of ``InfoTable`` objects defining the type to generate.

    ``vid``
      The variable ID.  The root choice will be labeled with this ID.  By
      default, a new ID is allocated.

    ``target``
      The node to overwrite with the generator tree.  By default, a new node
      will be allocated.
  '''
  N = len(ctors)
  assert N
  if N == 1:
    ctor, = ctors
    return Node(
        ctor
      , *[Node(interp.prelude.prim_unknown) for _ in xrange(ctor.arity)]
      , target=target
      )
  else:
    middle = -(-N // 2) # ceiling-divide, e.g., 7 -> 4.
    return Node(
        interp.prelude._Choice
      , vid if vid is not None else nextid(interp)
      , _createGenerator(interp, ctors[:middle])
      , _createGenerator(interp, ctors[middle:])
      , target=target
      )

def _gen_ctors(interp, gen):
  '''Iterate through the constructors of a generator.'''
  queue = [gen]
  while queue:
    gen = queue.pop()
    if gen.info.tag == T_CHOICE:
      queue.extend([gen[2], gen[1]])
    else:
      if gen.info.tag >= T_CTOR:
        yield gen.info
      else:
        # For types with one constructor, the generator is a choice between
        # that constructor and a failure.
        assert gen.info.tag == T_FAIL

def clone_generator(interp, bound, unbound):
  vid = unbound[0]
  constructors = list(_gen_ctors(interp, bound[1]))
  get_generator(interp, unbound, typedef=constructors)

def get_generator(interp, freevar, typedef):
  '''
  Get the generator for a free variable.  Instantiates the variable if
  necessary.

  Parameters:
  -----------
  ``interp``
      The interpreter.
  ``freevar``
      The free variable node to instantiate.
  ``typedef``
      A ``TypeDefinition`` that indicates the type to instantiate the variable
      to.  This can also be a list of ``icurry.IConstructor``s or
      ``InfoTables``.  If the free variable has already been instantiated, then
      this can be None.
  '''
  assert freevar.info.tag == T_FREE
  vid = freevar[0]
  if freevar[1].info is interp.prelude.Unit.info:
    constructors = [
        getattr(ctor, 'info', ctor)
            for ctor in getattr(typedef, 'constructors', typedef)
      ]
    instance = _createGenerator(interp, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere
      # (e.g., see Replacer._a_).
      instance = Node(
          interp.prelude._Choice, vid, instance, Node(interp.prelude._Failure)
        )
    Node(freevar.info, vid, instance, target=freevar)
  return freevar[1]

