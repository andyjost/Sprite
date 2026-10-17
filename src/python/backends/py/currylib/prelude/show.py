from .....show import show as show_node, show_float

__all__ = ['show']

def show(rts, arg):
  if arg.is_boxed:
    string = show_node(arg.target)
  elif isinstance(arg.target, float):
    string = show_float(arg.target)
  else:
    string = str(arg.target)
  if len(string) == 1:
    string = [string]
  result = rts.expr(string)
  yield rts.Fwd
  yield result

