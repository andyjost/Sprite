from .....common import T_SETGRD, T_CHOICE, LEFT, RIGHT
from ..control import E_UNWIND
from copy import deepcopy, copy
from .. import fairscheme, graph
from ..... import icurry, inspect


def exports():
  yield '_SetGuard'
  yield 'SetEval'

def aliases():
  return []

def _T(name, constructors):
  return icurry.IDataType('Control.SetFunctions.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Control.SetFunctions.' + name, *args, **kwds)

_types_ = [
    _T('SetEval'   , [_C('SetEval', 2)])
  , _T('_SetGuard', [_C('_SetGuard', 2, metadata={'all.tag':T_SETGRD})])
  ]

def _F(name, *args, **kwds):
  return icurry.IFunction('Control.SetFunctions.' + name, *args, **kwds)

def create_guarded_expr(rts, arg):
  return arg if not hasattr(arg, 'info') else \
         graph.Node(rts.setfunctions._SetGuard, rts.sid, arg)

def make_subgoal(rts, f, *args):
  expr = create_guarded_expr(rts, f)
  for arg in args:
    expr = graph.Node(rts.prelude.apply, expr, create_guarded_expr(rts, arg))
  return expr

def setN(rts, _0):
  # setN :: (a1 -> ... -> aN -> b) -> a1 -> ... -> aN -> Values b
  sid = rts.create_setfunction()
  with rts.queue_scope(sid=sid, trace=False):
    goal = make_subgoal(rts, *_0.successors)
    rts.set_goal(goal)
    yield rts.setfunctions.Values
    yield graph.Node(
        rts.setfunctions.allValues
      , graph.Node(rts.setfunctions.SetEval, sid, rts.qid)
      )

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
    subconfig = rts.qtable[qid][0]
    assert inspect.tag_of(subconfig.root) == T_CHOICE
    cid = rts.obj_id(config=subconfig)
    with rts.queue_scope(sid=sid):
      rts.Q = copy(rts.qtable[qid])
      assert rts.qid != qid
      rhs_seteval = graph.Node(seteval.info, sid, rts.qid)
    yield rts.prelude._Choice
    yield cid
    yield graph.Node(rts.setfunctions.allValues, seteval)
    yield graph.Node(rts.setfunctions.allValues, rhs_seteval)

_functions_ = [
    _F('set0', 1, metadata={'py.rawfunc': setN})
  , _F('set1', 1, metadata={'py.rawfunc': setN})
  , _F('set2', 1, metadata={'py.rawfunc': setN})
  , _F('set3', 1, metadata={'py.rawfunc': setN})
  , _F('set4', 1, metadata={'py.rawfunc': setN})
  , _F('set5', 1, metadata={'py.rawfunc': setN})
  , _F('set6', 1, metadata={'py.rawfunc': setN})
  , _F('set7', 1, metadata={'py.rawfunc': setN})
  , _F('allValues', 1, metadata={'py.rawfunc': allValues})
  ]

SetFunctions = icurry.IModule(
    fullname='Control.SetFunctions', imports=[], types=_types_, functions=_functions_
  )
