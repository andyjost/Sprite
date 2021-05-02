'''
Code for free variable instantiation, including generator construction.
'''

from ..graph import Node, Replacer
from ..misc import *
from ..... import runtime

__all__ = [
    'clone_generator'
  , 'get_generator'
  , 'instantiate'
  ]

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
    if gen.info.tag == runtime.T_CHOICE:
      queue.extend([gen[2], gen[1]])
    else:
      if gen.info.tag >= runtime.T_CTOR:
        yield gen.info
      else:
        # For types with one constructor, the generator is a choice between
        # that constructor and a failure.
        assert gen.info.tag == runtime.T_FAIL

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
      A ``CurryDataType`` that indicates the type to instantiate the variable
      to.  This can also be a list of ``icurry.IConstructor``s or
      ``InfoTables``.  If the free variable has already been instantiated, then
      this can be None.
  '''
  assert freevar.info.tag == runtime.T_FREE
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
  assert replacer.target.info.tag == runtime.T_FREE
  assert context.info == replaced.info
  context.successors[:] = replaced.successors
  return replacer.target[1]

