import cytest # from ./lib; must be first
from collections import OrderedDict
from curry.utility.proptree import proptree

class PropertyTree(cytest.TestCase):
  def test_proptree(self):
    self.assertRaisesRegexp(
        TypeError, r"key 'a.b' cannot be created at 'b'"
      , lambda: proptree(OrderedDict([('a',0), ('a.b',1)]))
      )
    self.assertRaisesRegexp(
        TypeError, r"key 'a.b' cannot be created at 'b'"
      , lambda: proptree(OrderedDict([('a.b.c',0), ('a.b',1)]))
      )
    self.assertIs(proptree(None), None)
    self.assertIs(proptree(1), 1)

    pt = proptree({'a.b.a':0, 'a.b.b':1, 'a.b.c':2, 'b.a':3, 'a.a':4})
    self.assertIs(proptree(pt), pt)

    # __str__.
    self.assertEqual(str(pt), '[a=[a=4,b=[a=0,b=1,c=2]],b=[a=3]]')

    # Attribute read.
    self.assertEqual(pt.a.b.a, 0)
    self.assertEqual(pt.a.b.b, 1)
    self.assertEqual(pt.a.b.c, 2)
    self.assertEqual(pt.b.a, 3)
    self.assertEqual(pt.a.a, 4)

    # Assignment.
    pt.a.a = 42
    self.assertEqual(pt.a.a, 42)
    with self.assertRaisesRegexp(
        AttributeError, r"'proptreenode_a_b' object has no attribute 'x'"
      ):
      pt.a.x = None

    # __contains__.
    self.assertIn('a', pt)
    self.assertIn('b', pt)
    self.assertNotIn('c', pt)
    self.assertIn('a', pt.a)
    self.assertIn('b', pt.a)
    self.assertNotIn('c', pt.a)
    self.assertIn('a', pt.a.b)
    self.assertIn('b', pt.a.b)
    self.assertIn('c', pt.a.b)
    self.assertNotIn('d', pt.a.b)
    #
    self.assertIn('a.b.c', pt)
    self.assertNotIn('a.x.c', pt)

    # __iter__.
    self.assertEqual(list(pt), ['a','b'])
    self.assertEqual(list(pt.a.b), ['a','b','c'])

    # __getitem__.
    self.assertEqual(pt['a'], pt.a)
    self.assertRaisesRegexp(KeyError, "'x'", lambda: pt.a['x'])

    # get.
    self.assertEqual(pt.get('a.b.a'), 0)
    self.assertEqual(pt.get('a.b.a', 10), 0)
    self.assertIs(pt.get('a.FOO'), None)
    self.assertEqual(pt.get('a.FOO', 10), 10)

    # __setitem__.
    pt.a['a'] = 97
    self.assertEqual(pt.a.a, 97)
    with self.assertRaisesRegexp(KeyError, "'x'"):
      pt.a['x'] = None
    with self.assertRaisesRegexp(KeyError, "'a.x'"):
      pt['a.x'] = None

    # Equality.
    x = proptree({'a':0})
    x2 = proptree({'a':0})
    y = proptree({'a':1})
    z = proptree({'b':0})
    self.assertEqual(x, x2)
    self.assertNotEqual(x, y)
    self.assertNotEqual(x, z)
