# The llvm.types submodule provides the predefined types.  Star-import is
# intended.
import cytest # from ./lib; must be first
from curry.llvm import *
from curry.llvm.types import *
import ctypes

class TestLLVMTypes(cytest.TestCase):
  def test_predefined_types(self):
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

  def test_primitive_type_constructors(self):
    isz = lambda ty: "i%d" % (8 * ctypes.sizeof(ty))
    self.assertEqual(str(int_())      , isz(ctypes.c_int))
    self.assertEqual(str(int_(12))    , "i12")
    self.assertEqual(str(long())      , isz(ctypes.c_long))
    self.assertEqual(str(longlong())  , isz(ctypes.c_longlong))
    self.assertEqual(str(float_())    , "float")
    self.assertEqual(str(double())    , "double")
    self.assertEqual(str(longdouble()), "fp128")

  def test_type_composers(self):
    self.assertEqual(str(i8.p), "i8*")
    self.assertEqual(str(char[7]), "[7 x i8]")
    self.assertEqual(str(fp32[2].p), "[2 x float]*")
    self.assertEqual(str(i32*4), "<4 x i32>")
    self.assertEqual(str(2*fp64), "<2 x double>")
    self.assertEqual(str(void()), "void ()")
    self.assertEqual(str(i32(varargs=True)), "i32 (...)")
    self.assertEqual(str(i32(char, varargs=True)), "i32 (i8, ...)")
    self.assertEqual(str(fp64(fp64)), "double (double)")
    self.assertEqual(str(i8(i8,i8,i8,i8,i8,i8)), "i8 (i8, i8, i8, i8, i8, i8)")
    self.assertEqual(str(struct("abc")), "%abc = type opaque")
    self.assertEqual(str(struct([char,i32,fp32])), "{ i8, i32, float }")
    self.assertEqual(str(struct("abc", [bool_, char])), "%abc = type { i1, i8 }")
    self.assertRaisesRegexp(TypeError, 'pointer to void is not permitted', lambda: void.p)

  def test_isa_checks(self):
    self.assertIsa(i32[2], ArrayType)
    self.assertIsa(fp32, FPType)
    self.assertIsa(i32(), FunctionType)
    self.assertIsa(i32, IntegerType)
    self.assertIsa(i32.p, PointerType)
    self.assertIsa(struct([i8]), StructType)
    self.assertIsa((32*i8), VectorType)
    self.assertIsa(void, VoidType)
    #
    self.assertIsNotA(i32, ArrayType)
    self.assertIsNotA(i32, FPType)
    self.assertIsNotA(void, FunctionType)
    self.assertIsNotA(fp32.p, IntegerType)
    self.assertIsNotA(i32, PointerType)
    self.assertIsNotA(i8, StructType)
    self.assertIsNotA(i8[8], VectorType)
    self.assertIsNotA(i8, VoidType)

  def test_subtypes(self):
    self.assertEqual(int_(32), int_(32))
    self.assertEqual(i32, int_(32))
    self.assertEqual(i32.subtypes, [])
    self.assertEqual(fp32.subtypes, [])
    self.assertEqual(i8[2].subtypes, [i8])
    self.assertEqual(i32.p.subtypes, [i32])
    self.assertEqual(void(i32,i8).subtypes, [void,i32,i8])
    self.assertEqual((16*i8).subtypes, [i8])
    self.assertEqual(struct([fp32, i8[2], i8.p]).subtypes, [fp32, i8[2], i8.p])

  def test_struct_name(self):
    self.assertEqual(struct('foo', [i32,i8.p]).struct_name, 'foo')
    self.assertRaisesRegexp(TypeError, "expected a struct, got 'i8'", lambda: i8.struct_name)

  def test_array_extents(self):
    self.assertEqual(i8[2][3][7].array_extents, [7,3,2])
    self.assertRaisesRegexp(TypeError, "expected an array, got 'i8'", lambda: i8.array_extents)

  def test_sizeof(self):
    self.assertEqual(i8.sizeof, 1)
    self.assertEqual(i16.sizeof, 2)
    self.assertEqual(i32.sizeof, 4)
    self.assertEqual(i64.sizeof, 8)
    self.assertEqual(i128.sizeof, 16)
    self.assertEqual(fp32.sizeof, 4)
    self.assertEqual(fp64.sizeof, 8)
    self.assertEqual(fp128.sizeof, 16)
    self.assertEqual(i8.p.sizeof, ctypes.sizeof(ctypes.c_char_p))
    self.assertEqual(i8[10].sizeof, 10)
    self.assertEqual(fp32[7].sizeof, 28)
    self.assertEqual(i8[2][3][5].sizeof, 30)
    self.assertEqual((4*i32).sizeof, 16)
    self.assertEqual(struct({i8,i32}).sizeof, 2*i32.sizeof)
    self.assertRaisesRegexp(TypeError, "type 'void' is unsized", lambda: void.sizeof)
    self.assertRaisesRegexp(TypeError, "type 'i8 \(\)' is unsized", lambda: i8().sizeof)

  def test_decay(self):
    self.assertEqual(i8().decay, i8().p) # function -> pointer
    self.assertEqual(i32[2].decay, i32.p) # array -> pointer
    self.assertEqual(i8.decay, i8)

  def test_common_type(self):
    self.assertEqual(common_type(i32,fp32), fp32)
    self.assertEqual(common_type(bool_,i8,i32,i64), i64)
    self.assertEqual(common_type(bool_, fp64), fp64)
    self.assertEqual(common_type(i8(), i8().p), i8().p)
    self.assertEqual(common_type(i8.p(), i8.p().p), i8.p().p)
    self.assertRaisesRegexp(TypeError, 'no common type', lambda: common_type(i8(), i8.p().p))
    self.assertEqual(common_type(i8[3], i8[4]), i8.p)
    self.assertEqual(common_type(struct([i8,i32]), struct([i8,i32])), struct([i8,i32]))
    self.assertRaisesRegexp(TypeError, 'no common type', lambda: common_type(struct([i8,i32]), struct([i8.p,i32])))

  def test_isa(self):
    self.assertTrue(i32.isa(IntegerType))


