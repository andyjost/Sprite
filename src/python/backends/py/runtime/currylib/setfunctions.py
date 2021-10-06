from .....common import T_SETGRD, T_CHOICE, LEFT, RIGHT
from ..control import E_UNWIND
from copy import deepcopy, copy
from .. import fairscheme, graph
from ..... import icurry, inspect
import logging

logger = logging.getLogger(__name__)

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

def setN(rts, _0):
  # setN :: (a1 -> ... -> aN -> b) -> a1 -> ... -> aN -> Values b
  if rts.setfunction_strategy in ['sprite', 'kics2']:
    return prim_setN(rts, _0)
  elif rts.setfunction_strategy == 'pakcs':
    # E.g., set2 f a b -> (((prim_set2 f) $## a) $## b)
    n = (len(_0.successors) - 1)
    symbols = getattr(rts.setfunctions, '.symbols')
    prim_setN_symbol = symbols['prim_set%s' % n]
    if n == 0:
      rv = graph.utility.curry(
          rts, prim_setN_symbol, *_0.successors, fapply='apply'
        )
    else:
      rv = graph.utility.curry(
          rts, prim_setN_symbol, *_0.successors, fapply='$##'
        )
    return graph.utility.shallow_copy(rv)

def prim_setN(rts, _0, guard=lambda _,arg: arg):
  n = (len(_0.successors) - 1)
  sid = rts.create_setfunction()
  if rts.setfunction_strategy == 'sprite':
    if n == 0:
      logger.warn('set0 is amgibuous with strategy %r', 'sprite')
      logger.warn(
          'instead of %r consider %r', 'set0 f', r'set1 (\() -> f) ()'
        )
      args = _0.successors
    else:
      _1 = rts.variable(_0, 0)
      _1.hnf()
      _SetGuard = rts.setfunctions._SetGuard
      args = (graph.Node(_SetGuard, sid, arg) for arg in _0.successors)
  elif rts.setfunction_strategy == 'kics2':
    if n == 0:
      args = _0.successors
    else:
      _SetGuard = rts.setfunctions._SetGuard
      args = (graph.Node(_SetGuard, sid, arg) for arg in _0.successors)
  elif rts.setfunction_strategy == 'pakcs':
    args = _0.successors
  goal = reduce(lambda a, b: graph.Node(rts.prelude.apply, a, b), args)
    
  with rts.queue_scope(sid=sid, trace=False):
    rts.set_goal(goal)
    yield rts.setfunctions.Values
    yield graph.Node(
        rts.setfunctions.allValues
      , graph.Node(rts.setfunctions.SetEval, sid, rts.qid)
      )

# def applyS(rts, _0):
#   # applyS :: (a -> b) -> a -> Values b
#   applyS (applyS (+) 1) 2

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
  , _F('prim_set0', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set1', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set2', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set3', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set4', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set5', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set6', 1, metadata={'py.rawfunc': prim_setN})
  , _F('prim_set7', 1, metadata={'py.rawfunc': prim_setN})
  , _F('allValues', 1, metadata={'py.rawfunc': allValues})
  ]

SetFunctions = icurry.IModule(
    fullname='Control.SetFunctions', imports=[], types=_types_, functions=_functions_
  )
