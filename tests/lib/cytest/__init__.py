# ================================================================================
# Install the breakpoint function into the built-in module so it can be used
# anywhere.  This is the VERY FIRST THING done, so that breakpoint can be used
# in the curry module itself when debugging.
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
  banner = "\n[%s:%s%s]" % (namespace['__file__'], frame.f_lineno, msg)
  code.interact(banner=banner, local=namespace)
import __builtin__
__builtin__.breakpoint = breakpoint
# ================================================================================

from cStringIO import StringIO
from curry.interpreter.analysis import isa as cy_isa
from curry.interpreter.runtime import Node
from curry.llvm import isa as llvm_isa
import collections
import contextlib
import curry
import gzip
import inspect
import os
import sys
import textwrap
import types
import unittest

# Enable a break when certain exceptions occur.  For instance, this can be used
# to break whenever a RuntimeError or AssertionError occurs (n.b., that's an
# assertion failure, NOT a unittest.assert* failure).
def breakOn(exc_name):
  exception = getattr(__builtin__, exc_name)
  def __init__(self, *args, **kwds):
    breakpoint(depth=1)
    return super(self, exc_name).__init__(*args, **kwds)
  replacement = type(exc_name, (exception,), {'__init__': __init__})
  setattr(__builtin__, exc_name, replacement)

for exc_name in os.environ.get('SPRITE_CATCH_ERRORS', '').split(','):
  if exc_name:
    breakOn(exc_name)

@contextlib.contextmanager
def trap():
  '''
  (Built-in) Traps test failures for debugging.

      with trap():
        self.assertTrue(...)
  '''
  try:
    yield None
  except AssertionError as e:
    breakpoint(msg=repr(str(e)), depth=2)
    raise

__builtin__.trap = trap

class TestCase(unittest.TestCase):
  def tearDown(self):
    # Reset Curry after running each test to clear loaded modules, etc.
    reload(curry)

  def compareGolden(self, objs, filename, update=False):
    '''
    Compare an object or objects against a golden file.

    If ``update`` tests true, then just update the golden file instead.
    '''
    buf = StringIO()
    if isinstance(objs, collections.Sequence):
      for obj in objs: buf.write(str(obj))
    else:
      buf.write(str(objs))
    open_ = gzip.open if filename.endswith('.gz') else open
    if update:
      with open_(filename, 'wb') as au:
        au.write(buf.getvalue())
    else:
      with open_(filename, 'rb') as au:
        try:
          self.assertEqual(buf.getvalue(), au.read())
        except:
          breakpoint()

  def assertIsa(self, obj, ty):
    isa = cy_isa if isinstance(obj, Node) else llvm_isa
    self.assertTrue(isa(obj, ty))

  def assertIsNotA(self, obj, ty):
    isa = cy_isa if isinstance(obj, Node) else llvm_isa
    self.assertFalse(isa(obj, ty))

  def assertMayRaise(self, exception, expr, msg=None):
    if exception is None:
      try:
        expr()
      except:
        info = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        self.fail('%s raised%s' % (repr(info[0]), tail))
    else:
      try:
        self.assertRaises(exception, expr)
      except:
        ty,val,tb = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        raise ty, ty(str(val) + tail), tb
  
  def assertMayRaiseRegexp(self, exception, regexp, expr, msg=None):
    if exception is None:
      try:
        expr()
      except:
        info = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        self.fail('%s raised%s' % (repr(info[0]), tail))
    else:
      try:
        self.assertRaisesRegexp(exception, regexp, expr)
      except:
        ty,val,tb = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        raise ty, ty(str(val) + tail), tb
