import cytest # from ./lib; must be first
import curry
from curry.backends.py.runtime.graph import indexing

out_of_range = curry.CurryIndexError(r'node index out of range')

class TestIndex(cytest.TestCase):
  '''Tests code to index into Curry expressions.'''
  CHECKER = cytest.check_indexing(indexer=indexing.index)

  @CHECKER
  def test_index_bool(self):
    yield True, 0, out_of_range
    yield False, 0, out_of_range

  @CHECKER
  def test_index_int(self):
    yield 1, 0, 1  # Simple indexing reaches the unboxed value.
    yield 1, [0], 1
    yield 1, -1, 1
    yield 1, [-1], 1
    yield 1, 1, out_of_range
    yield 1, -2, out_of_range
    yield curry.unboxed(1), 0, out_of_range

  @CHECKER
  def test_index_char(self):
    yield 'a', 0, 'a'  # Simple indexing reaches the unboxed value.
    yield 'a', [0], 'a'
    yield 'a', -1, 'a'
    yield 'a', [-1], 'a'
    yield 'a', 1, out_of_range
    yield 'a', -2, out_of_range
    yield curry.unboxed('a'), 0, out_of_range

  @CHECKER
  def test_index_float(self):
    yield 1.0, 0, 1.0  # Simple indexing reaches the unboxed value.
    yield 1.0, [0], 1.0
    yield 1.0, -1, 1.0
    yield 1.0, [-1], 1.0
    yield 1.0, 1, out_of_range
    yield 1.0, -2, out_of_range
    yield curry.unboxed(1.0), 0, out_of_range

  @CHECKER
  def test_index_algebraic(self):
    prelude = curry.import_('Prelude')
    e = curry.expr([prelude.Just, 5])
    five = curry.expr(5)
    yield e, 0, five
    yield e, [0], five
    yield e, -1, five
    yield e, [-1], five
    yield e, [0, 0], 5
    yield e, 1, out_of_range
    yield e, -2, out_of_range
    yield e, [0, 1], out_of_range

  @CHECKER
  def test_index_list(self):
    e = curry.expr([0, 1, [2, 3, [], [4]]])
    middle = curry.expr([2, 3, [], [4]])
    bot = curry.expr([4])
    yield e, (), e
    yield e, 0, curry.expr(0)
    yield e, (1,0), curry.expr(1)
    yield e, (1,1,0), middle
    yield e, (1,1,-2), middle
    yield e, (1,1,0,0), curry.expr(2)
    yield e, (1,1,0,1,1,0), curry.expr([])
    yield e, (1,1,0,1,1,1,0,0,0), 4
    yield e, iter((1,1,0,1,1,1,0,0,0)), 4
    def path():
      yield 1
      yield 1
      yield 0
    yield e, path(), middle
    yield e, 2, out_of_range

  @CHECKER
  def test_index_tuple(self):
    e = curry.expr((0, (1, 2), [3]))
    yield e, (), e
    yield e, 1, curry.expr((1, 2))
    yield e, 2, curry.expr([3])

  @CHECKER
  def test_index_string(self):
    e = curry.expr('Hello, you!')
    yield e, (), e
    yield e, (1,1,1,1,0), curry.expr('o')
    yield e, (1,1,1,1,0,0), 'o'

  @CHECKER
  def test_index_choice(self):
    e = curry.expr(curry.expressions.choice(5, 'a', 'b'))
    yield e, 0, 5
    yield e, (0, 0), out_of_range
    yield e, 1, curry.expr('a')
    yield e, (1, 0), 'a'
    yield e, 2, curry.expr('b')

  @CHECKER
  def test_index_fail(self):
    e = curry.expr(curry.fail)
    yield e, (), e
    yield e, 0, out_of_range

  @CHECKER
  def test_index_fwd(self):
    fwd = curry.expressions.fwd
    e = curry.expr(fwd([0, fwd(1)]))
    yield e, (), e
    yield e, (0,0), curry.expr(0)
    yield e, (0,0,0), 0
    yield e, (0,1), curry.expr([fwd(1)])
    yield e, (0,1,0), curry.expr(fwd(1))
    yield e, (0,1,0,0), curry.expr(1)

  @CHECKER
  def test_index_setgrd(self):
    e = curry.expr(curry.expressions._setgrd(0, True))
    yield e, 0, 0
    yield e, 1, curry.expr(True)

  @CHECKER
  def test_index_cyclical(self):
    cons, index, nil, ref = curry.cons, indexing.index, curry.nil, curry.ref
    e = curry.expr(ref('a'), a=cons(0, ref('b')), b=cons(1, ref('a')))
    self.assertIs(index(e, ()), e)
    yield e, (0,0), 0
    yield e, (1,0,0), 1
    yield e, (1,1,0,0), 0
    yield e, (1,1,1,0,0), 1

  def test_index_invalid(self):
    onetwo = curry.expr([1,2])
    self.assertRaisesRegexp(
        curry.CurryIndexError
      , r"node index must be an integer or sequence of integers, not 'str'"
      , lambda: indexing.index(onetwo, 'foo')
      )

    self.assertRaisesRegexp(
        curry.CurryTypeError
      , r"invalid Curry expression \[1, 2\]"
      , lambda: indexing.index([1,2], 0)
      )

    self.assertRaisesRegexp(
        curry.CurryIndexError
      , r"node index out of range"
      , lambda: indexing.index(1, 0)
      )

    for badidx in [-3, 4]:
      self.assertRaisesRegexp(
          curry.CurryIndexError
        , r"node index out of range"
        , lambda: indexing.index(onetwo, badidx)
        )

    for badty, name in [
          (None, 'NoneType')
        , ('err', 'str')
        , (1.0, 'float')
        , ([0.], 'float')
        ]:
      self.assertRaisesRegexp(
          curry.CurryIndexError
        , r"node index must be an integer or sequence of integers, not %r"
              % name
        , lambda: indexing.index(onetwo, badty)
        )
