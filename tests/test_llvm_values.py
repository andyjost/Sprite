from curry.llvm.types import *
from curry.llvm import value
import cytest

class TestLLVMValues(cytest.TestCase):
  def test_values(self):
    # Conversion to value.
    self.assertEqual(value(1).typeof, i64)
    self.assertEqual(value(1.0).typeof, fp64)

    # Equality among values.
    # self.assertEqual(value(1), 1)
    # self.assertEqual(value(1), 1.0)
    # self.assertNotEqual(value(1), 2)
    # self.assertNotEqual(value(1), 1.1)
    # self.assertEqual(value(1), value(1))
    # self.assertNotEqual(value(1), value(2))
    # self.assertEqual(value(1), value(1.0))

    # Type instantiation.
    # self.assestEqual(i32(1), 1)


    # import code
    # code.interact(local=dict(globals(), **locals()))
