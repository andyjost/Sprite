def show(char, symbol, indent, frame, expr=None):
  expr = frame.expr[()] if expr is None else expr
  print '%1s %3s %-50s %s' % (
      char, symbol, '%s%s' % ('  ' * indent, expr), frame
    )

def _frame(rts):
  return getattr(rts, 'currentframe', '')

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
