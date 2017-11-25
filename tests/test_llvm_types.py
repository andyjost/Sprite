# The llvm.types submodule provides the predefined types.  Star-import is
# intended.
from curry.llvm.types import *
import curry.llvm as ll
import cytest
import ctypes

class TestLLVMTypes(cytest.TestCase):
  def test_types(self):
    # Predefined types.
    self.assertEqual(str(void) , "void")
    self.assertEqual(str(bool_), "i1")
    self.assertEqual(str(char) , "i8")
    self.assertEqual(str(i1)   , "i1")
    self.assertEqual(str(i8)   , "i8")
    self.assertEqual(str(i16)  , "i16")
    self.assertEqual(str(i32)  , "i32")
    self.assertEqual(str(i64)  , "i64")
    self.assertEqual(str(i128) , "i128")
    self.assertEqual(str(fp32) , "float")
    self.assertEqual(str(fp64) , "double")
    self.assertEqual(str(fp128), "fp128")
    # Type constructors.
    isz = lambda ty: "i%d" % (8 * ctypes.sizeof(ty))
    self.assertEqual(str(int_())      , isz(ctypes.c_int))
    self.assertEqual(str(int_(12))    , "i12")
    self.assertEqual(str(long())      , isz(ctypes.c_long))
    self.assertEqual(str(longlong())  , isz(ctypes.c_longlong))
    self.assertEqual(str(float_())    , "float")
    self.assertEqual(str(double())    , "double")
    self.assertEqual(str(longdouble()), "fp128")
    # Compound types.
    self.assertEqual(str(i8.p), "i8*")
    self.assertEqual(str(char[7]), "[7 x i8]")
    self.assertEqual(str(fp32[2].p), "[2 x float]*")
    self.assertEqual(str(void()), "void ()")
    self.assertEqual(str(i32(varargs=True)), "i32 (...)")
    self.assertEqual(str(i32(char, varargs=True)), "i32 (i8, ...)")
    self.assertEqual(str(fp64(fp64)), "double (double)")
    self.assertEqual(str(i8(i8,i8,i8,i8,i8,i8)), "i8 (i8, i8, i8, i8, i8, i8)")
    self.assertEqual(str(struct("abc")), "%abc = type opaque")
    self.assertEqual(str(struct([char,i32,fp32])), "{ i8, i32, float }")
    self.assertEqual(str(struct("abc", [bool_, char])), "%abc = type { i1, i8 }")
    
