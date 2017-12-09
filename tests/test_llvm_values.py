from curry.llvm import value
from curry.llvm.types import *
import cytest
import numpy as np
import sys

class TestLLVMValues(cytest.TestCase):
  def test_defaultValues(self):
    '''Literal value coercion'''
    # All integral types map to i64 and all floating point types to fp64.
    self.assertEqual(value(True).typeof, i64)
    self.assertEqual(value(False).typeof, i64)
    self.assertEqual(value(0).typeof, i64)
    self.assertEqual(value(1).typeof, i64)
    self.assertEqual(value(1.).typeof, fp64)
    self.assertEqual(value(np.bool(True)).typeof, i64)
    self.assertEqual(value(np.int8(5)).typeof, i64)
    self.assertEqual(value(np.int16(6)).typeof, i64)
    self.assertEqual(value(np.int32(7)).typeof, i64)
    self.assertEqual(value(np.int64(8)).typeof, i64)
    self.assertEqual(value(np.float32(1.1)).typeof, fp64)
    self.assertEqual(value(np.float64(1.1)).typeof, fp64)

  def test_literalRange(self):
    for i,(val,err) in enumerate([
        ( 2**63-1, False)
      , ( 2**63  , True)
      , (-2**63  , False)
      , (-2**63-1, True)
      , (np.inf  , False)
      , (-np.inf , False)
      , (-np.nan , False)
      , (np.finfo(float).max, False)
      , (np.finfo(float).min, False)
      ]):
      self.assertMayRaise(
          OverflowError if err else None
        , lambda: value(val)
        , msg='with value %s at i=%d' % (val, i)
        )

  def test_valueCasts(self):
    pass
    # self.assertRaisesRegexp(TypeError, r"cannot cast 'i64' to 'void \*'", lambda: void.p(value(1)))

    # Equality among values.
    # self.assertEqual(value(1), 1)
    # self.assertEqual(value(1), 1.0)
    # self.assertNotEqual(value(1), 2)
    # self.assertNotEqual(value(1), 1.1)
    # self.assertEqual(value(1), value(1))
    # self.assertNotEqual(value(1), value(2))
    # self.assertEqual(value(1), value(1.0))

  def test_implicitConversion(self):
    self.assertEqual(i8(1).typeof, i8)
    self.assertEqual(i16(1).typeof, i16)
    self.assertEqual(i32(1).typeof, i32)
    self.assertEqual(i64(1).typeof, i64)
    self.assertEqual(fp32(1).typeof, fp32)
    self.assertEqual(fp64(1).typeof, fp64)

    # import code
    # code.interact(local=dict(globals(), **locals()))
