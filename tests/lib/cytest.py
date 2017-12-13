from cStringIO import StringIO
from curry.llvm import isa
import __builtin__
import collections
import contextlib
import sys
import unittest

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
    if update:
      with open(filename, 'wb') as au:
        au.write(buf.getvalue())
    else:
      with open(filename, 'rb') as au:
        self.assertEqual(buf.getvalue(), au.read())

  def assertIsa(self, obj, llvmty):
    self.assertTrue(isa(obj, llvmty))

  def assertIsNotA(self, obj, llvmty):
    self.assertFalse(isa(obj, llvmty))

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
