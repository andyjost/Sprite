from .... import icurry
from .... import runtime
from .transforms import *

from .exceptions import *
from .graph import *
from .misc import *
from .transforms import *

__all__ = ['D', 'N', 'S', 'hnf']

def D(evaluator):
  '''The dispatch (D) Fair Scheme procedure.'''
  while evaluator.queue:
    frame = evaluator.queue.popleft()
    evaluator.interp.currentframe = frame
    if evaluator._handle_frame_if_blocked(frame):
      continue
    expr = frame.expr
    target = expr[()]
    if evaluator.interp.flags['trace']:
      print 'F :::', target, frame
    if isinstance(target, icurry.ILiteral):
      if evaluator.interp.flags['trace']:
        print 'Y :::', target, frame
      yield target
      continue
    tag = target.info.tag
    if tag == runtime.T_CHOICE:
      evaluator.queue.extend(frame.fork())
    elif tag == runtime.T_BIND:
      evaluator.queue.extend(frame.constrain())
    elif tag == runtime.T_FAIL:
      if evaluator.interp.flags['trace']:
        print 'X :::', frame
      continue # discard
    elif tag == runtime.T_FREE:
      try:
        frame.check_freevar_bindings(target, lazy=False)
      except E_CONTINUE:
        # TODO: Maybe a property for frame.expr would be better.
        frame.expr = evaluator.add_prefix(frame.expr)
        evaluator.queue.append(frame)
      else:
        if evaluator.interp.flags['trace']:
          print 'Y :::', target, frame
        yield target
    elif tag == runtime.T_FUNC:
      try:
        S(evaluator.interp, target)
      except E_CONTINUE:
        # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      except E_UPDATE_CONTEXT as cxt:
        frame.expr = cxt.expr
        evaluator.queue.append(frame)
      else:
        # TODO: The expr property was removed, so this next line does not do
        # what is says.
        frame.expr = frame.expr # insert FWD node, if needed.
        evaluator.queue.append(frame)
    elif tag >= runtime.T_CTOR:
      try:
        _, freevars = N(evaluator.interp, expr, target)
      except E_CONTINUE:
        # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
        evaluator.queue.append(frame)
      except E_RESIDUAL as res:
        evaluator.queue.append(frame.block(blocked_by=res.ids))
      else:
        target = expr[()]
        if target.info.tag == tag:
          if evaluator.interp.flags['trace']:
            print 'Y :::', target, frame
          yield target
        else:
          evaluator.queue.append(frame)
    else:
      assert False

def N(interp, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
  path = [] if path is None else path
  target = root[path] if target is None else target
  assert target.info.tag >= runtime.T_CTOR
  freevars = set() if freevars is None else freevars
  if target.info is interp.prelude._PartApplic.info:
    # A partial application is a value even through it may contain a function
    # symbol.  The first successor (# of arguments remaining) is unboxed, so there
    # is nothing to normalize.
    return target, freevars
  path.append(None)
  try:
    for path[-1], succ in enumerate(target):
      while True:
        if isinstance(succ, icurry.ILiteral):
          break
        succ = succ[()]
        tag = succ.info.tag
        if tag == runtime.T_FAIL:
          Node(interp.prelude._Failure, target=root)
          raise E_CONTINUE()
        elif tag == runtime.T_CHOICE:
          lift_choice(interp, root, path)
          raise E_CONTINUE()
        elif tag == runtime.T_BIND:
          lift_constr(interp, root, path)
          raise E_CONTINUE()
        elif tag == runtime.T_FREE:
          interp.currentframe.check_freevar_bindings(succ, path, lazy=False)
          freevars.add(succ)
          break
        elif tag == runtime.T_FUNC:
          try:
            S(interp, succ)
          except E_CONTINUE:
            pass
        elif tag >= runtime.T_CTOR:
          _,freevars2 = N(interp, root, succ, path, freevars)
          freevars.update(freevars2)
          break
        else:
          assert False
  finally:
    path.pop()
  return target, freevars

def hnf(interp, expr, path, typedef=None, values=None):
  assert path
  assert expr.info.tag == runtime.T_FUNC
  target = expr[path]
  while True:
    if isinstance(target, icurry.ILiteral):
      return target
    tag = target.info.tag
    if tag == runtime.T_FAIL:
      Node(interp.prelude._Failure, target=expr)
      raise E_CONTINUE()
    elif tag == runtime.T_CHOICE:
      lift_choice(interp, expr, path)
      raise E_CONTINUE()
    elif tag == runtime.T_BIND:
      lift_constr(interp, expr, path)
      raise E_CONTINUE()
    elif tag == runtime.T_FREE:
      if typedef is None or typedef is interp.type('Prelude.Int'):
        vid = get_id(target)
        if vid in interp.currentframe.lazy_bindings.read:
          bl, br = interp.currentframe.lazy_bindings.read[vid][0]
          assert bl is target
          replacement = replace_copy(interp, expr, path, br)
          raise E_UPDATE_CONTEXT(replacement)
        elif values:
          values = map(int, values)
          replace(interp, expr, path
            , Node(interp.integer.narrowInt, expr[path], interp.expr(values))
            )
          target = expr[path]
        else:
          raise E_RESIDUAL([vid])
      else:
        target = instantiate(interp, expr, path, typedef)
    elif tag == runtime.T_FUNC:
      try:
        S(interp, target)
      except E_CONTINUE:
        pass
      except E_UPDATE_CONTEXT as cxt:
        replacement = replace_copy(interp, expr, path, cxt.expr)
        raise E_UPDATE_CONTEXT(replacement)
    elif tag >= runtime.T_CTOR:
      return target
    elif tag == runtime.T_FWD:
      target = expr[path]
    else:
      assert False

def S(interp, target):
  '''The step (S) Fair Scheme procedure.'''
  interp._stepper(target)

