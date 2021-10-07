'''
Implements the external parts of Control.SetFunctions.
'''

from .....common import T_SETGRD, T_CHOICE, LEFT, RIGHT
from ..control import E_UNWIND
from copy import deepcopy, copy
from ..graph import infotable
from .. import fairscheme, graph
from ..... import icurry, inspect
import logging

logger = logging.getLogger(__name__)

NO_SID = -1            # an undetermined set ID.
ENCAPSULATED_EXPR = -1 # indicates a partialS is an encapsulated expression.

def exports():
  yield 'PartialS'
  yield 'SetEval'
  yield '_SetGuard'

def aliases():
  return []

def _T(name, constructors):
  return icurry.IDataType('Control.SetFunctions.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Control.SetFunctions.' + name, *args, **kwds)

_types_ = [
    _T('PartialS' , [_C('PartialS', 2, metadata={'all.flags': infotable.InfoTable.PARTIAL_TYPE})])
  , _T('SetEval'  , [_C('SetEval', 2)])
  , _T('_SetGuard', [_C('_SetGuard', 2, metadata={'all.tag':T_SETGRD})])
  ]

def _F(name, *args, **kwds):
  return icurry.IFunction('Control.SetFunctions.' + name, *args, **kwds)

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
    with rts.queue_scope(sid=sid, trace=False):
      rts.Q = copy(rts.qtable[qid])
      assert rts.qid != qid
      rhs_qid = rts.qid
      rhs_seteval = graph.Node(seteval.info, sid, rts.qid)
    rts.filter_queue(qid, cid, LEFT)
    rts.filter_queue(rhs_qid, cid, RIGHT)
    yield rts.prelude._Choice
    yield cid
    yield graph.Node(rts.setfunctions.allValues, seteval)
    yield graph.Node(rts.setfunctions.allValues, rhs_seteval)

def applyS(rts, _0, capture=False):
  # applyS :: PartialS (a -> b) -> a -> PartialS b
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  missing, term = partapplic.target.successors
  assert inspect.isa_unboxed_int(missing)
  assert inspect.isa_func(term) or inspect.isa_ctor(term)
  arg = _0.target.successors[1]
  assert missing >= 1
  _SetGuard = rts.setfunctions._SetGuard
  if not capture:
    arg = graph.Node(_SetGuard, NO_SID, arg)
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
    _SetGuard = rts.setfunctions._SetGuard
    goal = graph.Node(
        term.info
      , *[graph.Node(_SetGuard, sid, inspect.get_setguard_value(t))
             if inspect.info_of(t) is _SetGuard.info and inspect.get_set_id(t) == NO_SID
             else t
                 for t in term.successors
           ]
      )
  qid = rts.create_queue(sid, goal)
  yield rts.setfunctions.Values
  yield graph.Node(
      rts.setfunctions.allValues
    , graph.Node(rts.setfunctions.SetEval, sid, qid)
    )

def exprS(rts, _0):
  yield rts.setfunctions.PartialS
  yield ENCAPSULATED_EXPR
  yield _0.successors[0]

def set_(rts, _0):
  # set :: a -> PartialS a
  _1 = rts.variable(_0, 0)
  _1.hnf()
  assert _1.info is rts.prelude._PartApplic.info
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

_functions_ = [
    _F('allValues', 1, metadata={'py.rawfunc': allValues})
  , _F('applyS'   , 1, metadata={'py.rawfunc': applyS})
  , _F('captureS' , 1, metadata={'py.rawfunc': captureS})
  , _F('evalS'    , 1, metadata={'py.rawfunc': evalS})
  , _F('exprS'    , 1, metadata={'py.rawfunc': exprS})
  , _F('set'      , 1, metadata={'py.rawfunc': set_})
  , _F('set0'     , 1, metadata={'py.rawfunc': setN})
  , _F('set1'     , 1, metadata={'py.rawfunc': setN})
  , _F('set2'     , 1, metadata={'py.rawfunc': setN})
  , _F('set3'     , 1, metadata={'py.rawfunc': setN})
  , _F('set4'     , 1, metadata={'py.rawfunc': setN})
  , _F('set5'     , 1, metadata={'py.rawfunc': setN})
  , _F('set6'     , 1, metadata={'py.rawfunc': setN})
  , _F('set7'     , 1, metadata={'py.rawfunc': setN})
  ]

SetFunctions = icurry.IModule(
    fullname='Control.SetFunctions', imports=[], types=_types_, functions=_functions_
  )
