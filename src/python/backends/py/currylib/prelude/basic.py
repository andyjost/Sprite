from .....exceptions import EvaluationError

__all__ = ['choice', 'error', 'failed', 'not_used']

def choice(rts, _0):
  yield rts.Choice
  yield next(rts.idfactory)
  yield _0.successors[0]
  yield _0.successors[1]

def error(rts, msg):
  msg = str(rts.topython(msg))
  raise EvaluationError(msg)

def failed(rts):
  return [rts.Failure]

def not_used(rts, _0):
  raise RuntimeError("function 'Prelude.%s' is not used by Sprite" % _0.info.name)

