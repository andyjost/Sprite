from .. import graph

__all__ = ['CallStack', 'StackFrame']

class CallStack(object):
  def __init__(self):
    self.frames = []

  def realpath(self):
    for frame in self.frames:
      for part in frame.realpath:
        yield part

  def push(self, arg=None):
    frame = StackFrame(arg)
    self.frames.append(frame)

  def pop(self):
    self.frames.pop()


class StackFrame(object):
  def __init__(self, arg=None):
    self.obj = arg

  @property
  def realpath(self):
    return self.obj.realpath

  def set_from(self, arg):
    self.obj = arg


def with_N_stackframe(N_body):
  '''
  Wraps the N function.

  Performs stack manipulations for N.  Creates an instance of of WalkState,
  pushes it onto the stack, and adds it to the call.
  '''
  def N(rts, var):
    C = rts.C
    state = graph.walk(var.root, realpath=var.realpath)
    C.callstack.push(state)
    try:
      return N_body(rts, var, state)
    finally:
      C.callstack.pop()
  return N


def with_hnf_stackframe(hnf_body):
  '''
  Wraps the hnf function.

  Performs stack manipulations for hnf.  Pushes the inductive varible onto the
  stack.
  '''
  def hnf(rts, var, typedef=None, values=None):
    C = rts.C
    C.callstack.push(var)
    try:
      return hnf_body(rts, var, typedef, values)
    finally:
      C.callstack.pop()
  return hnf
