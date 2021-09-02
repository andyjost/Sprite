# ================================================================================
# Install built-in functions for debugging and development.  This must be done
# before loading anything from the project.
import __builtin__

def breakpoint(msg='', depth=0):
  '''(Built-in) Starts an interactive prompt.  For development and debugging.'''
  import code, inspect, pydoc
  frame = inspect.currentframe()
  for i in xrange(depth+1):
    frame = frame.f_back
  namespace = dict(help=pydoc.help)
  namespace.update(frame.f_globals)
  namespace.update(frame.f_locals)
  if msg:
    msg = " - " + msg
  banner = "\n[%s:%s%s]" % (namespace.get('__file__', None), frame.f_lineno, msg)
  code.interact(banner=banner, local=namespace)

__builtin__.breakpoint = breakpoint

def pdbtrace():
  '''(Built-in) Starts PDB.'''
  import pdb
  pdb.set_trace()

__builtin__.pdbtrace = pdbtrace
