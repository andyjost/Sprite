'''
Importing this module adds ``breakpoint`` and ``pdbtrace`` as built-ins.
'''

import six
__all__ = ['breakpoint', 'pdbtrace']

def breakpoint(msg='', depth=0):
  '''(Built-in) Starts an interactive prompt.  For development and debugging.'''
  import code, inspect, pydoc
  frame = inspect.currentframe()
  for i in six.moves.range(depth+1):
    frame = frame.f_back
  namespace = dict(help=pydoc.help)
  namespace.update(frame.f_globals)
  namespace.update(frame.f_locals)
  if msg:
    msg = " - " + msg
  banner = "\n[%s:%s%s]" % (namespace.get('__file__', None), frame.f_lineno, msg)
  kwds = {'banner':banner, 'local':namespace}
  if not six.PY2:
    kwds['exitmsg'] = ''
  code.interact(**kwds)

six.moves.builtins.breakpoint = breakpoint

def pdbtrace():
  '''(Built-in) Starts PDB.'''
  import pdb
  pdb.set_trace()

six.moves.builtins.pdbtrace = pdbtrace
