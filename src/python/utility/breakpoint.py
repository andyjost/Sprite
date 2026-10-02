'''
Importing this module installs ``breakpoint`` as ``sys.breakpointhook`` and adds
``pdbtrace`` as a built-in.
'''

import builtins, sys
__all__ = ['breakpoint', 'pdbtrace']

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
  code.interact(banner=banner, local=namespace, exitmsg='')

sys.breakpointhook = breakpoint

def pdbtrace():
  '''(Built-in) Starts PDB.'''
  import pdb
  pdb.set_trace()

builtins.pdbtrace = pdbtrace
