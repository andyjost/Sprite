from .....common import T_SETGRD, T_CHOICE, LEFT, RIGHT
from ..control import E_UNWIND
from copy import deepcopy, copy
from .. import fairscheme, graph
from ..... import icurry, inspect

def exports():
  yield '_SetGuard'
  yield 'Values'

def aliases():
  return []

def _T(name, constructors):
  return icurry.IDataType('Control.SetFunctions.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Control.SetFunctions.' + name, *args, **kwds)

_types_ = [
    _T('Values'   , [_C('Values', 2)])
  , _T('_SetGuard', [_C('_SetGuard', 2, metadata={'all.tag':T_SETGRD})])
  ]

def _F(name, *args, **kwds):
  return icurry.IFunction('Control.SetFunctions.' + name, *args, **kwds)

def create_guarded_expr(rts, arg):
  return arg if not hasattr(arg, 'info') else \
         graph.Node(rts.setfunctions._SetGuard, rts.get_sid(), arg)

def make_goal(rts, f, *args):
  expr = f
  for arg in args:
    expr = graph.Node(rts.prelude.apply, expr, create_guarded_expr(rts, arg))
  return expr

def setN(rts, _0):
  sid = rts.create_setfunction()
  with rts.queue_scope(sid=sid):
    goal = make_goal(rts, *_0.successors)
    rts.set_goal(goal)
    yield rts.setfunctions.Values
    yield sid
    yield rts.qid

def allValues(rts, _0):
  valueset = rts.variable(_0, 0)
  valueset.hnf()
  valueset.update()
  sid, qid = valueset.successors
  try:
    with rts.queue_scope(sid=sid, qid=qid):
      try:
        value = next(fairscheme.D(rts))
        yield rts.prelude.Cons
        yield value
        yield graph.Node(rts.setfunctions.allValues, valueset)
      except StopIteration:
        yield rts.prelude.Nil
  except E_UNWIND:
    subconfig = rts.qtable[qid][0]
    tag = inspect.tag_of(subconfig.root)
    if tag == T_SETGRD:
      gexpr = subconfig.root
      valueset.guards.add(gexpr[0])
      for arg in graph.guard_args(rts, valueset.guards, _0.target.copy()):
        yield arg
      with rts.queue_scope(sid=sid, qid=qid):
        rts.E = rts.E[1]
    elif tag == T_CHOICE:
      cid = rts.obj_id(config=subconfig)
      with rts.queue_scope(sid=sid):
        rts.Q = copy(rts.qtable[qid])
        assert rts.qid != qid
        right_valueset = graph.Node(valueset.info, sid, rts.qid)
      yield rts.prelude._Choice
      yield cid
      yield graph.Node(rts.setfunctions.allValues, valueset)
      yield graph.Node(rts.setfunctions.allValues, right_valueset)
    else:
      assert False

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
