'''
Implements tracing to debug Curry evaluation.
'''

def show(char, symbol, indent, qid, config, expr=None):
  if config is not None:
    expr = config.expr[()] if expr is None else expr
    print '%1s %3s %-50s %s:%s' % (
        char, symbol, '%s%s' % ('  ' * indent, expr), qid, config
      )
  else:
    print '%1s %3s %-50s' % (
        char, symbol, '%s%s' % ('  ' * indent, expr)
      )

def enter_rewrite(rts, indent, expr):
  if rts.tracing:
    show('S', '<<<', indent, rts.qid, rts.C, expr)

def exit_rewrite(rts, indent, expr):
  if rts.tracing:
    show('S', '>>>', indent, rts.qid, rts.C, expr)

def failed(rts):
  if rts.tracing:
    show('F', ':::', 0, rts.qid, rts.C)

def yield_(rts, value):
  if rts.tracing:
    show('Y', ':::', 0, None, None, value)

def kill(rts):
  if rts.tracing:
    show('K', ':::', 0, rts.qid, rts.C)

def activate_queue(rts, qid):
  if rts.tracing:
    print 'I ::: (switching to queue %s)' % qid

def set_goal(rts, goal, qid):
  if rts.tracing:
    print 'I ::: setting goal: %s' % goal


class Trace(object):
  def __init__(self, rts):
    self.rts = rts
    self.indent = 0

  def enter_rewrite(self, expr):
    enter_rewrite(self.rts, self.indent, expr)
    self.indent += 1

  def exit_rewrite(self, expr):
    self.indent -= 1
    exit_rewrite(self.rts, self.indent, expr)

  def failed(self):
    failed(self.rts)

  def yield_(self, value):
    yield_(self.rts, value)

  def kill(self):
    kill(self.rts)

  def activate_queue(self, qid):
    activate_queue(self.rts, qid)

  def set_goal(self, goal, qid):
    set_goal(self.rts, goal, qid)

def trace_values(f):
  '''Wraps the D procedure to trace value creation.'''
  def value_tracer(rts):
    for value in f(rts):
      rts.trace.yield_(value)
      yield value
  return value_tracer

def trace_steps(f):
  '''Wraps the S procedure to trace the application of steps.'''
  def step_tracer(rts, node):
    rts.trace.enter_rewrite(node)
    try:
      f(rts, node)
    finally:
      rts.trace.exit_rewrite(node)
  return step_tracer
