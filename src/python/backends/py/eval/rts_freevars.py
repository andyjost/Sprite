'''
Implements RuntimeState methods related to free variables.  This module is not
intended to be imported except by rts.py.
'''

from ....common import (
    LEFT, RIGHT, UNDETERMINED, ChoiceState, T_FAIL, T_FREE, T_CHOICE, T_CTOR
  )
from .. import graph
from .... import inspect

__all__ = [
    'clone_generator', 'freshvar_args', 'freshvar', 'get_generator'
  , 'get_freevar', 'has_generator', 'instantiate', 'is_nondet', 'is_narrowed'
  , 'is_void', 'register_freevar', 'register_freevars'
  ]

def clone_generator(rts, bound, unbound):
  constructors = list(_gen_ctors(rts, bound[1]))
  _make_generator(rts, unbound, typedef=constructors)

def freshvar_args(rts):
  '''
  Generates arguments for a fresh free variable using the next available ID.
  '''
  yield rts.Free
  yield next(rts.idfactory)
  yield graph.Node(rts.prelude.Unit.info)

def freshvar(rts, target=None):
  '''Places a fresh free variable at the specified location.'''
  node = graph.Node(*freshvar_args(rts), target=target)
  try:
    rts.register_freevar(node)
  except AttributeError:
    pass
  if rts.checker is not None:
    rts.checker.variable(node)
  return node

def get_generator(rts, arg=None, config=None):
  '''
  Returns the generator for the given free variable. The first argument must
  be a choice or free variable node, or ID.
  '''
  vid = rts.obj_id(arg, config)
  x = rts.get_freevar(vid)
  if not rts.has_generator(x):
    rts.constrain_equal(x, rts.get_freevar(rts.grp_id(vid, config)))
    assert rts.has_generator(x)
  _, gen = x.successors
  return gen

def get_freevar(rts, arg=None, config=None):
  try:
    if arg.info.tag == T_FREE:
      return arg
  except AttributeError: # arg is a variable ID, not a node
    vid = rts.obj_id(arg, config)
    return rts.vtable[vid]

def has_generator(rts, arg=None, config=None):
  variable = rts.get_freevar(arg, config)
  return variable.successors[1].info is not rts.prelude.Unit.info

def instantiate(rts, var, typedef, config=None):
  '''
  Instantiates a needed free variable, at the specified location.

  Returns:
    The expression the free variable was replaced with.
  '''
  if typedef is None:
    rts.suspend(var, config)
  else:
    var.target = _make_generator(rts, var, typedef)
    checker = rts.checker
    if checker is None:
      graph.utility.copy_spine(var.root, var.realpath, end=var.target, rewrite=var.root)
    else:
      # The reducts of the configurations that reference the redex are read
      # before the write and compared after it (X-b').
      before = checker.instantiate_begin(var)
      graph.utility.copy_spine(var.root, var.realpath, end=var.target, rewrite=var.root)
      checker.instantiate_end(var, before)
    return var.target

def is_narrowed(rts, arg=None, config=None):
  '''
  Indicates whether the given free varaible was narrowed in this
  configuration.  The argument must be a free variable node or ID.
  '''
  return rts.read_fp(arg, config=config) != UNDETERMINED

def is_nondet(rts, arg=None, config=None):
  '''
  Returns True if the argument is a choice or variable.
  '''
  arg = (config or rts.C).root if arg is None else arg
  return inspect.tag_of(arg) in [T_CHOICE, T_FREE]

def is_void(rts, arg=None, config=None):
  '''
  Indicates whether a free variable is missing any information that would allow
  a computation needing it to proceed.  Used to implement
  Prelude.ensureNotFree.
  '''
  return inspect.isa_freevar(arg) and not any(
      prop(arg, config) for prop in [
          rts.has_generator, rts.has_binding, rts.is_narrowed
        ]
    )

def register_freevar(rts, var):
  '''
  Update the vtable for variable ``var``.  The variable is added to the
  table so that it can be found later, if needed.
  '''
  rts.vtable[rts.obj_id(var)] = var

def register_freevars(rts, root):
  '''
  Registers every free variable of the expression at ``root`` in the vtable.
  A goal built outside this evaluation can hold variables that no table of
  this state knows: a ``curry.free`` marker shared with an earlier goal,
  whose node the step of ``Prelude.unknown`` forwarded to a free variable;
  the result of the single rewrite step of a compiled expression; a raw
  ``Free`` node of ``curry.raw_expr``; a value of an earlier evaluation.  The
  item of a generator node is built during the evaluation, so its step walks
  the item as well (prelude/string.py).  The walk is iterative with a
  visited set, because a goal can be cyclic.  It follows forward nodes and
  descends into every node successor: data, partial applications, set
  guards, constraints, choices, and the generators of free variables.  The
  C++ runtime has the same method.
  '''
  Node = graph.Node
  stack = [root]
  seen = set()
  while stack:
    node = stack.pop()
    if not isinstance(node, Node) or id(node) in seen:
      continue
    seen.add(id(node))
    if node.info.tag == T_FREE:
      rts.register_freevar(node)
    stack.extend(node.successors)

def _create_generator(rts, ctors, vid=None, target=None):
  '''
  Creates a generator tree.

  Args:
    rts:
      The RuntimeState object.

    ctors:
      A sequence of ``InfoTable`` objects defining the type to generate.

    vid:
      The variable ID.  The root choice will be labeled with this ID.  By
      default, a new ID is allocated.

    target:
      The node to overwrite with the generator tree.  By default, a new node
      will be allocated.
  '''
  N = len(ctors)
  assert N
  if N == 1:
    ctor, = ctors
    return graph.Node(
        ctor
      , *[freshvar(rts) for _ in range(ctor.arity)]
      , target=target
      )
  else:
    middle = -(-N // 2) # ceiling-divide, e.g., 7 -> 4.
    return graph.Node(
        rts.Choice
      , vid if vid is not None else next(rts.idfactory)
      , _create_generator(rts, ctors[:middle])
      , _create_generator(rts, ctors[middle:])
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

def _make_generator(rts, variable, typedef=None):
  '''
  Get the generator for a variable.  Instantiate it, if necessary.

  Args:
    rts:
      The RuntimeState object.

    variable:
      The variable indicating which generator to get.

    typedef:
      A ``CurryDataType`` that indicates the type of ``variable``.  This can
      alternatively be a list of ``icurry.IConstructor``s or ``InfoTables``.
      If the variable is not free, then this can be None.
  '''
  assert variable.info.tag == T_FREE
  vid = variable.successors[0]
  if variable.successors[1].info is rts.prelude.Unit.info:
    constructors = [
        getattr(ctor, 'info', ctor)
            for ctor in getattr(typedef, 'constructors', typedef)
      ]
    instance = _create_generator(rts, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere.
      instance = graph.Node(
          rts.Choice, vid, instance, graph.Node(rts.Failure)
        )
    graph.Node(variable.info, vid, instance, target=variable)
    if rts.checker is not None:
      rts.checker.generator(getattr(variable, 'target', variable), instance)
  return variable.successors[1]
