from curry.llvm import *
from curry.llvm.types import *
import curry.llvm as ll
import cytest

class TestLLVMModule(cytest.TestCase):
  def testGlobals(self):
    m = module("foo")

    # Test with no globals.
    self.assertEqual(len(m.globals), 0)
    self.assertEqual(m.globals.keys(), [])
    self.assertEqual(m.globals.values(), [])
    self.assertEqual(m.globals.items(), [])
    self.assertEqual(m.globals, m.globals)
    self.assertFalse(m.globals)
    self.assertNotIn('x', m.globals)
    self.assertEqual(list(m.globals), [])
    self.assertRaisesRegexp(KeyError, 'x', lambda: m.globals['x'])

    # Define globals.
    m.def_('x', i64)
    m.def_('y', i8, const=True, linkage=STATIC, init=7)
    self.assertRaisesRegexp(
        ValueError, "global 'x' exists", lambda: m.def_('x', i64)
      )

    # Check for the globals.
    self.assertEqual(len(m.globals), 2)
    self.assertEqual(sorted(m.globals.keys()), ['x', 'y'])
    self.assertEqual(
        sorted(m.globals.values())
      , sorted([m.globals['x'], m.globals['y']])
      )
    self.assertEqual(
        sorted(m.globals.items())
      , sorted([('x', m.globals['x']), ('y', m.globals['y'])])
      )
    self.assertEqual(m.globals, m.globals)
    self.assertTrue(m.globals)
    self.assertIn('x', m.globals)
    self.assertEqual(sorted(list(m.globals)), ['x', 'y'])
    self.assertMayRaiseRegexp(None, 'x', lambda: m.globals['x'])
    self.assertMayRaiseRegexp(None, 'y', lambda: m.globals['y'])

    # Check attributes.
    x = m.globals['x']
    self.assertIsa(x, GlobalVariable)
    self.assertEqual(x.name, 'x')
    self.assertFalse(x.is_const)
    self.assertEqual(x.linkage, EXTERN)

    y = m.globals['y']
    self.assertIsa(y, GlobalVariable)
    self.assertEqual(y.name, 'y')
    self.assertTrue(y.is_const)
    self.assertEqual(y.linkage, STATIC)

    # Change attributes.
    x.name = 'foo'
    self.assertEqual(sorted(m.globals.keys()), ['foo', 'y'])
    x.linkage = STATIC
    self.assertEqual(x.linkage, STATIC)
    x.is_const = True
    self.assertTrue(x.is_const)

    # Delete a global.
    x.erase()
    self.assertNotIn('x', m.globals)
    self.assertNotIn('foo', m.globals)

    # Delete a global and check that references do not become dangling.
    y1 = m.globals['y']
    y2 = m.globals['y']
    del m.globals['y']
    str(y2)

# @mod.function(i64(i64), "n", linkage=EXTERNAL)
# def fact(n):
#   if n < 2:
#     return 1
#   else:
#     return n * fact(n-1)

