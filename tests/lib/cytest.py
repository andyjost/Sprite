from cStringIO import StringIO
import collections
import unittest
from curry.llvm import isa

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

