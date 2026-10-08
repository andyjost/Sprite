import cytest # from ./lib; must be first
import curry, unittest
from curry.expressions import (
    anchor, ref, _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding
  , free, fwd, choice, unboxed, cons, nil
  )
from curry import inspect
from curry.exceptions import CurryTypeError, EvaluationError
from curry.typecheck.errors import ConversionError

listiterator_name = type(iter([])).__name__

CLEAN_KWDS = {'standardize_floats': True, 'keep_spacing': True}
FLOAT_CLEANER = lambda s: cytest.clean.clean(s, **CLEAN_KWDS)
CXX = curry.flags['backend'] == 'cxx'

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
      , ([], r"\[\]")
      , ([0], r"\[0\]")
      , ((), r"\(\)")
      , ((0,1), r"\(0, 1\)")
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

  @cytest.check_expressions()
  def test_char(self):
    yield 'a', "'a'", "<Char 'a'>", 'a'

  @cytest.check_expressions(cleaner=FLOAT_CLEANER)
  def test_float(self):
    yield 1.2, '1.2', "<Float 1.2>", 1.2

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
    self.assertRegex(str(e), '_biGenerator')
    val = next(curry.eval(e))
    self.assertEqual(str(e), '[]')

    e = curry.raw_expr(iter([1,2]))
    self.assertRegex(str(e), '_biGenerator')
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

  @cytest.check_expressions()
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

  @unittest.skipIf(CXX, 'Cannot directly create C++ values sets')
  @cytest.check_expressions()
  def test_setgrd(self):
    yield _setgrd(1, True), '_SetGuard 1 True', '<_SetGuard 1 <True>>'

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
        _valuebinding(True, (free(1), 2))
      , '_ValueBinding True (_a, 2)'
      , '<_ValueBinding <True> <(,) <_Free 1 <()>> <Int 2>>>'
      )

  @cytest.check_expressions()
  def test_unboxed(self):
    # The marker is the payload of a primitive; see TestUnboxedMarker.
    prelude = curry.import_('Prelude')
    yield [prelude.Int, curry.unboxed(2)], '2', '<Int 2>', 2
    yield [prelude.Char, curry.unboxed('a')], "'a'", "<Char 'a'>", 'a'

  @cytest.check_expressions()
  def test_var(self):
    yield free(5), '_a', '<_Free 5 <()>>'

  @cytest.check_expressions()
  def test_nonlinear(self):
    # let a=1 in [a, a]
    e = curry.raw_expr([curry.expressions.anchor(1), curry.ref()])
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




class TestUnboxedMarker(cytest.TestCase):
  '''
  The place of curry.unboxed (issue #107).  The marker is the payload of a
  primitive, [Int, unboxed(3)].  Anywhere else both builders raise a
  CurryTypeError at construction, on both backends: the C++ backend
  dereferenced the raw value as a node and ended the process, and the
  Python backend built an ill-formed node.
  '''
  PLACE = (
      r'the marker is the payload of an Int, Char or Float, as in '
      r'\[Prelude\.Int, curry\.unboxed\(1\)\]'
    )

  def test_payload(self):
    '''As the payload of a primitive the marker works through both builders.'''
    P = curry.import_('Prelude')
    for build in (curry.expr, curry.raw_expr):
      e = build([P.Int, curry.unboxed(3)])
      self.assertEqual(repr(e), '<Int 3>')
      self.assertEqual(curry.topython(e), 3)
      self.assertEqual(repr(build(P.Char, curry.unboxed('a'))), "<Char 'a'>")
      self.assertEqual(curry.topython(build([P.Float, curry.unboxed(2.5)])), 2.5)
    self.assertEqual(curry.typeof(curry.expr([P.Int, curry.unboxed(3)])), 'Int')
    self.assertEqual(
        list(curry.eval([P.Int, curry.unboxed(3)], converter='topython')), [3]
      )

  def test_typed_builder(self):
    '''Alone, as an argument, in a list, in a tuple: an error that names the position.'''
    P = curry.import_('Prelude')
    cases = [
        ( (curry.unboxed(1),)
        , r'^curry\.unboxed\(1\) stands alone; ' + self.PLACE + '$'
        )
      , ( (P.id, curry.unboxed(1))
        , r'^curry\.unboxed\(1\) stands at argument 1 of Prelude\.id :: a -> a; '
          + self.PLACE + '$'
        )
      , ( ([curry.unboxed(1)],)
        , r'^curry\.unboxed\(1\) stands at element 1 of the list in the '
          r'expression; ' + self.PLACE + '$'
        )
      , ( ((curry.unboxed(1), 2),)
        , r'^curry\.unboxed\(1\) stands at component 1 of the tuple in the '
          r'expression; ' + self.PLACE + '$'
        )
      ]
    for args, regex in cases:
      with self.assertRaisesRegex(CurryTypeError, regex):
        curry.expr(*args)
      with self.assertRaisesRegex(CurryTypeError, regex):
        curry.typeof(curry.describe(*args))
      with self.assertRaisesRegex(CurryTypeError, regex):
        list(curry.eval(*args))
    # The message names the primitive of the payload.
    with self.assertRaisesRegex(
        CurryTypeError, r"as in \[Prelude\.Char, curry\.unboxed\('a'\)\]$"
      ):
      curry.expr(P.id, curry.unboxed('a'))
    with self.assertRaisesRegex(
        CurryTypeError, r'as in \[Prelude\.Float, curry\.unboxed\(2\.5\)\]$'
      ):
      curry.expr(P.Just, curry.unboxed(2.5))
    # The error is one of the catalogue and carries the position.
    with self.assertRaises(ConversionError) as cm:
      curry.expr(P.id, curry.unboxed(1))
    self.assertEqual(cm.exception.where, 'argument 1 of Prelude.id :: a -> a')
    self.assertEqual(cm.exception.value, 1)
    # A description holds the marker and prints it; typing it is the error.
    d = curry.describe(P.id, curry.unboxed(1))
    self.assertEqual(str(d), 'id 1')
    with self.assertRaisesRegex(CurryTypeError, 'stands at argument 1 of'):
      d.typeof()
    # Nothing is built: a target stays as it is.
    target = curry.expr(P.id, 0)
    with self.assertRaisesRegex(CurryTypeError, 'stands alone'):
      curry.expr(curry.unboxed(1), target=target)
    self.assertEqual(str(target), 'id 0')

  def test_untyped_builder(self):
    '''raw_expr, and expr with the typing off, raise too, without a position.'''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    regex = r'^curry\.unboxed\(1\) stands outside a primitive; ' + self.PLACE + '$'
    for args in [
        (curry.unboxed(1),), (P.id, curry.unboxed(1)), ([curry.unboxed(1)],)
      , ((curry.unboxed(1), 2),), (P.Just, [1, curry.unboxed(1)])
      ]:
      with self.assertRaisesRegex(CurryTypeError, regex):
        curry.raw_expr(*args)
      with self.assertRaisesRegex(CurryTypeError, regex):
        curry.expressions.untyped_expr(interp, *args)
    # The marker alone with a target is the same error, and the target stays.
    target = curry.raw_expr(P.id, 0)
    with self.assertRaisesRegex(CurryTypeError, regex):
      curry.raw_expr(curry.unboxed(1), target=target)
    self.assertEqual(str(target), 'id 0')
    # Trailing arguments are reported first, as for every marker.
    with self.assertRaisesRegex(CurryTypeError, 'invalid arguments after unboxed 1'):
      curry.raw_expr(curry.unboxed(1), True)

  def test_payload_type(self):
    '''A payload that does not fit its primitive is refused by both builders.'''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    cases = [
        ( P.Int, 2.5
        , r"curry\.unboxed\(2\.5\) is not the payload of an Int%s; the payload "
          r"of an Int is a Python int, as in \[Prelude\.Int, curry\.unboxed\(3\)\]$"
        )
      , (P.Int, 'a', r"curry\.unboxed\('a'\) is not the payload of an Int%s; ")
      , (P.Int, True, r"curry\.unboxed\(True\) is not the payload of an Int%s; ")
      , ( P.Float, 1
        , r"curry\.unboxed\(1\) is not the payload of a Float%s; the payload of "
          r"a Float is a Python float, as in \[Prelude\.Float, curry\.unboxed\(2\.5\)\]$"
        )
      , (P.Float, 'a', r"curry\.unboxed\('a'\) is not the payload of a Float%s; ")
      , ( P.Char, 1
        , r"curry\.unboxed\(1\) is not the payload of a Char%s; the payload of "
          r"a Char is a str of length one, as in \[Prelude\.Char, curry\.unboxed\('a'\)\]$"
        )
      , (P.Char, 'ab', r"curry\.unboxed\('ab'\) is not the payload of a Char%s; ")
      , (P.Char, 2.5, r"curry\.unboxed\(2\.5\) is not the payload of a Char%s; ")
      ]
    for prim, value, regex in cases:
      # The typed builder names the position of the primitive.
      with self.assertRaisesRegex(ConversionError, '^' + regex % ' at the expression'):
        curry.expr([prim, curry.unboxed(value)])
      with self.assertRaisesRegex(
          ConversionError, '^' + regex % r' at argument 1 of Prelude\.id :: a -> a'
        ):
        curry.expr(P.id, [prim, curry.unboxed(value)])
      with self.assertRaisesRegex(
          ConversionError
        , '^' + regex % r' at element 1 of the list in the expression'
        ):
        curry.typeof(curry.describe([[prim, curry.unboxed(value)]]))
      # The untyped builder has no position.
      with self.assertRaisesRegex(CurryTypeError, '^' + regex % ''):
        curry.raw_expr([prim, curry.unboxed(value)])
      with self.assertRaisesRegex(CurryTypeError, '^' + regex % ''):
        curry.expressions.untyped_expr(interp, P.id, [prim, curry.unboxed(value)])
    with self.assertRaises(ConversionError) as cm:
      curry.expr(P.Just, [P.Int, curry.unboxed(2.5)])
    self.assertEqual(cm.exception.where, 'argument 1 of Prelude.Just :: a -> Maybe a')
    self.assertEqual(cm.exception.value, 2.5)
    # A description prints the payload; typing it is the error.
    d = curry.describe([P.Int, curry.unboxed(2.5)])
    self.assertEqual(str(d), '2.5')
    with self.assertRaisesRegex(ConversionError, 'is not the payload of an Int'):
      d.typeof()
    # The range of Int is checked where the node is made, on both backends.
    with self.assertRaisesRegex(CurryTypeError, 'outside the range of Int'):
      curry.expr([P.Int, curry.unboxed(2 ** 64)])
    with self.assertRaisesRegex(CurryTypeError, 'outside the range of Int'):
      curry.raw_expr([P.Int, curry.unboxed(2 ** 64)])

  def test_iterator(self):
    '''An item of an iterator converts when the list is demanded: the error names the marker.'''
    P = curry.import_('Prelude')
    self.assertEqual(repr(curry.unboxed(1)), 'curry.unboxed(1)')
    self.assertEqual(repr(curry.unboxed('a')), "curry.unboxed('a')")
    # The construction passes: the items are not read yet.
    e = curry.expr(P.length, iter([curry.unboxed(1), curry.unboxed(2)]))
    with self.assertRaisesRegex(
        EvaluationError
      , r'^cannot convert item curry\.unboxed\(1\) of the iterator at argument 1 '
        r'of Prelude\.length :: \[a\] -> Int to a$'
      ):
      list(curry.eval(e))
    with self.assertRaisesRegex(EvaluationError, r'cannot convert item curry\.unboxed\(1\)'):
      list(curry.eval(P.length, iter([curry.unboxed(1)])))


class TestSurplusArguments(cytest.TestCase):
  '''
  A symbol applied to more arguments than its arity (issue #63).  A function
  may return a function, as a point-free definition does: the surplus goes
  through Prelude.apply in the untyped builder, as it does in the typed one.
  A constructor applied to a surplus is an error, and so is a node made with
  a count other than the arity, on both backends.
  '''
  @classmethod
  def setUpClass(cls):
    cls.M = curry.compile(
        '''
        norm :: Int -> Int
        norm = (+ 1) . (* 2)

        twice :: (a -> a) -> a -> a
        twice f = f . f
        '''
      , modulename='PointFree63'
      )

  def values(self, *args):
    return list(curry.eval(*args, converter='topython'))

  def test_point_free(self):
    M = self.M
    e = curry.raw_expr(M.norm, 3)
    self.assertEqual(str(e), 'apply norm 3')
    self.assertEqual(self.values(e), [7])
    e = curry.raw_expr(M.twice, M.norm, 3)
    self.assertEqual(str(e), 'apply (twice norm) 3')
    self.assertEqual(self.values(e), [15])
    # Two surplus arguments: one apply per argument.
    e = curry.raw_expr(M.twice, M.twice, M.norm, 3)
    self.assertEqual(str(e), 'apply (apply (twice twice) norm) 3')
    self.assertEqual(self.values(e), [63])
    # The typed builder, and so curry.eval, take the same route.
    self.assertEqual(str(curry.expr(M.norm, 3)), 'apply norm 3')
    self.assertEqual(self.values(M.norm, 3), [7])
    self.assertEqual(self.values(M.twice, M.norm, 3), [15])

  def test_constructor_surplus(self):
    '''Both builders refuse the surplus with one sentence form.'''
    P = curry.import_('Prelude')
    with self.assertRaises(CurryTypeError) as cm:
      curry.raw_expr(P.Just, 1, 2)
    self.assertEqual(str(cm.exception), 'Just takes 1 argument, 2 given')
    with self.assertRaisesRegex(CurryTypeError, 'takes 1 argument, 2 given'):
      curry.expr(P.Just, 1, 2)
    with self.assertRaises(CurryTypeError) as cm:
      curry.raw_expr(P.Nothing, 1)
    self.assertEqual(str(cm.exception), 'Nothing takes 0 arguments, 1 given')

  def test_node_count(self):
    '''A node is made with the count of its arity, on both backends.'''
    P = curry.import_('Prelude')
    backend = curry.getInterpreter().backend
    make = backend.make_node
    partial = backend.fundamental_symbols.PartApplic
    one = curry.raw_expr(1)
    with self.assertRaisesRegex(
        TypeError, r"cannot construct 'Just' \(arity=1\), with 2 args"
      ):
      make(P.Just, one, one)
    with self.assertRaisesRegex(
        TypeError, r"cannot construct 'Just' \(arity=1\), with 0 args"
      ):
      make(P.Just)
    with self.assertRaisesRegex(
        TypeError, r"cannot curry 'Just' \(arity=1\), with 1 arg"
      ):
      make(P.Just, one, partial_info=partial)
    self.assertEqual(str(make(P.Just, one)), 'Just 1')
    self.assertEqual(str(make(P.Just, partial_info=partial)), 'Just')
