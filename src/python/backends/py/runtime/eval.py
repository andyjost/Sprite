from __future__ import absolute_import
from .... import icurry
from .... import exceptions
import collections

from .exceptions import *
from .frame import *
from .graph import *
from .nondet import *
from .misc import *

__all__ = ['Evaluator', 'hnf', 'N', 'S']

class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    goal = self.add_prefix(goal)
    self.queue = collections.deque([Frame(interp, goal)])
    # The number of consecutive blocked frames handled.  If this ever equals
    # the queue length, then the computation fails.
    self.n_consecutive_blocked_seen = 0
    return self

  def add_prefix(self, goal):
    '''Adds the prefix needed for top-level expressions.'''
    return self.interp.expr(
        getattr(self.interp.prelude, '$!!')
      , self.interp.prelude.id
      , goal
      )

  def D(self):
    '''The dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      frame = self.queue.popleft()
      self.interp.currentframe = frame
      if self._handle_frame_if_blocked(frame):
        continue
      expr = frame.expr
      target = expr[()]
      if self.interp.flags['trace']:
        print 'F :::', target, frame
      if isinstance(target, icurry.ILiteral):
        if self.interp.flags['trace']:
          print 'Y :::', target, frame
        yield target
        continue
      tag = target.info.tag
      if tag == T_CHOICE:
        self.queue.extend(frame.fork())
      elif tag == T_BIND:
        self.queue.extend(frame.constrain())
      elif tag == T_FAIL:
        if self.interp.flags['trace']:
          print 'X :::', frame
        continue # discard
      elif tag == T_FREE:
        try:
          frame.check_freevar_bindings(target, lazy=False)
        except E_CONTINUE:
          # TODO: Maybe a property for frame.expr would be better.
          frame.expr = self.add_prefix(frame.expr)
          self.queue.append(frame)
        else:
          if self.interp.flags['trace']:
            print 'Y :::', target, frame
          yield target
      elif tag == T_FUNC:
        try:
          S(self.interp, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        except E_UPDATE_CONTEXT as cxt:
          frame.expr = cxt.expr
          self.queue.append(frame)
        else:
          # TODO: The expr property was removed, so this next line does not do
          # what is says.
          frame.expr = frame.expr # insert FWD node, if needed.
          self.queue.append(frame)
      elif tag >= T_CTOR:
        try:
          _, freevars = N(self.interp, expr, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        else:
          target = expr[()]
          if target.info.tag == tag:
            if self.interp.flags['trace']:
              print 'Y :::', target, frame
            yield target
          else:
            self.queue.append(frame)
      else:
        assert False

  def _handle_frame_if_blocked(self, frame):
    '''
    Process a blocked frame, if applicable.  Returns true if the frame was
    indeed blocked, unless the computation suspends.
    '''
    if frame.blocked:
      self.queue.append(frame)
      if frame.unblock():
        self.n_consecutive_blocked_seen = 0
      else:
        self.n_consecutive_blocked_seen += 1
        if self.n_consecutive_blocked_seen == len(self.queue):
          raise exceptions.EvaluationSuspended()
      return True
    else:
      self.n_consecutive_blocked_seen = 0
      return False


def N(interp, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
  path = [] if path is None else path
  target = root[path] if target is None else target
  assert target.info.tag >= T_CTOR
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
        if tag == T_FAIL:
          Node(interp.prelude._Failure, target=root)
          raise E_CONTINUE()
        elif tag == T_CHOICE:
          lift_choice(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_BIND:
          lift_constr(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_FREE:
          interp.currentframe.check_freevar_bindings(succ, path, lazy=False)
          freevars.add(succ)
          break
        elif tag == T_FUNC:
          try:
            S(interp, succ)
          except E_CONTINUE:
            pass
        elif tag >= T_CTOR:
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
  assert expr.info.tag == T_FUNC
  target = expr[path]
  while True:
    if isinstance(target, icurry.ILiteral):
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      Node(interp.prelude._Failure, target=expr)
      raise E_CONTINUE()
    elif tag == T_CHOICE:
      lift_choice(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_BIND:
      lift_constr(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_FREE:
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
    elif tag == T_FUNC:
      try:
        S(interp, target)
      except E_CONTINUE:
        pass
      except E_UPDATE_CONTEXT as cxt:
        replacement = replace_copy(interp, expr, path, cxt.expr)
        raise E_UPDATE_CONTEXT(replacement)
    elif tag >= T_CTOR:
      return target
    elif tag == T_FWD:
      target = expr[path]
    else:
      assert False

def S(interp, target):
  '''The step (S) Fair Scheme procedure.'''
  interp._stepper(target)

