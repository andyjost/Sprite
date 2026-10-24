'''List functions over long lists (issue #62), bounded by stack_limit.'''
import cytest # from ./lib; must be first
import curry, unittest

N = 10000
# The size of the long list.  In the stress mode of the collector
# (SPRITE_GC_STRESS=1) a collection follows every rewrite step and marks the
# whole list, so length costs the square of the size and sort more: ten
# thousand elements take about three minutes on the C++ backend, two
# thousand about eight seconds.  The property holds at either size.
LONG = 2000 if cytest.GC_STRESS else N

def values(*args):
  return list(curry.eval(args[0](*args[1:]) if len(args) > 1 else args[0]))

class TestLongLists(cytest.TestCase):
  @cytest.timeout(120)
  def test_length_and_sort(self):
    '''
    length and sort over ten thousand elements; over two thousand in
    the stress mode of the collector.
    '''
    P = curry.import_('Prelude')
    DL = curry.import_('Data.List')
    self.assertEqual(values(P.length, list(range(LONG))), [LONG])
    self.assertEqual(
        values(DL.sort, list(range(LONG, 0, -1))), [list(range(1, LONG + 1))]
      )

  def test_length_below_the_limit(self):
    '''A list of a thousand elements works.'''
    P = curry.import_('Prelude')
    self.assertEqual(values(P.length, list(range(1000))), [1000])


if __name__ == '__main__':
  unittest.main()
