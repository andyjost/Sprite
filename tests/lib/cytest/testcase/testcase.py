import curry, re, sys, unittest

# Import Curry-specific assert functions.
from .assert_equal_to_file import *
from .assert_sets import *
from .assert_inspect import *
import six

__all__ = ['TestCase']

class TestCase(unittest.TestCase):
  '''Base class for Sprite test cases.'''

  # Pull the Curry-specific assert functions into this class.
  locals().update({
      name: obj for name, obj in globals().items()
                if name.startswith('assert')
    })

  # Pull in the assertions defined in six.
  locals().update({
      name: obj for name, obj in six.__dict__.items()
                if name.startswith('assert')
                if not hasattr(unittest.TestCase, name)
    })

  def tearDown(self):
    curry.reset() # Undo, e.g., path and I/O modifications after each test.

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
        six.raise_from(ty(str(val) + tail), val)

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
        self.assertRaisesRegex(exception, regexp, expr)
      except:
        ty,val,tb = sys.exc_info()
        tail = '' if msg is None else ' %s' % msg
        six.raise_from(ty(str(val) + tail), val)


