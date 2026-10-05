import cytest # from ./lib; must be first
import curry, gc, unittest
from curry import inspect

class TestPyCompile(cytest.TestCase):
  '''Tests for curry.compile.'''
  def testIllegalProgram(self):
    self.assertRaisesRegex(
        curry.CompileError
      , '.x. is undefined'
      , lambda: curry.compile('f=x')
      )

  def testIllegalMode(self):
    self.assertRaisesRegex(
        TypeError
      , "expected mode 'module' or 'expr'"
      , lambda: curry.compile('goal=0', mode='foo')
      )

  def testModuleRedefined(self):
    curry.compile('goal=0', modulename='a')
    self.assertRaisesRegex(
        ValueError
      , "module 'a' is already defined"
      , lambda: curry.compile('goal=0', modulename='a')
      )

  def testMissingExternalConstructorDefinition(self):
    self.assertRaisesRegex(
        curry.CompileError
      , r"failed to resolve external type 'sprite__interactive_\d+\.A'"
      , lambda: curry.compile('data A')
      )

  @cytest.with_flags(defaultconverter='topython')
  def testCompileStringAsModule(self):
    '''Test dynamic module compilation.'''
    text = '''
      fib :: Int -> Int
      fib n | n < 3 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib = curry.compile(text).fib
    eight = curry.eval([fib, 6])
    self.assertEqual(next(eight), 8)

    # Compile another version (zero-based index this time).  Ensure each one
    # works independently.
    text2 = '''
      fib :: Int -> Int
      fib n | n < 2 = 1
            | True  = (fib (n-1)) + (fib (n-2))
    '''
    fib2 = curry.compile(text2).fib
    five = curry.eval([fib2, 4])
    self.assertEqual(next(five), 5)
    two = curry.eval([fib, 3])
    self.assertEqual(next(two), 2)

  @cytest.with_flags(defaultconverter='topython')
  def testCompileStringAsExpr(self):
    '''Test dynamic expression compilation.'''
    Or = curry.compile(
        '''
        or :: Int -> Int -> Int
        or 0 0 = 0
        or 1 0 = 1
        or 0 1 = 1
        or 1 1 = 1
        '''
      , modulename='Or'
      )
    e = curry.compile('Or.or 0 0', mode='expr', imports=[Or])
    self.assertEqual(next(curry.eval(e)), 0)
    e = curry.compile('Or.or 0 1', mode='expr', imports=[Or])
    self.assertEqual(next(curry.eval(e)), 1)

    # Check that ICurry-generated symbols are hidden.  There are multiple
    # symbols in .symbols, but only one at the top of the module.
    self.assertGreater(len(getattr(Or, '.symbols')), 1)
    is_public = lambda k: not (k.startswith('_') or k.startswith('.'))
    self.assertEqual(len([k for k in Or.__dict__ if is_public(k)]), 1)

  @cytest.with_flags(defaultconverter='topython')
  def testExprModuleOutlivesNextCompile(self):
    '''
    An expression module stays loaded while its goal can still be evaluated.
    An audit finding: compiling a second expression unloaded the first one's
    module, and the C++ backend then read freed memory through the goal.
    '''
    a = curry.compile('"hello" ++ " world"', 'expr')
    b = curry.compile('"other"', 'expr')
    gc.collect()
    self.assertEqual(list(curry.eval(a)), ['hello world'])
    self.assertEqual(list(curry.eval(b)), ['other'])

  @cytest.with_flags(defaultconverter='topython')
  def testAnonymousModuleNamesNotReused(self):
    '''
    The names of anonymous modules are unique for the process.  An audit
    finding: the counter restarted with each reset, so a module compiled after
    a reset took the name of one compiled before it.  On the C++ backend the
    second module then resolved to the first one's code.
    '''
    first = curry.compile('f :: Int\nf = 1')
    goal = curry.compile('"first"', 'expr')
    # Keep the first expression module loaded across the reset.
    held = list(curry.getInterpreter()._expression_modules)
    curry.reset()
    second = curry.compile('f :: Int\nf = 2')
    self.assertNotEqual(first.__name__, second.__name__)
    self.assertEqual(list(curry.eval(second.f)), [2])
    self.assertEqual(list(curry.eval(curry.compile('"second"', 'expr'))), ['second'])
    del held, goal

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the module registry belongs to the C++ backend'
    )
  def testReusedModuleNameIsAnError(self):
    '''
    A second library under a live module name is refused.  The runtime would
    otherwise resolve the new module to the code of the first one.
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='Dup')
    curry.reset()
    with self.assertRaisesRegex(curry.exceptions.DynloadError, "'Dup'"):
      curry.compile('f :: Int\nf = 2', modulename='Dup')
    del first

  @cytest.check_expressions()
  def testExprType(self):
    '''Test the exprtype argument.'''
    # 1+2.  Without exprtype, the constraint Num a is defaulted to Int by the
    # table of the PAKCS REPL (unit_goals.py), and the body passes the
    # dictionary.
    yield curry.compile('1+2', mode='expr'), None, None, None, [3]
    # The C++ backend represents the single rewrite step taken by
    # curry.compile(..., 'expr') as a forward node at the root; the Python
    # backend rewrites the root in place.  Compare the forward target so one
    # expectation serves both backends.  The optimizer replaces the call of
    # the alias _impl#+#Prelude.Num#Prelude.Int by a call of plusInt.
    e = curry.compile('1+2', mode='expr', exprtype='Int')
    yield inspect.fwd_chain_target(e), None \
           , '<plusInt <Int 1> <Int 2>>' \
           , None \
           , [3]

    # 1 ? 2
    yield curry.compile('1 ? 2', mode='expr'), None, None, None, [1, 2]
    e = curry.compile('1 ? 2', mode='expr', exprtype='Int')
    yield inspect.fwd_chain_target(e), None, '<? <Int 1> <Int 2>>', None, [1, 2]

  @cytest.check_expressions()
  def test_reclet(self):
    e = curry.compile('''let a = True:b ; b = False:a in a''', 'expr')
    yield e, '[True, False, ...]', '<_Fwd <: <True> <: <False> ...>>>'
    # A back reference below the top-level constructor gives the INodeAssign a
    # path of length two.  Both backends must index to the parent slot.
    M = curry.compile('data T = T Bool T Int', modulename='RecLetT')
    e = curry.compile('let a = T True (T False a 1) 2 in a', 'expr', imports=M)
    yield e, 'T True (T False ... 1) 2' \
           , '<_Fwd <T <True> <T <False> ... <Int 1>> <Int 2>>>'

