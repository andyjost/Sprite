import cytest # from ./lib; must be first
from curry.backends.py.graph.indexing import (
    logical_subexpr, realpath, subexpr
  )
from curry.expressions import fwd, _setgrd
from curry import inspect
from six.moves import reduce
import curry, unittest

out_of_range = curry.CurryIndexError(r'node index out of range')

def cross_check_realpath(expr, path, expected):
  '''
  Ensures that for any call to realpath, the returned path indexes to the
  target.
  '''
  # Only run the check if the expected result is a tuple.
  if isinstance(expected, tuple):
    tgt, rpath, _ = expected
    return subexpr(expr, rpath) is tgt
  else:
    return True

# Most of thest tests in this file are run twice, once for indexing.subexpr and
# again for indexing.realpath.  The common tests are defined in IndexingTests
# and inherted by test classes at the end of the file.

class IndexingTests(object):
  '''Tests code to index into Curry expressions.'''

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_bool(self):
    yield True, 0, out_of_range
    yield False, 0, out_of_range

  @cytest.check_indexing
  @cytest.check_predicate(cross_check_realpath)
  def test_index_int(self):
    yield 1, 0, 1  # Simple indexing reaches the unboxed value.
    yield 1, [0], 1
    yield 1, -1, 1
    yield 1, [-1], 1
    yield 1, 1, out_of_range
    yield 1, -2, out_of_range
    yield curry.unboxed(1), 0, out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_char(self):
    yield 'a', 0, 'a'  # Simple indexing reaches the unboxed value.
    yield 'a', [0], 'a'
    yield 'a', -1, 'a'
    yield 'a', [-1], 'a'
    yield 'a', 1, out_of_range
    yield 'a', -2, out_of_range
    yield curry.unboxed('a'), 0, out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_float(self):
    yield 1.0, 0, 1.0  # Simple indexing reaches the unboxed value.
    yield 1.0, [0], 1.0
    yield 1.0, -1, 1.0
    yield 1.0, [-1], 1.0
    yield 1.0, 1, out_of_range
    yield 1.0, -2, out_of_range
    yield curry.unboxed(1.0), 0, out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_algebraic(self):
    prelude = curry.import_('Prelude')
    e = curry.raw_expr([prelude.Just, 5])
    five = curry.raw_expr(5)
    yield e, 0, five
    yield e, [0], five
    yield e, -1, five
    yield e, [-1], five
    yield e, [0, 0], 5
    yield e, 1, out_of_range
    yield e, -2, out_of_range
    yield e, [0, 1], out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_list(self):
    e = curry.raw_expr([0, 1, [2, 3, [], [4]]])
    middle = curry.raw_expr([2, 3, [], [4]])
    bot = curry.raw_expr([4])
    yield e, (), e
    yield e, 0, curry.raw_expr(0)
    yield e, (1,0), curry.raw_expr(1)
    yield e, (1,1,0), middle
    yield e, (1,1,-2), middle
    yield e, (1,1,0,0), curry.raw_expr(2)
    yield e, (1,1,0,1,1,0), curry.raw_expr([])
    yield e, (1,1,0,1,1,1,0,0,0), 4
    yield e, iter((1,1,0,1,1,1,0,0,0)), 4
    def path():
      yield 1
      yield 1
      yield 0
    yield e, path(), middle
    yield e, 2, out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_tuple(self):
    e = curry.raw_expr((0, (1, 2), [3]))
    yield e, (), e
    yield e, 1, curry.raw_expr((1, 2))
    yield e, 2, curry.raw_expr([3])

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_string(self):
    e = curry.raw_expr('Hello, you!')
    yield e, (), e
    yield e, (1,1,1,1,0), curry.raw_expr('o')
    yield e, (1,1,1,1,0,0), 'o'

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_choice(self):
    e = curry.raw_expr(curry.expressions.choice(5, 'a', 'b'))
    yield e, 0, 5
    yield e, (0, 0), out_of_range
    yield e, 1, curry.raw_expr('a')
    yield e, (1, 0), 'a'
    yield e, 2, curry.raw_expr('b')

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_fail(self):
    e = curry.raw_expr(curry.fail)
    yield e, (), e
    yield e, 0, out_of_range

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_cyclical(self):
    cons, nil, ref = curry.cons, curry.nil, curry.ref
    e = curry.raw_expr(ref('a'), a=cons(0, ref('b')), b=cons(1, ref('a')))
    self.assertIs(subexpr(e, ()), e)
    yield e, (0,0), 0
    yield e, (1,0,0), 1
    yield e, (1,1,0,0), 0
    yield e, (1,1,1,0,0), 1

  def test_index_invalid(self):
    onetwo = curry.raw_expr([1,2])
    self.assertRaisesRegex(
        curry.CurryIndexError
      , r"node index must be an integer or sequence of integers, not 'str'"
      , lambda: subexpr(onetwo, 'foo')
      )

    self.assertRaisesRegex(
        curry.CurryTypeError
      , r"invalid Curry expression \[1, 2\]"
      , lambda: subexpr([1,2], 0)
      )

    self.assertRaisesRegex(
        curry.CurryIndexError
      , r"node index out of range"
      , lambda: subexpr(1, 0)
      )

    for badidx in [-3, 4]:
      self.assertRaisesRegex(
          curry.CurryIndexError
        , r"node index out of range"
        , lambda: subexpr(onetwo, badidx)
        )

    for badty, name in [
          (None, 'NoneType')
        , ('err', 'str')
        , (1.0, 'float')
        , ([0.], 'float')
        ]:
      self.assertRaisesRegex(
          curry.CurryIndexError
        , r"node index must be an integer or sequence of integers, not %r"
              % name
        , lambda: subexpr(onetwo, badty)
        )

# Note: many tests are inherited.
class TestIndex(IndexingTests, cytest.TestCase):
  '''Tests for indexing.index.'''
  INDEXER = staticmethod(subexpr)

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_fwd(self):
    e = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, (), e
    yield e, (0,0), curry.raw_expr(0)
    yield e, (0,0,0), 0
    yield e, (0,1), curry.raw_expr([fwd(1)])
    yield e, (0,1,0), curry.raw_expr(fwd(1))
    yield e, (0,1,0,0), curry.raw_expr(1)

  @unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_index_setgrd(self):
    e = curry.raw_expr(_setgrd(0, True))
    yield e, 0, 0
    yield e, 1, curry.raw_expr(True)


# Note: many tests are inherited.
class TestLogicalSubexpr(IndexingTests, cytest.TestCase):
  '''Tests for indexing.logical_subexpr.'''
  INDEXER = staticmethod(
      lambda *args: logical_subexpr(*args, update_fwd_nodes=False)
    )


class TestRealpathNoUFN(cytest.TestCase):
  '''Additional tests for indexing.realpath with update_fwd_nodes=False.'''
  INDEXER = staticmethod(
      lambda *args: realpath(*args, update_fwd_nodes=False)
    )

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_realpath_fwd(self):
    e = curry.raw_expr(fwd([0, fwd(1)]))
    e_copy = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, ()   , (curry.raw_expr([0, fwd(1)]), [0]      , set())
    yield e, (0,0), (0                      , [0,0,0]  , set())
    yield e, 1    , (curry.raw_expr([fwd(1)])   , [0,1]    , set())
    yield e, (1,0), (curry.raw_expr(1)          , [0,1,0,0], set())

    # Ensure indexing did not modify the expression.
    self.assertStructEqual(e, e_copy)

  @unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_realpath_setgrd(self):
    e = curry.raw_expr(_setgrd(0, True))
    true = curry.raw_expr(True)
    yield e, (), (true, [1], set([0]))
    self.assertStructEqual(subexpr(e, [1]), true)

    e = curry.raw_expr(_setgrd(0, _setgrd(1, _setgrd(0, True))))
    yield e, (), (true, [1,1,1], set([0,1]))
    self.assertStructEqual(subexpr(e, [1,1,1]), true)

  @unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_realpath_interleaved(self):
    '''Test interleaved forward nodes and set guards.'''
    e = curry.raw_expr(_setgrd(0, fwd(fwd(_setgrd(1, True)))))
    true = curry.raw_expr(True)
    yield e, (), (true, [1,0,0,1], set([0,1]))
    self.assertStructEqual(e, curry.raw_expr(_setgrd(0, fwd(fwd(_setgrd(1, True))))))


class TestRealpathUFN(cytest.TestCase):
  '''Additional tests for indexing.realpath with update_fwd_nodes=True.'''
  INDEXER = staticmethod(
      lambda *args: realpath(*args, update_fwd_nodes=True)
    )

  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_realpath_fwd(self):
    e = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, ()   , (curry.raw_expr([0, fwd(1)]), [0]     , set())
    self.assertIsaFwd(e)

    e = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, (0,0), (0                      , [0,0,0] , set())
    self.assertIsaFwd(e)

    e = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, 1    , (curry.raw_expr([1])        , [0, 1]  , set())
    self.assertIsaFwd(e)

    e = curry.raw_expr(fwd([0, fwd(1)]))
    yield e, (1,0), (curry.raw_expr(1)          , [0, 1,0], set())
    self.assertIsaFwd(e)

  def test_realpath_compress_fwd_chain1(self):
    '''Check that a chain beginning with a forward node is compressed.'''
    # Try the following with chains of various lengths.
    for N in range(2, 5):
      # Make a chain of N forward nodes: fwd(...fwd(-1)...)
      end = curry.raw_expr(-1)
      e = curry.raw_expr(reduce(lambda a,_: fwd(a), range(N), end))
      chain = [subexpr(e, [0]*i) for i in range(N)] # keep each link
      # Everything in the chain is a forward node.
      map(self.assertIsaFwd, chain)
      # Not all links point directly to the end.
      self.assertFalse(all(inspect.fwd_target(link) is end for link in chain))

      # Index with UFN=True.
      tgt, path, grds = realpath(e, (), update_fwd_nodes=True)
      self.assertStructEqual(tgt, end)
      self.assertStructEqual(subexpr(e, path), end)
      self.assertEqual(grds, set())
      # The head remains a FWD b/c we don't have its parent.
      self.assertStructEqual(e, curry.raw_expr(fwd(end)))
      # Now, every link is short-cut to the end.
      self.assertTrue(all(inspect.fwd_target(link) is end for link in chain))

  def test_realpath_compress_fwd_chain2(self):
    '''Checks that an embedded chain of forward nodes is compressed.'''
    # Check chains of various lengths.  Unlike the previous test, a node
    # is placed before the chain.  In this case, all forward nodes are
    # completely removed.
    prelude = curry.import_('Prelude')
    for head in [prelude.Just, prelude.id]: # try with a ctor and function
      for N in range(2, 5):
        # Make a chain of N forward nodes: fwd(...fwd(-1)...)
        end = curry.raw_expr(-1)
        e = curry.raw_expr([head, reduce(lambda a,_: fwd(a), range(N), end)])
        chain = [subexpr(e, [0]+[0]*i) for i in range(N)] # keep each link
        # Everything in the chain is a forward node.
        map(self.assertIsaFwd, chain)
        # Not all links point directly to the end.
        self.assertFalse(all(inspect.fwd_target(link) is end for link in chain))

        # Index with UFN=True.
        tgt, path, grds = realpath(e, 0, update_fwd_nodes=True)
        self.assertIs(tgt, end)
        self.assertIs(subexpr(e, path), end)
        self.assertEqual(grds, set())
        # Now, every link is short-cut to the end.
        self.assertTrue(all(inspect.fwd_target(link) is end for link in chain))
        # And there are no forward nodes at all in the expression.
        self.assertStructEqual(e, curry.raw_expr([head, -1]))

  @unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
  @cytest.check_predicate(cross_check_realpath)
  @cytest.check_indexing
  def test_realpath_interleaved(self):
    '''Test interleaved forward nodes and set guards.'''
    e = curry.raw_expr(_setgrd(0, fwd(fwd(_setgrd(1, True)))))
    true = curry.raw_expr(True)
    yield e, (), (true, [1,1], set([0,1]))
    self.assertStructEqual(e, curry.raw_expr(_setgrd(0, _setgrd(1, True))))

    e = curry.raw_expr(_setgrd(0, [fwd(fwd(_setgrd(1, fwd(True))))]))
    true = curry.raw_expr(True)
    yield e, 1, (curry.raw_expr([]), [1,1], set([0]))
    yield e, 0, (true, [1,0,1], set([0,1]))
    self.assertStructEqual(e, curry.raw_expr(_setgrd(0, [_setgrd(1, True)])))

