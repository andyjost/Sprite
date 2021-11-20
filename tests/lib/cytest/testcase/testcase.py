import curry, re, sys, unittest

# Import all of the Curry-specific assert* functions.
from .assert_equal_to_file import *
from .assert_sets import *
from .assert_inspect import *

import six


__all__ = ['TestCase']

class TestCase(unittest.TestCase):
  '''A base test case class for testing Sprite.'''

  # Pull the Curry-specific assert* functions into this class.
  locals().update({
      name: obj for name, obj in six.iteritems(globals())
                if name.startswith('assert')
    })

  def tearDown(self):
    curry.reset() # Undo, e.g., path and I/O modifications after each test.

  # New in Python 3.4.
  if not hasattr(unittest.TestCase, 'assertRegex'):
    def assertRegex(self, string, pattern):
      string, pattern = str(string), str(pattern)
      self.assertTrue(
          re.search(pattern, string)
        , msg='%r does not match pattern %r' % (string, pattern)
        )

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


