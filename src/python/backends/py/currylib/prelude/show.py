from ..... import show as show_module

__all__ = ['show']

def show(rts, arg):
  if arg.is_boxed:
    string = show_module.show(arg.target)
  elif isinstance(arg.target, float):
    string = show_module.show_float(arg.target)
  else:
    string = str(arg.target)
  if len(string) == 1:
    string = [string]
  result = rts.expr(string)
  yield rts.Fwd
  yield result

