from curry.llvm import *
import curry.llvm as ll
from curry.llvm.types import *
import cytest
import itertools
import numpy as np
import re
import sys

class TestLLVMValues(cytest.TestCase):
  def test_literalValueTypes(self):
    '''Literal value coercion'''
    # All integral types map to i64 and all floating point types to fp64.
    self.assertEqual(value(True).type, i64)
    self.assertEqual(value(False).type, i64)
    self.assertEqual(value(0).type, i64)
    self.assertEqual(value(1).type, i64)
    self.assertEqual(value(1.).type, fp64)
    self.assertEqual(value(np.bool(True)).type, i64)
    self.assertEqual(value(np.int8(5)).type, i64)
    self.assertEqual(value(np.int16(6)).type, i64)
    self.assertEqual(value(np.int32(7)).type, i64)
    self.assertEqual(value(np.int64(8)).type, i64)
    self.assertEqual(value(np.float32(1.1)).type, fp64)
    self.assertEqual(value(np.float64(1.1)).type, fp64)
    self.assertEqual(str(value(None)), 'void undef')

  def test_literalLimits(self):
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

  def test_casting(self):
    types = [
        i1, i8, i16, i32, i64, fp32, fp64   # Numbers
      , i8.p, void.p, struct([]).p, i32().p # Pointers
      , i32[4], i32[5], i64[2]              # Arrays
      , void, i32(i32)                      # Void and function
      , 4*fp32, 2*fp64, 3*fp32              # Vectors
      , struct([i32,4*i8]), struct([])      # Structs
      ]
    for src,dst in itertools.product(types, types):
      # Bitcast.
      self.assertMayRaiseRegexp(
          None if is_bitcastable(src, dst) else TypeError
        , re.escape(r"cannot bitcast '%s' to '%s'" % (src, dst))
        , lambda: bitcast(src.null_value, dst)
        , msg="for source '%s' and destination '%s'" % (src, dst)
        )
      # Value cast.
      self.assertMayRaiseRegexp(
          None if is_castable(src, dst) else TypeError
        , re.escape(r"cannot cast '%s' to '%s'" % (src, dst))
        , lambda: cast(src.null_value, dst)
        , msg="for source '%s' and destination '%s'" % (src, dst)
        )

  # def test_valueCasting(self):
  #   for bitwidth in [1, 8, 16, 32, 64]:
  #     ty = int_(bitwidth)
  #     # signed.
  #     minval = -2**(bitwidth-1)
  #     maxval = 2**(bitwidth-1)-1
  #     # print 'for', ty, 'min =', minval, 'max =', maxval

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
    # These exercise implicit conversion because the Python number must be
    # converted to a "value" object for type.__call__ to accept it.
    # From int.
    self.assertEqual(i8(1).type, i8)
    self.assertEqual(i16(1).type, i16)
    self.assertEqual(i32(1).type, i32)
    self.assertEqual(i64(1).type, i64)
    self.assertEqual(fp32(1).type, fp32)
    self.assertEqual(fp64(1).type, fp64)
    # From float.
    self.assertEqual(i8(1.).type, i8)
    self.assertEqual(i16(1.).type, i16)
    self.assertEqual(i32(1.).type, i32)
    self.assertEqual(i64(1.).type, i64)
    self.assertEqual(fp32(1.).type, fp32)
    self.assertEqual(fp64(1.).type, fp64)
    # Overflow.
    # self.assertEqual(i8(300).type, i8)
