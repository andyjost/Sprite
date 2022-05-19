import cytest # from ./lib; must be first
import curry
from curry.expressions import (
    anchor, ref, _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding
  , free, fwd, choice, unboxed, cons, nil
  )
from curry import inspect
from curry.exceptions import CurryTypeError

listiterator_name = type(iter([])).__name__

CLEAN_KWDS = {'standardize_floats': True, 'keep_spacing': True}
FLOAT_CLEANER = lambda s: cytest.clean.clean(s, **CLEAN_KWDS)

class TestExpr(cytest.TestCase):
  '''Tests expression-building with ``curry.raw_expr``.'''

  def test_negative(self):
    # A bunch of things that cannot accept trailing arguments in curry.raw_expr.
    for (before, what) in [
        (True, 'True')
      , (1, '1')
      , (1.0, '1.0')
      , ('a', "'a'")
      , ('hello', "'hello'")
      , ([], "\[\]")
      , ([0], "\[0\]")
      , ((), "\(\)")
      , ((0,1), "\(0, 1\)")
      , (anchor(0), "anchor '_1'")
      , (anchor(0, name='a'), "anchor 'a'")
      , (ref('a'), "ref 'a'")
      , (iter([1,2]), r'\<%s object at 0x\w+\>' % listiterator_name)
      , (curry.raw_expr(0), r"'Int' node")
      , (unboxed(0), r'unboxed 0')
      , (cons(0, []), r"'cons'")
      , (nil, r"'nil'")
      , (_setgrd(0, True), "'_setgrd'")
      , (fail, "'fail'")
      , (_strictconstr(0, (free(0), free(1))), "'_strictconstr'")
      , (_nonstrictconstr(0, (free(0), free(1))), "'_nonstrictconstr'")
      , (_valuebinding(0, (free(0), 1)), "'_valuebinding'")
      , (free(0), "'free'")
      , (fwd(0), "'fwd'")
      , (choice(0, 1), "'choice'")
      ]:
      self.assertRaisesRegex(
          CurryTypeError, r'invalid arguments after %s' % what
        , lambda: curry.raw_expr(before, True)
        )

  @cytest.check_expressions()
  def test_bool(self):
    yield True, 'True', '<True>', True
    yield False, 'False', '<False>', False

  @cytest.check_expressions()
  def test_int(self):
    yield 1, '1', '<Int 1>', 1
    yield curry.unboxed(1), '1', '1', 1

  @cytest.check_expressions()
  def test_char(self):
    yield 'a', "'a'", "<Char 'a'>", 'a'
    yield curry.unboxed('a'), 'a', "'a'", 'a'

  @cytest.check_expressions(cleaner=FLOAT_CLEANER)
  def test_float(self):
    yield 1.2, '1.2', "<Float 1.2>", 1.2
    yield curry.unboxed(1.0), '1.0', '1.0', 1.0

  @cytest.check_expressions()
  def test_nodeinfo(self):
    prelude = curry.import_('Prelude')
    yield [prelude.Just, 5], 'Just 5', '<Just <Int 5>>'
    yield [prelude.id, [prelude.Just, 5]], 'id (Just 5)', '<id <Just <Int 5>>>'

  @cytest.check_expressions()
  def test_list(self):
    yield [], '[]', '<[]>', []
    yield [True], '[True]', '<: <True> <[]>>', [True]
    yield [0,1,2], '[0, 1, 2]', '<: <Int 0> <: <Int 1> <: <Int 2> <[]>>>>', [0,1,2]

  @cytest.check_expressions()
  def test_cons(self):
    yield curry.nil, '[]', '<[]>', []
    yield curry.cons(0, curry.nil), '[0]', '<: <Int 0> <[]>>', [0]
    yield curry.cons(0, 1, curry.nil), '[0, 1]', '<: <Int 0> <: <Int 1> <[]>>>', [0, 1]

  def test_iterators(self):
    '''Python iterators become lazy lists in Curry.'''
    e = curry.raw_expr(iter([]))
    self.assertRegex(str(e), '_PyGenerator')
    val = next(curry.eval(e))
    self.assertEqual(str(e), '[]')

    e = curry.raw_expr(iter([1,2]))
    self.assertRegex(str(e), '_PyGenerator')
    val = curry.topython(next(curry.eval(e)))
    self.assertEqual(val, [1, 2])

  @cytest.check_expressions()
  def test_tuple(self):
    yield (), '()', '<()>', ()
    yield (1,2), '(1, 2)', '<(,) <Int 1> <Int 2>>', (1,2)

    self.assertRaisesRegex(
        TypeError
      , r'Curry has no 1-tuple'
      , lambda: curry.raw_expr((1,))
      )

  @cytest.check_expressions()
  def test_str(self):
    yield '', '[]', "<[]>", []  # empty string and list are indistiguishable
    yield 'hi', '"hi"', "<: <Char 'h'> <: <Char 'i'> <[]>>>", 'hi'

  def test_choice(self):
    yield choice(1, True, False), '_Choice 1 True False' \
                                , '<_Choice 1 <True> <False>>' \
                                , None \
                                , sorted([True, False])

  def test_fail(self):
    e = curry.raw_expr(fail)
    self.assertEqual(str(e), 'failed')
    self.assertEqual(list(curry.eval(e)), [])

  @cytest.check_expressions()
  def test_fwd(self):
    yield fwd(1), '1', "<_Fwd <Int 1>>"

  @cytest.check_expressions()
  def test_nonstrictconstr(self):
    yield (
        _nonstrictconstr(True, (free(1), False))
      , '_NonStrictConstraint True (_a, False)'
      , '<_NonStrictConstraint <True> <(,) <_Free 1 <()>> <False>>>'
      )

  @cytest.check_expressions()
  def test_setgrd(self):
    yield (
        _setgrd(1, True)
      , '_SetGuard 1 True'
      , '<_SetGuard 1 <True>>'
      )

  @cytest.check_expressions()
  def test_strictconstr(self):
    yield (
        _strictconstr(True, (free(1), free(2)))
      , '_StrictConstraint True (_a, _b)'
      , '<_StrictConstraint <True> <(,) <_Free 1 <()>> <_Free 2 <()>>>>'
      )

  @cytest.check_expressions()
  def test_valuebinding(self):
    yield (
        _valuebinding(True, (free(1), curry.unboxed(2)))
      , '_ValueBinding True (_a, 2)'
      , '<_ValueBinding <True> <(,) <_Free 1 <()>> 2>>'
      )

  @cytest.check_expressions()
  def test_var(self):
    yield free(5), '_a', '<_Free 5 <()>>'

  def test_nonlinear(self):
    # let a=1 in [a, a]
    e = curry.raw_expr([curry.anchor(1), curry.ref()])
    a, b = e[0], e[1][0]
    self.assertEqual(id(a), id(b))
    yield e, None, None, None, [[1, 1]]

  @cytest.check_expressions()
  def test_circular(self):
    anchor, ref = curry.expressions.anchor, curry.ref

    # let a=a in a
    e = curry.raw_expr(anchor(ref()))
    self.assertIsaFwd(e)
    also_e = inspect.fwd_target(e)
    self.assertIs(e, also_e)
    yield e, '...', '<_Fwd ...>'
    #
    e = curry.raw_expr(ref('a'), a=ref('a'))
    self.assertIsaFwd(e)
    also_e = inspect.fwd_target(e)
    self.assertIs(e, also_e)
    yield e, '...', '<_Fwd ...>'

    # let a=[a] in a
    e = curry.raw_expr(anchor([ref()]))
    self.assertEqual(id(e), id(e[0]))
    yield e, '[...]', '<: ... <[]>>'
    #
    exprs = {'a': [ref('a')]}
    e = curry.raw_expr(ref('a'), **exprs)
    self.assertEqual(id(e), id(e[0]))
    yield e, '[...]', '<: ... <[]>>'

  @cytest.check_expressions()
  def test_named_anchor1(self):
    '''Test named anchors using a direct style.'''
    # let a=(0:b), b=(1:a) in take 5 a
    prelude = curry.import_('Prelude')
    anchor, cons, ref = curry.expressions.anchor, curry.cons, curry.ref
    b = anchor(cons(1, ref('a')), name='b')
    a = anchor(cons(0, b), name='a')
    e = curry.raw_expr(prelude.take, 5, a)
    A = e[1]
    B = A[1]
    self.assertEqual(id(A), id(B[1]))
    yield e, None, None, None, [[0, 1, 0, 1, 0]]

  @cytest.check_expressions()
  def test_named_anchor2(self):
    '''Test named anchors using keyword style.'''
    # let a=(0:b), b=(1:a) in take 5 a
    prelude = curry.import_('Prelude')
    cons, ref = curry.cons, curry.ref
    exprs = {
        'a': cons(0, ref('b'))
      , 'b': cons(1, ref('a'))
      }
    e = curry.raw_expr(prelude.take, 5, ref('a'), **exprs)
    A = e[1]
    B = A[1]
    self.assertEqual(id(A), id(B[1]))
    yield e, 'take 5 [0, 1, ...]' \
           , '<take <Int 5> <: <Int 0> <: <Int 1> ...>>>' \
           , None \
           , [[0, 1, 0, 1, 0]]

    # Make sure the value of each keyword argument is interpreted as expected.
    exprs = {
        'a': 5
      , 'b': [5]
      , 'c': [prelude.Just, []]
      }
    e = curry.raw_expr((ref('a'), ref('b'), ref('c')), **exprs)
    yield e, '(5, [5], Just [])' \
           , '<(,,) <Int 5> <: <Int 5> <[]>> <Just <[]>>>'


