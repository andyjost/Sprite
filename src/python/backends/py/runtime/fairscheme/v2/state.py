from copy import copy
from .. import freevars
from ... import graph
from .. import stepcounter
from ....sprite import Fingerprint, LEFT, RIGHT, UNDETERMINED, ChoiceState
from ......tags import *
from ......utility import exprutil
from ......utility import unionfind
from ......utility import shared
from ......utility.shared import compose, Shared
import collections
import itertools

class DefaultDict(shared.DefaultDict):
  def __repr__(self):
    return '{%s}' % ','.join('%s:%s' % (k,v) for k,v in self.iteritems())

Bindings = lambda: Shared(dict)

class Configuration(object):
  def __init__(self, root, fingerprint=None, strict_constraints=None, bindings=None):
    self.root = root
    self.fingerprint = Fingerprint() if fingerprint is None else fingerprint
    self.strict_constraints = Shared(unionfind.UnionFind) \
        if strict_constraints is None else strict_constraints
    self.bindings = Bindings() if bindings is None else bindings

  def __copy__(self):
    return self.clone(self.root)

  def clone(self, root):
    return Configuration(
        root, copy(self.fingerprint), copy(self.strict_constraints)
      , copy(self.bindings)
      )

  def __repr__(self):
    return '{{fp=%s, cst=%s, bnd=%s}}' % (
        self.fingerprint, self.strict_constraints.read, self.bindings
      )

Queue = collections.deque

class InterpreterState(object):
  '''
  The part of the runtime system state that belongs to the interpreter.  Each
  interpreter keeps its own ID factory.  Storing this with the interpreter is
  necessary to ensure that all expressions built by the interpreter are
  compatible.
  '''
  def __init__(self, interp):
    self.idfactory = itertools.count()

class RuntimeState(object):
  '''
  The state of the runtime system during evaluation.  Each time a goal is
  activated an object of this type is created.

  Attributes:
  -----------
      ``C``
          The active configuration.  Equivalent to queue[0].
      ``E``
          The active expression.  Equivalent to queu[0].root.
      ``queue``
          The Fair Scheme work queue.  A sequence of Configurations comprising
          a set of disjoint paths through the non-deterministic solution
          space.
  '''
  def __init__(self, interp, goal=None):
    # Capture the interpreter state.  This includes mutable objects, such as
    # the standard file streams; system lbraries, such as the Prelude; and
    # functions that might be required by built-ins, such as the ``expr``,
    # ``type``, and ``unbox`` functions.
    self.currypath = tuple(interp.path)
    self.expr = interp.expr
    self.integer = interp.integer
    self.prelude = interp.prelude
    self.stdin = interp.stdin
    self.stdout = interp.stdout
    self.topython = interp.topython
    self.tracing = interp.flags['trace']
    self.algebraic_substitution = interp.flags['algebraic_substitution']
    self.type = interp.type
    self.unbox = interp.unbox

    # State unique to this evaluation.
    self.idfactory = interp.context.runtime.get_interpreter_state(interp).idfactory
    self.stepcounter = stepcounter.StepCounter()

    # The Fair Scheme work queue.
    self.queue = Queue([])
    self.set_goal(goal)

    # The free variable table.
    self.vtable = {}

    # The trace object.
    from ... import trace
    self.trace = trace.Trace(self)

  def set_goal(self, goal):
    assert not self.queue
    if goal is not None:
      self.queue.append(Configuration(goal))

  @property
  def C(self):
    '''The current configuration.'''
    return self.queue[0]

  @property
  def E(self):
    '''The current root expression.'''
    return self.C.root

  @E.setter
  def E(self, node):
    self.C.root = node

  def real_id(self, arg=None, config=None):
    '''
    Returns the ID as it appears in a node.  The node argument must be a choice
    or free variable node, or ID.
    '''
    arg = (config or self.C).root if arg is None else arg
    if isinstance(arg, int):
      return arg
    else:
      if arg.info.tag == T_CHOICE:
        cid, _, _ = arg
        return cid
      elif arg.info.tag == T_FREE:
        vid, _ = arg
        return vid

  def eff_id(self, arg=None, config=None):
    '''
    Returns the effective ID.  The argument must be a choice or variable node,
    or ID.

    From each group of free variables constrained equal with (=:=), one
    representative is chosen to identify the group.  The effective ID is the ID
    of that variable.
    '''
    config = config or self.C
    return config.strict_constraints.read.root(self.real_id(arg))

  def read_fp(self, arg=None, config=None):
    '''
    Read the fingerprint for the given argument, which must be a choice or
    variable node, ID, or ChoiceState.
    '''
    if isinstance(arg, ChoiceState):
      return arg
    else:
      config = config or self.C
      return config.fingerprint[self.eff_id(arg, config=config)]

  def _leftright(self, idx, choicestate, config=None):
    '''Implements methods ``left`` and ``right.``'''
    config = config or self.C
    clone = config.clone(config.root[idx])
    if self.update_fp(choicestate, config.root, config=clone):
      if self.real_id() in self.vtable:
        i = self.real_id()
        j = self.eff_id(i, config=clone)
        if not self.constrain_equal(*map(self.freevar, [i,j]), config=clone):
          return None
        # if self.has_binding(i, config=clone):
        #   clone.root = graph.Node(
        #       getattr(self.prelude, '&>')
        #     , graph.Node(
        #           self.prelude.prim_nonstrictEq
        #         , self.generator(i, config=clone)
        #         , self.pop_binding(i, config=clone)
        #         )
        #     , clone.root
        #     )
      return clone
    return None

  def left(self, config=None):
    '''
    Returns a new configuration representing the left alternative at the root,
    if it would be consistent, otherwise None.
    '''
    return self._leftright(1, LEFT, config)

  def right(self, config=None):
    '''
    Returns a new configuration representing the left alternative at the root,
    if it would be consistent, otherwise None.
    '''
    return self._leftright(2, RIGHT, config)
    # config = config or self.C
    # clone = config.clone(config.root[2])
    # return clone if self.update_fp(RIGHT, config.root, config=clone) else None

  def is_narrowed(self, arg=None, config=None):
    '''
    Indicates whether the given free varaible was narrowed in this
    configuration.  The argument must be a free variable node or ID.
    '''
    return self.read_fp(arg, config=config) != UNDETERMINED

  def drop(self):
    '''Drop the current configuration.'''
    self.queue.popleft()

  def register_freevar(self, var):
    '''
    Update the vtable for variable ``var``.  The variable is added to the
    table so that it can be found later, if needed.
    '''
    self.vtable[self.real_id(var)] = var

  def freevar(self, arg=None):
    vid = self.real_id(arg)
    return self.vtable[vid]

  def is_choice_or_freevar_node(self, node):
    '''Indicates whether the given argument is a choice or free variable.'''
    try:
      return node.info.tag in [T_CHOICE, T_FREE]
    except AttributeError:
      return False

  def is_freevar_node(self, node):
    '''Indicates whether the given argument is a free variable.'''
    try:
      return node.info.tag == T_FREE
    except AttributeError:
      return False

  def generator(self, arg=None, config=None):
    '''
    Returns the generator for the given free variable. The first argument must
    be a choice or free variable node, or ID.
    '''
    vid = self.real_id(arg)
    x = self.freevar(vid)
    if not freevars.has_generator(self, x):
      self.constrain_equal(x, self.freevar(self.eff_id(vid, config)))
      assert freevars.has_generator(self, x)
    _, gen = x
    return gen

  def instantiate(self, func, path, typedef, config=None):
    config = config or self.C
    gen = freevars.instantiate(self, func, path, typedef)
    return gen

  def constrain_equal(self, arg0, arg1, strict=True, config=None):
    '''
    Constrain the given arguments to be equal in the specified context.  This
    implements the equational constraint, (=:=).  Both arguments must be
    choices or both free variables, and, in the latter case, the free variables
    must represent values of the same type.

    The return value indicates whether the constaint is consistent.

    Recursive constraints arise from interleaving the rules of (=:=) with
    narrowing steps.  Suppose x =:= y is first evaluated, then x and y are
    subsequently narrowed to (x0:x1) and (y0:y1), resp.  The recursive
    constraints over subariabls, x0 =:= y0 and x1 =:= y1, must then be
    evaluated.

    When this function is called, either at least one of the two variables has
    been narrowed, or neither has.  In the first case,
    ``constrain_equal_rec`` is called to constrain the subvariables
    right away.  The narrowed variable is guaranteed to be instantiated, and so
    can serve as a template to instantiate the other, if necessary.  Otherwise,
    it is necessary to wait until one of the variables is narrowed before
    evaluating recursive constraints.

    Parameters:
    -----------
      ``arg0``, ``arg1``
          The arguments to constrain.  Each must be a choice or free variable node,
          or ID. The associated IDs must correspond to free variables in the
          ``vtable``.

       ``config``
          The configuration to use as context.
    '''
    config = config or self.C
    i, j = map(self.real_id, [arg0, arg1])
    self.apply_binding(i, config=config)
    self.apply_binding(j, config=config)
    if i != j:
      if strict:
        if not self.equate_fp(i, j, config=config):
          return False
        config.strict_constraints.write.unite(i, j)
        if any(map(self.is_freevar_node, [arg0, arg1])):
          if not self.constrain_equal_rec(i, j, config=config):
            return False
      elif not self.add_binding(i, arg1, config=config):
        return False
    return True

  def constrain_equal_rec(self, arg0, arg1, config=None):
    '''
    Implements the recursive part of ``constrain_equal.``  Given two arguments,
    if at least one has been narrowed, ensure both are instantiated and then
    constrain the subvariables to be equal.  The arguments must all be free
    variables (or arguments convertible to free variables) of the same type.

    Example:
    --------
    1. Suppose the arguments are free variables x and y.  x has been narrowed
    to a non-empty list, (x0:x1), and so xR is in the fingerprint.  y is
    uninstantiated.  This function would instantiate y, giving it the generator
    "[] ?_y (y0:y1)", update the fingerprint with yR, and evaluate the
    equational constraints x0 =:= y0 and x1 =:= y1.
    
    If all these operations succeed in the sense that none invalidate the
    fingerprint, then True is returned.

    2. Now suppose neither free variable was narrowed.  This function does
    nothing and returns True.

    Parameters:
    -----------
      ``arg0``, ``arg1``
          The arguments to check.  Each must be a choice or free variable node,
          or ID. If any associated ID does not correspond to a free variable in
          the ``vtable`` then this function does nothing.  At least one of the
          variables must have been narrowed in the given configuration.

       ``config``
          The configuration to use as context.

    Returns:
    --------
    A Boolean indicating whether the new constraints succeeded (i.e., could be
    consistent).
    '''
    try:
      xs = map(self.freevar, [arg0, arg1])
    except KeyError:
      return True
    else:
      config = config or self.C # maybe don't need this
      try:
        pivot = next(
            x for x in xs if self.is_narrowed(x, config=config)
                          and freevars.has_generator(self, x)
          )
      except StopIteration:
        return True
      else:
        assert not self.has_binding(pivot) # not certain about this
        u = self.generator(pivot, config=config)
        for x in xs:
          if x is not pivot:
            if not freevars.has_generator(self, x):
              freevars.clone_generator(self, pivot, x)
            assert not self.has_binding(x) # not certain about this
            v = self.generator(x, config=config)
            for p, q in itertools.izip(*[exprutil.walk(uv) for uv in [u,v]]):
              if self.is_choice_or_freevar_node(p.cursor):
                if not self.constrain_equal(p.cursor, q.cursor, config=config):
                  return False
              if not self.is_freevar_node(p.cursor):
                p.push()
                q.push()
        return True

  def equate_fp(self, arg0, arg1, config=None):
    '''
    Equate two IDs in a fingerprint.  Set both to the same value and return
    True, if that is consistent, or return False otherwise.
    '''
    return self.update_fp(arg0, arg1, config=config) \
       and self.update_fp(arg1, arg0, config=config)

  def update_fp(self, choicestate, arg=None, config=None):
    '''
    Update the fingerprint to reflect the ID associated with ``arg``` being
    set to ``choicestate.``

    If ``choicestate`` is ``UNDETERMINED``, this does nothing.  Otherwise, the
    current value of ``arg`` is determined, consulting the fingerprint, if
    necessary.  If it is consistent with ``choicestate`` then it is updated and
    True is returned.  Otherwise, False is returned.

    Parameters:
    -----------
        ``choicestate``
            The choice state to set.  Must be a ChoiceState, choice or free
            variable node, or ID.
        ``arg``
            The ID to update in the fingerprint.  Must be a choice or free variable node,
            or ID.
        ``config``
            The Configuration to use as context.

    Returns:
    --------
    A Boolean indicating whether the change is consistent.
    '''
    config = config or self.C
    choicestate = self.read_fp(choicestate, config=config)
    if choicestate == UNDETERMINED:
      return True
    current = self.read_fp(arg, config=config)
    if current == UNDETERMINED:
      config.fingerprint = copy(config.fingerprint)
      config.fingerprint[self.real_id(arg)] = choicestate
      config.fingerprint[self.eff_id(arg, config=config)] = choicestate
      return True
    else:
      return current == choicestate

  def is_strict_binding(self, arg=None, config=None):
    '''
    Indicates whether the given argument is a strict binding.  It must be a
    binding of some kind.
    '''
    arg = (config or self.C).root if arg is None else arg
    assert arg.info.tag == T_BIND
    return arg.info is self.prelude._StrictBinding.info

  def add_binding(self, vid, node, config=None):
    '''
    Create a binding from the given variable ID to ``node`` in the given
    context.  Returns a Boolean indicating whether the binding succeeded.  If
    the variable is already bound to a different node, then this fails.

    '''
    config = config or self.C
    node = graph.Node.getitem(node)
    if vid in config.bindings:
      return config.bindings.read[vid] is node
    else:
      config.bindings.write[vid] = node
      return True

  def has_binding(self, arg=None, config=None):
    config = config or self.C
    return self.real_id(arg, config) in config.bindings
    
  def pop_binding(self, arg=None, config=None):
    config = config or self.C
    vid = self.real_id(arg, config)
    return config.bindings.write.pop(vid)

  def apply_binding(self, i, config=None):
    config = config or self.C
    if self.has_binding(i, config=config):
      config.root = graph.Node(
          getattr(self.prelude, '&>')
        , graph.Node(
              self.prelude.prim_nonstrictEq
            , self.generator(i, config=config)
            , self.pop_binding(i, config=config)
            )
        , config.root
        )
    
