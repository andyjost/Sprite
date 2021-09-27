'''Functions for tracing Curry evaluation.'''
import collections, contextlib

def show_queue(rts, qid=None):
  qid = rts.qid if qid is None else qid
  return 'queue %s: %s' % (qid, list(e.fingerprint for e in rts.qtable[qid]))

def enter_rewrite(rts, indent, expr):
  if rts.tracing:
    print 'S <<< %s%s' % ('  ' * indent, expr)

def exit_rewrite(rts, indent, expr):
  if rts.tracing:
    print 'S >>> %s%s' % ('  ' * indent, expr)

def failed(rts, qid=None):
  if rts.tracing:
    print 'Q ::: failed config dropped from %s' % show_queue(rts, qid)

def yield_(rts, value):
  if rts.tracing:
    print 'Y ::: %s' % value

def position(rts, indent, expr, path):
  if rts.tracing:
    print 'I ::: %sat path=%s of %s' % (
        '  ' * (indent + 1)
      , '[' + ','.join(map(str, path)) + ']'
      , expr
      )

def activate_queue(rts, qid):
  if rts.tracing:
    print 'Q ::: switching to %s' % show_queue(rts, qid)

@contextlib.contextmanager
def fork(rts, qid=None):
  if rts.tracing:
    qid = rts.qid if qid is None else qid
    cid = rts.grp_id()
    head_fp = str(rts.qtable[qid][0].fingerprint)
    try:
      yield
    finally:
      print 'Q ::: fork %s on cid=%s appending to %s' % (
          head_fp, cid, show_queue(rts, qid)
        )
  else:
    yield


class Trace(object):
  '''
  This object calls the freestanding trace functions to print log output.  It
  keeps track of the indent level and filters out clutter.  As an example of
  the latter, when an expression being inspected was just created in the
  previous step, it is not repeated.
  '''
  def __init__(self, rts):
    self.rts = rts
    self.indents = collections.defaultdict(int)
    self.prevexprs = collections.defaultdict(lambda: None)
    self.prevpaths = collections.defaultdict(lambda: None)

  def indent(self, qid=None):
    qid = self.rts.qid if qid is None else qid
    self.indent_value = self.indents[qid]
    self.indents[qid] += 1

  def dedent(self, qid=None):
    qid = self.rts.qid if qid is None else qid
    self.indents[qid] -= 1
    self.indent_value = self.indents[qid]

  def enter_rewrite(self, expr):
    self.indent()
    if self.prevexprs[self.rts.qid] != id(expr):
      enter_rewrite(self.rts, self.indent_value, expr)

  def exit_rewrite(self, expr, buffering=False):
    self.dedent()
    exit_rewrite(self.rts, self.indent_value, expr)
    self.prevexprs[self.rts.qid] = id(expr)

  def failed(self):
    failed(self.rts)

  def yield_(self, value):
    yield_(self.rts, value)

  def activate_queue(self, qid):
    activate_queue(self.rts, qid)

  def fork(self, qid=None):
    return fork(self.rts, qid)

  @contextlib.contextmanager
  def position(self, expr, path):
    qid = self.rts.qid
    key = id(expr), tuple(path)
    self.indent(qid)
    try:
      if self.prevpaths[qid] != key:
        position(self.rts, self.indent_value, expr, path)
      yield
      self.prevpaths[qid] = id(expr), tuple(path)
    finally:
      self.dedent(qid)



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
