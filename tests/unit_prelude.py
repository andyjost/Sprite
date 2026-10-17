import cytest # from ./lib; must be first
from curry.backends.py.graph import Node, equality
from curry import config, inspect
import curry, cytest.step, sys, unittest

def cells(e):
  '''The expression with every string argument as a list of characters.'''
  return [e[0]] + [list(a) if isinstance(a, str) else a for a in e[1:]]

class TestPrelude(cytest.TestCase):
  @property
  def constrEq(self):
    if config.syslibversion() < (3,3,0):
      return curry.import_('Prelude')['=:=']
    else:
      return curry.import_('Prelude')['constrEq']

  def testBuiltinPreludeTypes(self):
    '''
    Tests the built-in Prelude types and, indicentally, the ``isa`` function.
    '''
    e2s = lambda expr: str(next(cytest.raw.values(cytest.raw.expr(expr, typed=True))))

    # Int, Char, Float.
    Int = curry.import_('Prelude')['Int']
    Char = curry.import_('Prelude')['Char']
    Float = curry.import_('Prelude')['Float']
    int_ = next(cytest.raw.values(1))
    char_ = next(cytest.raw.values(curry.term(curry.Char('a'))))
    float_ = next(cytest.raw.values(1.))

    self.assertIsa(int_, Int)
    self.assertIsNotA(int_, Char)
    self.assertIsNotA(int_, Float)
    self.assertIsNotA(char_, Int)
    self.assertIsa(char_, Char)
    self.assertIsNotA(char_, Float)
    self.assertIsNotA(float_, Int)
    self.assertIsNotA(float_, Char)
    self.assertIsa(float_, Float)

    # List.
    Cons,Nil = curry.import_('Prelude')[':'], curry.import_('Prelude')['[]']
    self.assertEqual(e2s([Cons, 1, Nil]), '[1]')
    self.assertEqual(e2s([Cons, 1, [Cons, 2, Nil]]), '[1, 2]')
    l0 = Node(Nil)
    l1 = Node(Cons, 1, l0)
    self.assertIsa(l0, curry.import_('Prelude')['[]'])
    self.assertIsNotA(l0, curry.import_('Prelude')[':'])
    self.assertIsa(l0, curry.info(curry.import_('Prelude')).types['[]'])
    self.assertIsa(l1, curry.info(curry.import_('Prelude')).types['[]'])
    self.assertIsNotA(int_, curry.info(curry.import_('Prelude')).types['[]'])

    # Tuples.
    Unit = curry.import_('Prelude')['()']
    self.assertEqual(e2s([Unit]), '()')
    Pair = curry.import_('Prelude')['(,)']
    self.assertEqual(e2s([Pair, 1, 2]), '(1, 2)')
    T = curry.import_('Prelude')['(,,)']
    self.assertEqual(e2s([T, 1, 2, 3]), '(1, 2, 3)')
    T = curry.import_('Prelude')['(,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4]), '(1, 2, 3, 4)')
    T = curry.import_('Prelude')['(,,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5]), '(1, 2, 3, 4, 5)')
    T = curry.import_('Prelude')['(,,,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6]), '(1, 2, 3, 4, 5, 6)')
    T = curry.import_('Prelude')['(,,,,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7]), '(1, 2, 3, 4, 5, 6, 7)')
    T = curry.import_('Prelude')['(,,,,,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8]), '(1, 2, 3, 4, 5, 6, 7, 8)')
    T = curry.import_('Prelude')['(,,,,,,,,)']
    self.assertEqual(e2s([T, 1, 2, 3, 4, 5, 6, 7, 8, 9]), '(1, 2, 3, 4, 5, 6, 7, 8, 9)')

    # Bool.
    T,F = curry.import_('Prelude')['True'], curry.import_('Prelude')['False']
    self.assertEqual(e2s([Cons, T, [Cons, F, Nil]]), '[True, False]')

  def testLitParsers(self):
    # The primitives are called without the $## of their Prelude wrappers,
    # so the string must be in normal form already: a list of characters,
    # not the lazy string node the typed builder makes of a str.
    eval_ = lambda e: next(cytest.raw.values(cytest.raw.expr(cells(e), typed=True)))
    sym = lambda s: curry.import_('Prelude')[s]
    # Int
    self.assertEqual(eval_([sym('prim_readNatLiteral'), ['0']]), cytest.raw.expr([(0, "")]))
    self.assertEqual(eval_([sym('prim_readNatLiteral'), "123"]), cytest.raw.expr([(123, "")]))
    # Float
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.23"]), cytest.raw.expr([(1.23, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+1.23"]), cytest.raw.expr([(1.23, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "-1.23"]), cytest.raw.expr([(-1.23, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1."]), cytest.raw.expr([(1.0, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), ["1"]]), cytest.raw.expr([(1.0, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "+.9"]), cytest.raw.expr([(0.9, "")]))
    self.assertEqual(eval_([sym('prim_readFloatLiteral'), "1.2"]), cytest.raw.expr([(1.2, "")]))
    # Char
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'a'"]), cytest.raw.expr([('a', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\''"]), cytest.raw.expr([('\'', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\\'"]), cytest.raw.expr([('\\', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\''"]), cytest.raw.expr([('\'', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\\"'"]), cytest.raw.expr([('"', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\b'"]), cytest.raw.expr([('\b', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\f'"]), cytest.raw.expr([('\f', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\n'"]), cytest.raw.expr([('\n', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\r'"]), cytest.raw.expr([('\r', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\t'"]), cytest.raw.expr([('\t', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\v'"]), cytest.raw.expr([('\v', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\x41'"]), cytest.raw.expr([('A', "")]))
    self.assertEqual(eval_([sym('prim_readCharLiteral'), "'\\65'"]), cytest.raw.expr([('A', "")]))
    # String
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"A"''']), cytest.raw.expr([(['A'], "")]))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\x41\\66"''']), cytest.raw.expr([('AB', "")]))
    self.assertEqual(eval_([sym('prim_readStringLiteral'), '''"\\\\ \\' \\" \\b \\f \\n \\r \\t \\v"'''])
      , cytest.raw.expr([('\\ \' " \b \f \n \r \t \v', "")])
      )

  def testLitParsersBad(self):
    # The primitive read functions are over-specified in the Prelude.  They are
    # always matched against [(a, "")].  Upon a parse failure, a proper
    # implementation can either fail or produce a non-empty string.  Even this
    # should never occur because a lexer is used beforehand to ensure the input
    # is always valid.
    def assertNoGood(e):
      values = list(cytest.raw.values(cytest.raw.expr(cells(e), typed=True)))
      self.assertTrue(values == [] or cytest.raw.interp().topython(values[0][1]) == [])
    sym = lambda s: curry.import_('Prelude')[s]

    # Int
    assertNoGood([sym('prim_readNatLiteral'), '0foo'])
    assertNoGood([sym('prim_readNatLiteral'), "123 foo"])
    assertNoGood([sym('prim_readNatLiteral'), "-1"])
    # Float
    assertNoGood([sym('prim_readFloatLiteral'), "1.23 foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "+1.23 foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "-1.23 foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "1. foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "1foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "+.9 foo"])
    assertNoGood([sym('prim_readFloatLiteral'), "1.2.3"])
    # Char
    assertNoGood([sym('prim_readCharLiteral'), "'a'xx"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\\''xx"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\\\'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\''"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\\"'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\b'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\f'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\n'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\r'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\t'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\v'"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\x41'xx"])
    assertNoGood([sym('prim_readCharLiteral'), "'\\65'xx"])
    # String
    assertNoGood([sym('prim_readStringLiteral'), '''"A"xx'''])
    assertNoGood([sym('prim_readStringLiteral'), '''"\\x41\\66""xx'''])
    assertNoGood([sym('prim_readStringLiteral'), '''"\\\\ \\' \\" \\b \\f \\n \\r \\t \\v" tail'''])

  def testApply(self):
    '''
    A class method applied from Python.  Since Curry 3 a method is a
    selector of arity 1 whose parameter is the dictionary, so the typed
    builder supplies the dictionary of the instance and routes the value
    arguments through apply: apply (apply (+ dict) 1) 2.
    '''
    add = curry.import_('Prelude')['+']
    apply_ = curry.import_('Prelude')['apply']
    #
    e = cytest.raw.expr(add, 1, 2, typed=True)
    self.assertEqual(
        str(e), 'apply (apply ((+) _inst#Prelude.Num#Prelude.Int) 1) 2'
      )
    self.assertEqual(list(curry.eval(e)), [3])
    self.assertEqual(curry.typeof(e), 'Num a => a')
    self.assertEqual(curry.typeof(e, defaulted=True), 'Int')
    # The same expression spelled with apply.
    e = cytest.raw.expr(apply_, [apply_, add, 1], 2, typed=True)
    self.assertEqual(list(curry.eval(e)), [3])
    #
    incr = cytest.raw.expr(add, 1, typed=True)
    self.assertEqual(curry.typeof(incr, defaulted=True), 'Int -> Int')
    self.assertEqual(str(incr), 'apply ((+) _inst#Prelude.Num#Prelude.Int) 1')
    e = cytest.raw.expr(apply_, incr, 6, typed=True)
    self.assertEqual(list(curry.eval(e)), [7])

  def testFailed(self):
    failed = curry.import_('Prelude')['failed']
    self.assertEqual(len(list(curry.eval(failed))), 0)

  def testError(self):
    error = curry.import_('Prelude')['error']
    self.assertRaisesRegex(
        curry.EvaluationError
      , 'oops', lambda: next(curry.eval((error)("oops")))
      )

  def testOrd(self):
    ord_ = curry.import_('Prelude')['ord']
    self.assertEqual(list(curry.eval((ord_)(curry.Char('A')))), [65])
    # A Char is a code point.  The C++ backend stored a signed byte, so this
    # gave -96.
    chr_ = curry.import_('Prelude')['chr']
    self.assertEqual(list(curry.eval((ord_)(chr_(160)))), [160])
    self.assertEqual(list(curry.eval((ord_)(curry.Char('\u00e4')))), [228])
    self.assertEqual(list(curry.eval((ord_)(curry.Char('\U0001f600')))), [0x1f600])

  def testRound(self):
    '''round halves away from zero, as PAKCS and std::round do.'''
    round_ = curry.import_('Prelude')['round']
    cases = [
        (2.5, 3), (-2.5, -3), (0.5, 1), (-0.5, -1), (1.5, 2), (3.5, 4)
      , (2.4, 2), (-2.6, -3), (0.49999999999999994, 0), (1e15 + 0.5, 1000000000000001)
      ]
    for x, expected in cases:
      self.assertEqual(list(curry.eval((round_)(x))), [expected], x)

  def testChr(self):
    chr_ = curry.import_('Prelude')['chr']
    self.assertEqual(list(curry.eval((chr_)(65))), ['A'])
    self.assertEqual(list(curry.eval((chr_)(228))), ['\u00e4'])
    self.assertEqual(list(curry.eval((chr_)(0x1f600))), ['\U0001f600'])

  def testShowNonAscii(self):
    '''show writes a code point outside printable ASCII as a decimal escape.'''
    module = curry.compile(
        '''
        c :: String
        c = show '\\228'
        s :: String
        s = show "\\228\\246\\252"
        e :: String
        e = show (chr 128512)
        '''
      , modulename='ShowNonAscii'
      )
    self.assertEqual(list(curry.eval(module.c)), ["'\\228'"])
    self.assertEqual(list(curry.eval(module.s)), ['"\\228\\246\\252"'])
    self.assertEqual(list(curry.eval(module.e)), ["'\\128512'"])

  def testIsSpace(self):
    '''
    The ICurry text writes the non-breaking space in ``isSpace`` as the
    decimal escape '\\160'.  The committed JSON cache of the Prelude, built by
    an old reader, held '0' there, so ``isSpace '0'`` was true and
    ``read "0"`` failed on both backends.
    '''
    isSpace = curry.import_('Prelude')['isSpace']
    chr_ = curry.import_('Prelude')['chr']
    for char, expected in [
        ('0', False), ('1', False), ('9', False), ('a', False)
      , (' ', True), ('\t', True), ('\n', True)
      ]:
      self.assertEqual(list(curry.eval((isSpace)(curry.Char(char)))), [expected], char)
    self.assertEqual(list(curry.eval((isSpace)(chr_(160)))), [True])
    self.assertEqual(list(curry.eval((isSpace)(chr_(48)))), [False])

  def test_apply_nf(self):
    '''Test the $!! operator.'''
    # Ensure the RHS argument is normalized before the function is applied.
    interp = cytest.raw.interp()
    code = interp.compile(
        '''
        f :: Int -> Int
        f 0 = 1
        goal :: Int
        goal = id $!! (f 0)
        step2 :: Int
        step2 = id $!! 1
        '''
      )
    goal = interp.raw_expr(code.goal)
    step2 = interp.raw_expr(code.step2)
    cytest.step.step(interp, step2)
    cytest.step.step(interp, goal, num=2)
    self.assertEqual(goal, step2)

    # Ensure results are ungrounded.  The lifted variable of the text route
    # is a marker (curry.free) that its first step turns into the variable,
    # so the variable costs one step of the four.
    freevar = cytest.raw.expr(curry.parse('id $!! (x::Int) where x free'))
    cytest.step.step(interp, freevar, num=5)
    freevar = inspect.fwd_chain_target(freevar)
    self.assertIsaFreevar(freevar)

  def test_apply_nf_free_variable(self):
    '''
    A free variable is a normal form: ($!), ($!!) and normalForm give the
    variable, as PAKCS does, and ($##), which needs a ground normal form,
    suspends.  The C++ runtime suspended on all four; found when
    test_apply_nf started to run on the C++ backend.  ($!) suspended on
    both backends (issue #112).
    '''
    interp = cytest.raw.interp()
    for text in (
        'id $! (x::Int) where x free', 'id $!! (x::Int) where x free'
      , 'normalForm (x::Int) where x free'
      ):
      e = cytest.raw.expr(curry.parse(text))
      value, = cytest.raw.values(e)
      self.assertIsaFreevar(inspect.fwd_chain_target(value))
    e = cytest.raw.expr(curry.parse('id $## (x::Int) where x free'))
    self.assertRaises(
        curry.exceptions.EvaluationSuspended, lambda: list(curry.eval(e))
      )

  def test_strict_apply_choice(self):
    '''
    A choice or a failure in the argument of a strict application.  An audit
    finding: on the C++ backend, ($!) read a dead variable after hnf had
    pull-tabbed the choice to the root, and crashed; ($!!) and ($##) ran
    procN with the choice as its root and failed an assertion in pull_tab.
    '''
    for op in ['$!', '$!!', '$##']:
      goal = curry.parse('id %s ((1 :: Int) ? 2)' % op)
      self.assertEqual(sorted(curry.eval(goal)), [1, 2], op)
      goal = curry.parse('id %s (failed :: Int)' % op)
      self.assertEqual(list(curry.eval(goal)), [], op)

  def test_partial_application_value(self):
    '''
    A partial application is a value, and its arguments are not normalized.
    An audit finding: on the Python backend, a string literal inside it (a
    memoryview) stopped the copier that makes the value.
    '''
    goal = curry.parse('(++) "abc"')
    value, = cytest.raw.values(goal)
    apply = curry.import_('Prelude')['apply']
    self.assertEqual(
        list(curry.eval(cytest.raw.expr(apply, value, 'de', typed=True))), ['abcde']
      )

  # Used by testEqualityConstraint.
  def checkSatisfied(self, lhs, rhs):
    e = cytest.raw.expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [True])

  def checkUnsatisfied(self, lhs, rhs):
    e = cytest.raw.expr(self.constrEq, lhs, rhs)
    self.assertEqual(list(curry.eval(e)), [])

  def testEquationalConstraint(self):
    interp = cytest.raw.interp()
    # Note: a type dictionary is needed to call Prelude.unknown, but the type
    # is irrelevant for these tests.
    inst_unit = curry.import_('Prelude')['_inst#Prelude.Data#()']
    unknown = cytest.raw.expr([interp.prelude.unknown, inst_unit])

    # First, test with no free variable constraints.
    # builtin <=> builtin
    self.checkSatisfied(1, 1)
    self.checkUnsatisfied(0, 1)
    # ctor <=> ctor
    self.checkSatisfied([], [])
    self.checkSatisfied([0], [0])
    self.checkSatisfied([0,1], [0,1])
    self.checkSatisfied((0,1), (0,1))
    self.checkUnsatisfied([], [1])
    self.checkUnsatisfied([0], [1])
    self.checkUnsatisfied([0], [0,1])
    self.checkUnsatisfied((0,0), (0,1))

    # Now, test with free variable constraints.
    # free <=> free
    self.checkSatisfied(unknown, unknown)

    # builtin <=> free
    self.checkSatisfied(1, unknown)
    # free <=> builtin
    self.checkSatisfied(unknown, 0)

    # ctor <=> free
    self.checkSatisfied([], unknown)



class TestErrorMessage(cytest.TestCase):
  '''The message of ``error`` reaches the runtime in normal form.'''

  def test_error_message_is_normalized(self):
    # A module that runs interpreted at first (the tiered default of the C++
    # backend) resolves Prelude.error through the symbol table of the
    # compiled Prelude.  The primitive behind prim_error carried the display
    # name "error" and shadowed the function that normalizes the message, so
    # an unevaluated (++) reached the runtime ("bad Curry string").
    M = curry.compile('main = error ("A " ++ "b")', mode='module')
    with self.assertRaisesRegex(curry.EvaluationError, r'^A b'):
      list(curry.eval(M.main))

  @unittest.skipUnless(curry.flags['backend'] == 'cxx', 'C++ symbol tables')
  def test_primitives_carry_their_curry_names(self):
    self.assertEqual(curry.import_('Prelude')['prim_error'].info.name, 'prim_error')
    self.assertEqual(curry.import_('Prelude')['error'].info.name, 'error')
    self.assertEqual(
        curry.import_('Prelude')['prim_showIntLiteral'].info.name
      , 'prim_showIntLiteral'
      )
