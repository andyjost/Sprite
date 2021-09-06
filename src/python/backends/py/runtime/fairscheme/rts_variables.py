'''
Implements RuntimeState methods related to free variables.  This module is not
intended to be imported except by state.py.
'''

from .....common import (
    LEFT, RIGHT, UNDETERMINED, ChoiceState
  , T_FAIL, T_VAR, T_CHOICE, T_CTOR
  )
from ..graph import replacer
from .. import graph
from ..... import inspect

__all__ = [
    'clone_generator', 'freshvar_args', 'freshvar', 'get_generator'
  , 'get_variable', 'has_generator', 'instantiate', 'is_free', 'is_nondet'
  , 'is_variable', 'is_narrowed', 'register_variable'
  ]

def clone_generator(self, bound, unbound):
  vid = unbound[0]
  constructors = list(_gen_ctors(self, bound[1]))
  _make_generator(self, unbound, typedef=constructors)

def freshvar_args(self):
  '''
  Generates arguments for a fresh free variable using the next available ID.
  '''
  yield self.prelude._Free.info
  yield next(self.idfactory)
  yield graph.Node(self.prelude.Unit.info)

def freshvar(self, target=None):
  '''Places a fresh free variable at the specified location.'''
  node = graph.Node(*freshvar_args(self), target=target)
  try:
    self.register_variable(node)
  except AttributeError:
    pass
  return node

def get_generator(self, arg=None, config=None):
  '''
  Returns the generator for the given free variable. The first argument must
  be a choice or free variable node, or ID.
  '''
  vid = self.obj_id(arg, config)
  x = self.get_variable(vid)
  if not self.has_generator(x):
    self.constrain_equal(x, self.get_variable(self.grp_id(vid, config)))
    assert self.has_generator(x)
  _, gen = x
  return gen

def get_variable(self, arg=None, config=None):
  try:
    if arg.info.tag == T_VAR:
      return arg
  except:
    vid = self.obj_id(arg, config)
    return self.vtable[vid]

def has_generator(self, arg=None, config=None):
  variable = self.get_variable(arg, config)
  return variable.successors[1].info is not self.prelude.Unit.info

def instantiate(self, func, path, typedef, config=None):
  '''
  Instantiates a needed free variable, which occurs at ``func[path]`` and has
  type ``typedef``.  The subexpression ``func`` will be rewritten such that the
  specified occurrence is replaced.

  See algorithm.hnf for a description of the arguments.

  Returns:
  --------
    The expression the free variable was replaced with.
  '''
  if typedef is None:
    self.suspend(func.getitem_with_guards(func, path), config)
  else:
    R = replacer.Replacer(func, path
      , lambda node, _: _make_generator(self, node, typedef)
      )
    replaced = R[None]
    assert R.target.info.tag == T_VAR
    assert func.info == replaced.info
    func.successors[:] = replaced.successors
    target = R.target.successors[1]
    if R.guards:
      return graph.utility.guard(self, R.guards, target)
    else:
      return target

def is_free(self, arg=None, config=None):
  '''
  Indicates whether a free variable is missing any information that would allow
  a computation needing it to proceed.  Used to implement
  Prelude.ensureNotFree.
  '''
  return self.is_variable(arg) and not any(
      prop(arg, config) for prop in [
          self.has_generator, self.has_binding, self.is_narrowed
        ]
    )

def is_narrowed(self, arg=None, config=None):
  '''
  Indicates whether the given free varaible was narrowed in this
  configuration.  The argument must be a free variable node or ID.
  '''
  return self.read_fp(arg, config=config) != UNDETERMINED

def is_nondet(self, arg=None, config=None):
  '''
  Returns True if the argument is a choice or variable.
  '''
  arg = (config or self.C).root if arg is None else arg
  return inspect.tag_of(arg) in [T_CHOICE, T_VAR]

def is_variable(self, node):
  '''Indicates whether the given argument is a free variable.'''
  try:
    return node.info.tag == T_VAR
  except AttributeError:
    return False

def register_variable(self, var):
  '''
  Update the vtable for variable ``var``.  The variable is added to the
  table so that it can be found later, if needed.
  '''
  self.vtable[self.obj_id(var)] = var

def _create_generator(rts, ctors, vid=None, target=None):
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
    return graph.Node(
        ctor
      , *[freshvar(rts) for _ in xrange(ctor.arity)]
      , target=target
      )
  else:
    middle = -(-N // 2) # ceiling-divide, e.g., 7 -> 4.
    return graph.Node(
        rts.prelude._Choice
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

  Parameters:
  -----------
    ``rts``
      The RuntimeState object.

    ``variable``
      The variable indicating which generator to get.

    ``typedef``
      A ``CurryDataType`` that indicates the type of ``variable``.  This can
      alternatively be a list of ``icurry.IConstructor``s or ``InfoTables``.
      If the variable is not free, then this can be None.
  '''
  assert variable.info.tag == T_VAR
  vid = variable.successors[0]
  if variable.successors[1].info is rts.prelude.Unit.info:
    constructors = [
        getattr(ctor, 'info', ctor)
            for ctor in getattr(typedef, 'constructors', typedef)
      ]
    instance = _create_generator(rts, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere
      # (e.g., see Replacer._a_).
      instance = graph.Node(
          rts.prelude._Choice, vid, instance, graph.Node(rts.prelude._Failure)
        )
    graph.Node(variable.info, vid, instance, target=variable)
  return variable.successors[1]
