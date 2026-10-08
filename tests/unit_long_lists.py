'''
List functions over long lists (issue #62).

The Python backend evaluates a nested step by a recursive Python call: hnf
calls the step of the redex, which calls hnf on its inductive argument.  A
function that is not tail recursive, length (length (_:xs) = 1 + length xs)
or sort, nests one such call per element, about eight Python frames each.
The flag recursion_limit bounds the frames of one value: 262144 by default,
which covers a list of about thirty thousand elements under length; the
former limit of 16384 frames ended length over about two thousand elements
with RecursionError.  The C++ backend has no such limit below its
stack_limit.
'''
import cytest # from ./lib; must be first
import curry, unittest

PY = curry.flags['backend'] == 'py'
N = 10000
# The size of the long list.  In the stress mode of the collector
# (SPRITE_GC_STRESS=1) a collection follows every rewrite step and marks the
# whole list, so length costs the square of the size and sort more: ten
# thousand elements take about three minutes on the C++ backend, two
# thousand about eight seconds.  The property holds at either size.  The
# Python backend has no such collector and keeps ten thousand: that size is
# the subject of issue #62 there.
LONG = 2000 if cytest.GC_STRESS and not PY else N

def values(*args):
  return list(curry.eval(*args, converter='topython'))

class TestLongLists(cytest.TestCase):
  @cytest.timeout(120)
  def test_length_and_sort(self):
    '''
    length and sort over ten thousand elements, on both backends; over two
    thousand on the C++ backend in the stress mode of the collector.
    '''
    P = curry.import_('Prelude')
    DL = curry.import_('Data.List')
    self.assertEqual(values(P.length, list(range(LONG))), [LONG])
    self.assertEqual(
        values(DL.sort, list(range(LONG, 0, -1))), [list(range(1, LONG + 1))]
      )

  def test_length_below_the_limit(self):
    '''A list of a thousand elements works on both backends.'''
    P = curry.import_('Prelude')
    self.assertEqual(values(P.length, list(range(1000))), [1000])

  @unittest.skipUnless(PY, 'the recursion limit belongs to the Python backend')
  @cytest.with_flags(recursion_limit=1 << 14)
  @cytest.timeout(60)
  def test_recursion_limit_flag(self):
    '''
    The flag bounds the frames of one value: under the former limit the list
    of ten thousand elements ends with RecursionError, and a thousand pass.
    '''
    self.assertEqual(curry.flags['recursion_limit'], 1 << 14)
    P = curry.import_('Prelude')
    with self.assertRaises(RecursionError):
      values(P.length, list(range(N)))
    self.assertEqual(values(P.length, list(range(1000))), [1000])

if __name__ == '__main__':
  unittest.main()
