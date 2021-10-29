from . import types

__all__ =['show']

def show(arg, top=True):
  if isinstance(arg, types.Applic):
    if getattr(arg.f, 'is_operator', False) and len(arg.args) == 2:
      lhs = show(arg.args[0], top=False)
      rhs = show(arg.args[1], top=False)
      string = '%s%s%s' % (lhs, arg.f, rhs)
      return string if top else '(%s)' % string
    else:
      return ' '.join(map(str, arg._seq_))
  elif isinstance(arg, list):
    return '[%s]' % ', '.join(show(a) for a in arg)
  elif isinstance(arg, tuple):
    return '(%s)' % ', '.join(show(a) for a in arg)
  elif isinstance(arg, types.Literal):
    return repr(arg)
  else:
    return str(arg)


