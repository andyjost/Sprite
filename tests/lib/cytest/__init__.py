from cStringIO import StringIO
import collections
import contextlib
import gzip
import os
import sys
import unittest

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
  banner = "\n[%s:%s%s]" % (namespace['__file__'], frame.f_lineno, msg)
  code.interact(banner=banner, local=namespace)

__builtin__.breakpoint = breakpoint

def pdbtrace():
  '''(Built-in) Starts PDB.'''
  import pdb
  pdb.set_trace()

__builtin__.pdbtrace = pdbtrace

@contextlib.contextmanager
def trap():
  '''
  (Built-in) Traps test failures for debugging.

      with trap():
        self.assertTrue(...)
  '''
  try:
    yield None
  except Exception as e:
    breakpoint(msg=repr(str(e)), depth=2)
    raise

__builtin__.trap = trap

# Enable a break when certain exceptions occur.  For instance, this can be used
# to break whenever a RuntimeError or AssertionError occurs (n.b., that's an
# assertion failure, NOT a unittest.assert* failure).
def breakOn(exc_name):
  exception = getattr(__builtin__, exc_name)
  def __new__(cls, *args, **kwds):
    # breakpoint(depth=1)
    pdbtrace()
    return exception(*args, **kwds)
  replacement = type(exc_name, (exception,), {'__new__': __new__})
  setattr(__builtin__, exc_name, replacement)

for exc_name in os.environ.get('SPRITE_CATCH_ERRORS', '').split(','):
  if exc_name:
    breakOn(exc_name)

# ================================================================================

import curry
from curry.interpreter.analysis import isa as cy_isa
from curry.interpreter.runtime import Node
from curry.llvm import isa as llvm_isa


class TestCase(unittest.TestCase):
  '''A base test case class for testing Sprite.'''
  def tearDown(self):
    # Reset Curry after running each test to clear loaded modules, etc.
    reload(curry)

  def compareGolden(self, objs, filename, update=False):
    '''
    Compare an object or objects against a golden file.

    Parameters:
    -----------
    ``objs``
        An object or sequence of objects to compare.
    ``filename``
        The name of the file that stores the golden result.
    ``update``
        If true, then just update the golden file.
    '''
    buf = StringIO()
    if isinstance(objs, collections.Sequence):
      for obj in objs: buf.write(str(obj))
    else:
      buf.write(str(objs))
    value = buf.getvalue()
    open_ = gzip.open if filename.endswith('.gz') else open
    if update:
      with open_(filename, 'wb') as au:
        au.write(value)
    else:
      with open_(filename, 'rb') as au:
        self.assertEqual(value, au.read())

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
