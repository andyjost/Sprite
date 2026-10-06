from ....common import T_CHOICE, T_FREE, LEFT, UNDETERMINED
from ..eval import fairscheme
from ...generic.currylib import setfunctions as generic_setfunctions
from ...generic.eval.control import E_UNWIND
from .. import graph
from .... import inspect

NO_SID = -1            # an undetermined set ID.
ENCAPSULATED_EXPR = -1 # indicates a partialS is an encapsulated expression.

# The number of nodes _holds_private_state visits before it gives up.  The
# C++ runtime has the same bound (currylib/setfunctions.cpp).
PRIVATE_WALK_BUDGET = 64

def allValues(rts, _0):
  # allValues a :: SetEval sid qid -> [a]
  seteval = rts.variable(_0, 0)
  seteval.hnf()
  sid, qid = seteval.successors
  try:
    with rts.queue_scope(sid=sid, qid=qid):
      try:
        value = next(fairscheme.D(rts))
        yield rts.prelude.Cons
        yield value
        yield graph.Node(rts.setfunctions.allValues, seteval)
      except StopIteration:
        yield rts.prelude.Nil
  except E_UNWIND:
    # The choice at the root of the front configuration escapes the set
    # function (rule SF.1), whatever this configuration decided: nothing of
    # the configuration that runs the capsule goes into the capsule.  The
    # queue splits on the choice (split_queue): the configurations that
    # made it LEFT stay, those that made it RIGHT move to a new queue, and
    # one that has not made it is in both, which record the choice.  The
    # redex becomes the choice between the two capsules, a node of the
    # shared graph like any pull-tabbed choice: a configuration that has not
    # decided the choice forks on it, and one that decided it prunes it.  So
    # two configurations that share the capsule, with different decisions,
    # each get their side (issue #61).  The C++ runtime has the same step
    # (allValues_step).
    subconfig = rts.qtable[qid][0]
    assert inspect.tag_of(subconfig.root) == T_CHOICE
    cid = rts.obj_id(config=subconfig)
    rhs_qid = rts.split_queue(qid, cid)
    rhs_seteval = graph.Node(seteval.info, sid, rhs_qid)
    lhs_view = graph.Node(rts.setfunctions.allValues, seteval)
    rhs_view = graph.Node(rts.setfunctions.allValues, rhs_seteval)
    lr = rts.read_fp(cid)
    if lr == UNDETERMINED or not rts.owns_decision(cid):
      # The choice is undecided here, or an enclosing configuration alone
      # decided it (read_fp walks the queue stack).  In the second case this
      # configuration may be in a capsule that enclosing configurations with
      # different decisions share, so it takes no side: the choice node
      # reaches its root and escapes in turn (choice_escapes), up to the
      # configuration that decided it.
      yield rts.Choice
      yield cid
      yield lhs_view
      yield rhs_view
    else:
      # This configuration owns the decision (owns_decision): it made the
      # choice, or its queue is bound to the side.  It takes its side at
      # once, through a private copy of the spine, as a binding goes into
      # the expression (hnf); E_RESTART tells the enclosing steps that the
      # root was replaced.  The fork would prune the choice node to the same
      # side, but it sends the configuration to the back of its queue, and a
      # search with many alternatives then advances them in lockstep, with
      # every capsule alive at once.  The redex is rewritten here, because
      # the restart leaves the generator before the caller does it.
      graph.Node(rts.Choice, cid, lhs_view, rhs_view, target=_0)
      rts.E = graph.utility.copy_spine(
          rts.E, rts.C.realpath, end=lhs_view if lr == LEFT else rhs_view
        )
      rts.restart()

def applyS(rts, _0, capture=False):
  # applyS :: PartialS (a -> b) -> a -> PartialS b
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  missing, term = partapplic.target.successors
  assert inspect.isa_unboxed_int(missing)
  assert inspect.isa_func(term) or inspect.isa_ctor(term)
  arg = _0.target.successors[1]
  assert missing >= 1
  if not capture:
    arg = graph.Node(rts.SetGuard, NO_SID, arg)
  yield rts.setfunctions.PartialS
  yield missing - 1
  yield graph.Node(
      term
    , *(term.successors + [arg])
    , partial=(missing != 1)
    )

def captureS(rts, _0):
  # captureS :: PartialS (a -> b) -> a -> PartialS b
  return applyS(rts, _0, capture=True)

def _holds_private_state(rts, root):
  '''
  Tells whether the current configuration holds private state for the
  expression at ``root``: for a free variable of it, a binding, a narrowing
  (the fingerprint, read through the queue stack), or a group with another
  variable; for a choice of it, a decision.  That is the state the evaluator
  puts into the expression through a private copy of the spine (the T_FREE
  cases of N and hnf in fairscheme.py), and the state a fork of the nested
  evaluation reads through the queue stack (rts_fingerprint.fork).  The walk
  follows forward nodes and every node successor, so it crosses set guards,
  partial applications, data, and the alternatives of an undecided choice.
  It does not enter the generator of a free variable: the variable itself is
  the test, and nothing below its generator is decided while the variable is
  not.  It stops after PRIVATE_WALK_BUDGET nodes with the conservative
  answer: a long argument counts as private.  So does a cyclic one.

  When the outermost queue holds one configuration, no other configuration
  reads the shared graph, and a later clone of this one starts with the
  same state, so the answer is False without a walk: a deterministic program
  never pays the walk and never loses the sharing of an application to the
  bound.  Inside a set function the state read through the queue stack
  depends on the enclosing configuration that runs the nested queue, so the
  walk runs there.
  '''
  if not rts.in_recursive_call and len(rts.Q) == 1:
    return False
  Node = graph.Node
  stack = [root]
  budget = PRIVATE_WALK_BUDGET
  while stack:
    node = stack.pop()
    if not isinstance(node, Node):
      continue
    if budget == 0:
      return True
    budget -= 1
    tag = node.info.tag
    if tag == T_FREE:
      vid = node.successors[0]
      gid = rts.grp_id(vid)
      if vid != gid or rts.has_binding(gid) or rts.is_narrowed(gid):
        return True
      continue
    if tag == T_CHOICE and rts.read_fp(node.successors[0]) != UNDETERMINED:
      return True
    stack.extend(node.successors)
  return False

def evalS(rts, _0):
  # evalS :: PartialS a -> Values a
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  missing, term = partapplic.target.successors
  sid = rts.create_setfunction()
  if missing == ENCAPSULATED_EXPR:
    goal = term
  else:
    assert missing == 0
    goal = graph.Node(
        term.info
      , *[graph.Node(rts.SetGuard, sid, inspect.get_setguard_value(t))
             if inspect.info_of(t) is rts.SetGuard and inspect.get_set_id(t) == NO_SID
             else t
                 for t in term.successors
           ]
      )
  qid = rts.create_queue(sid, goal)
  allvalues = graph.Node(
      rts.setfunctions.allValues
    , graph.Node(rts.setfunctions.SetEval, sid, qid)
    )
  # The nested evaluation reads the state of this configuration for the free
  # variables and the choices of its goal (the fingerprint, through the queue
  # stack), so its values depend on that state when this configuration
  # bound, narrowed, or grouped such a variable, or decided such a choice.  A
  # result that depends on the private state of a configuration never goes
  # into the shared graph, where another configuration, with another binding
  # of the variable or another side of the choice, would read it (issue
  # #61).  It goes into a private copy of the spine, as the binding itself
  # does (hnf), and the shared node stays an application for the other
  # configurations.  E_RESTART tells the enclosing steps that the root was
  # replaced.  The copy is taken for the state the goal captures outside
  # its guards (set1 (constT x) 0); the escape would handle such a choice
  # too (choice_escapes), at the cost of a split per choice.  A choice or a
  # variable under a guard escapes the capsule or is resolved by each reader
  # of the value (see allValues), so the copy only loses the sharing there.
  # The C++ runtime has the same rule (evalS_step).
  if _holds_private_state(rts, term):
    replacement = graph.Node(rts.setfunctions.Values, allvalues)
    rts.E = graph.utility.copy_spine(rts.E, rts.C.realpath, end=replacement)
    rts.restart()
  yield rts.setfunctions.Values
  yield allvalues

def exprS(rts, _0):
  yield rts.setfunctions.PartialS
  yield ENCAPSULATED_EXPR
  yield _0.successors[0]

def set_(rts, _0):
  # set :: a -> PartialS a
  _1 = rts.variable(_0, 0)
  _1.hnf()
  assert _1.info is rts.PartApplic
  yield rts.setfunctions.PartialS
  yield _1.successors[0]
  yield _1.successors[1]

def setN(rts, _0):
  # setN :: (a1 -> ... -> aN -> b) -> a1 -> ... -> aN -> Values b
  n = len(_0.successors) - 1
  pure = getattr(rts.setfunctions, 'exprS' if n == 0 else 'set')
  setf = graph.Node(pure, _0.successors[0])
  fapply = getattr(
      rts.setfunctions
    , '$##>' if rts.setfunction_strategy == 'eager' else '$>'
    )
  yield rts.setfunctions.evalS
  yield graph.utility.curry(rts, setf, *_0.successors[1:], fapply=fapply)

FUNCTION_METADATA = {
    'allValues': {'py.rawfunc': allValues}
  , 'applyS'   : {'py.rawfunc': applyS}
  , 'captureS' : {'py.rawfunc': captureS}
  , 'evalS'    : {'py.rawfunc': evalS}
  , 'exprS'    : {'py.rawfunc': exprS}
  , 'set'      : {'py.rawfunc': set_}
  , 'set0'     : {'py.rawfunc': setN}
  , 'set1'     : {'py.rawfunc': setN}
  , 'set2'     : {'py.rawfunc': setN}
  , 'set3'     : {'py.rawfunc': setN}
  , 'set4'     : {'py.rawfunc': setN}
  , 'set5'     : {'py.rawfunc': setN}
  , 'set6'     : {'py.rawfunc': setN}
  , 'set7'     : {'py.rawfunc': setN}
  }

class SetFunctionsSpecification(generic_setfunctions.SetFunctionsSpecification):
  FUNCTION_METADATA = FUNCTION_METADATA

