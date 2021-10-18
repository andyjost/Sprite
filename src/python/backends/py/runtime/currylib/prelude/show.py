from ...... import show as show_module

__all__ = ['show']

def show(rts, arg):
  if arg.is_boxed:
    string = show_module.show(arg.target)
  else:
    string = str(arg.target)
  if len(string) == 1:
    string = [string]
  result = rts.expr(string)
  yield rts.prelude._Fwd
  yield result

