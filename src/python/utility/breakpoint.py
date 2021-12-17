# ================================================================================
# Install built-in functions for debugging and development.  This must be done
# before loading anything from the project.

import six
from six.moves import builtins, range

def breakpoint(msg='', depth=0):
  '''(Built-in) Starts an interactive prompt.  For development and debugging.'''
  import code, inspect, pydoc
  frame = inspect.currentframe()
  for i in range(depth+1):
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

builtins.breakpoint = breakpoint

def pdbtrace():
  '''(Built-in) Starts PDB.'''
  import pdb
  pdb.set_trace()

builtins.pdbtrace = pdbtrace
