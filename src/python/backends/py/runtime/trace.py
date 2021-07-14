def show(char, symbol, indent, frame, expr=None):
  expr = frame.expr[()] if expr is None else expr
  print '%1s %3s %-50s %s' % (
      char, symbol, '%s%s' % ('  ' * indent, expr), frame
    )

def _frame(rts):
  from .api import FAIR_SCHEME_VERSION
  if FAIR_SCHEME_VERSION == 1:
    return getattr(rts, 'currentframe', '')
  else:
    return rts.C

def enter_rewrite(rts, indent, expr):
  if rts.tracing:
    show('S', '<<<', indent, _frame(rts), expr)

def exit_rewrite(rts, indent, expr):
  if rts.tracing:
    show('S', '>>>', indent, _frame(rts), expr)

def failed(rts):
  if rts.tracing:
    show('F', ':::', 0, _frame(rts))

def yield_(rts, value):
  if rts.tracing:
    show('Y', ':::', 0, _frame(rts), value)

def kill(rts):
  if rts.tracing:
    show('K', ':::', 0, _frame(rts))

def activate_frame(rts):
  if rts.tracing:
    show('F', ':::', 0, _frame(rts))

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

  def activate_frame(self):
    active_frame(self.rts)
