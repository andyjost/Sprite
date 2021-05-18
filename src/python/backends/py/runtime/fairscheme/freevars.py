'''
Code for free variable instantiation, including generator construction.
'''

from ..graph import Node, Replacer
from .....tags import *

__all__ = [
    'clone_generator'
  , 'freshvar'
  , 'freshvar_args'
  , 'get_generator'
  , 'get_id'
  , 'has_generator'
  , 'instantiate'
  ]

def _createGenerator(rts, ctors, vid=None, target=None):
  '''
  Creates a generator tree.

  Parameters:
  -----------
    ``rts``
      The RuntimeState object.

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
      , *[Node(rts.prelude.prim_unknown) for _ in xrange(ctor.arity)]
      , target=target
      )
  else:
    middle = -(-N // 2) # ceiling-divide, e.g., 7 -> 4.
    return Node(
        rts.prelude._Choice
      , vid if vid is not None else next(rts.idfactory)
      , _createGenerator(rts, ctors[:middle])
      , _createGenerator(rts, ctors[middle:])
      , target=target
      )

def _gen_ctors(rts, gen):
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

def clone_generator(rts, bound, unbound):
  vid = unbound[0]
  constructors = list(_gen_ctors(rts, bound[1]))
  get_generator(rts, unbound, typedef=constructors)

def get_generator(rts, freevar, typedef):
  '''
  Get the generator for a free variable.  Instantiates the variable if
  necessary.

  Parameters:
  -----------
  ``rts``
      The RuntimeState object.

  ``freevar``
      The free variable node to instantiate.

  ``typedef``
      A ``CurryDataType`` that indicates the type to instantiate the variable
      to.  This can also be a list of ``icurry.IConstructor``s or
      ``InfoTables``.  If the free variable has already been instantiated, then
      this can be None.
  '''
  assert freevar.info.tag == T_FREE
  vid = freevar[0]
  if freevar[1].info is rts.prelude.Unit.info:
    constructors = [
        getattr(ctor, 'info', ctor)
            for ctor in getattr(typedef, 'constructors', typedef)
      ]
    instance = _createGenerator(rts, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere
      # (e.g., see Replacer._a_).
      instance = Node(
          rts.prelude._Choice, vid, instance, Node(rts.prelude._Failure)
        )
    Node(freevar.info, vid, instance, target=freevar)
  return freevar[1]

def instantiate(rts, context, path, typedef):
  '''
  Instantiates a free variable at ``context[path]``.

  Parameters:
  -----------
    ``rts``
      The RuntimeState object.

    ``context``
      The context in which the free variable appears.

    ``path``
      A sequence of integers giving the path in ``context`` to the free
      variable.
  '''
  replacer = Replacer(context, path
    , lambda node, _: get_generator(rts, node, typedef)
    )
  replaced = replacer[None]
  assert replacer.target.info.tag == T_FREE
  assert context.info == replaced.info
  context.successors[:] = replaced.successors
  return replacer.target[1]

def freshvar_args(rts):
  '''
  Generates arguments for a fresh free variable using the next available ID.
  '''
  yield rts.prelude._Free.info
  yield next(rts.idfactory)
  yield Node(rts.prelude.Unit.info)

def freshvar(rts, target=None):
  '''Places a fresh free variable at the specified location.'''
  return Node(*freshvar_args(rts), target=target)

def get_id(arg):
  '''Returns the choice or variable id for a choice or free variable.'''
  if isinstance(arg, Node):
    arg = arg[()]
    if arg.info.tag in [T_FREE, T_CHOICE]:
      cid = arg[0]
      assert cid >= 0
      return cid

def has_generator(rts, freevar):
  '''Indicates whether a free variable has a bound generator.'''
  assert freevar.info.tag == T_FREE
  return freevar[1].info is not rts.prelude.Unit.info

