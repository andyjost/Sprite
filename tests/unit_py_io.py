'''
IO on the Python backend: the monadic flag of the Prelude, the standard
streams, and a choice inside an action.  The tests on files and on errors
are in unit_py_io_files.py.  The two files share no fixture; the split
spreads the front-end calls over the parallel runner (tests/README,
section 10).
'''
from curry import common
from io import StringIO
import curry, unittest
import cytest

@unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
class TestPyIO(cytest.TestCase):
  MONADIC_PAKCS_3_3_0 = [
        'appendFile', 'prim_appendFile', 'prim_ioError', 'prim_putChar', 'prim_readFile'
      , 'prim_writeFile', 'print', 'putChar', 'putStr', 'putStrLn'
      , 'readFile', 'writeFile'
      ]
  MONADIC_PAKCS_3_4_1 = [
      '_impl#*>#Prelude.Applicative#Prelude.IO'
    , '_impl#<$#Prelude.Functor#Prelude.IO'
    , '_impl#<*#Prelude.Applicative#Prelude.IO'
    , '_impl#<*>#Prelude.Applicative#Prelude.IO'
    , '_impl#<|>#Prelude.Alternative#Prelude.IO'
    , '_impl#>>#Prelude.Monad#Prelude.IO'
    , '_impl#>>=#Prelude.Monad#Prelude.IO'
    , '_impl#empty#Prelude.Alternative#Prelude.IO'
    , '_impl#fail#Prelude.MonadFail#Prelude.IO'
    , '_impl#fmap#Prelude.Functor#Prelude.IO'
    , '_impl#liftA2#Prelude.Applicative#Prelude.IO'
    , '_impl#many#Prelude.Alternative#Prelude.IO'
    , '_impl#mappend#Prelude.Monoid#Prelude.IO'
    , '_impl#mconcat#Prelude.Monoid#Prelude.IO'
    , '_impl#mempty#Prelude.Monoid#Prelude.IO'
    , '_impl#pure#Prelude.Applicative#Prelude.IO'
    , '_impl#return#Prelude.Monad#Prelude.IO'
    , '_impl#some#Prelude.Alternative#Prelude.IO'
    , '_inst#Prelude.Alternative#Prelude.IO'
    , '_inst#Prelude.Applicative#Prelude.IO'
    , '_inst#Prelude.Functor#Prelude.IO'
    , '_inst#Prelude.Monad#Prelude.IO'
    , '_inst#Prelude.MonadFail#Prelude.IO'
    , '_inst#Prelude.Monoid#Prelude.IO'
    , 'appendFile'
    , 'bindIO'
    , 'catch'
    , 'doSolve'
    , 'getChar'
    , 'getLine'
    , 'getLine._#lambda512'
    , 'getLine._#lambda512._#lambda516'
    , 'getLine._#lambda512_COMPLEXCASE0'
    , 'ioError'
    , 'prim_appendFile'
    , 'prim_ioError'
    , 'prim_putChar'
    , 'prim_readFile'
    , 'prim_writeFile'
    , 'print'
    , 'putChar'
    , 'putStr'
    , 'putStrLn'
    , 'readFile'
    , 'returnIO'
    , 'writeFile'
    ]
  MONADIC = {
      (3,3,0): MONADIC_PAKCS_3_3_0
    , (3,4,1): MONADIC_PAKCS_3_4_1
    }

  def test_monadic_property1(self):
    stab = getattr(curry.getInterpreter().prelude, '.symbols')
    monadic_symbols = sorted([
        symbol for symbol, obj in stab.items()
               if obj.info.flags & common.F_MONADIC
      ])
    libversion = curry.config.syslibversion()
    self.assertEqual(monadic_symbols, self.MONADIC[libversion])

  def test_monadic_property2(self):
    Test = curry.compile(
        '''
        main = do
            x <- return ("Hello, " ++ "World!")
            putStr x
        '''
      , modulename='Test'
      )
    self.assertTrue(Test.main.icurry.metadata['all.monadic'])

  def test_ioHello(self):
    Test = curry.compile(
        '''
        main = do
            x <- return ("Hello, " ++ "World!")
            putStr x
        '''
      , modulename='Test'
      )
    stdout = StringIO()
    curry._interpreter_.stdout = stdout
    out = curry.eval([Test.main])
    result = next(out)
    self.assertEqual(stdout.getvalue(), "Hello, World!")
    self.assertEqual(str(result), '()')

  @cytest.setio(stdout='')
  def test_nd_io(self):
    goal = curry.compile("putChar ('a' ? 'b')", 'expr')
    self.assertRaisesRegex(
        curry.EvaluationError
      , r'non-determinism in monadic actions occurred'
      , lambda: list(curry.eval(goal))
      )

  @cytest.setio(stdout='')
  def test_nd_io2(self):
    goal = curry.compile('''putStrLn ("one" ? "two")''', 'expr')
    self.assertRaisesRegex(
        curry.EvaluationError
      , r'non-determinism in monadic actions occurred'
      , lambda: list(curry.eval(goal))
      )

  @cytest.with_flags(defaultconverter='topython')
  @cytest.setio(stdin='muh\ninput\n')
  def test_getChar(self):
    getChar = curry.symbol('Prelude.getChar')
    self.assertEqual(list(curry.eval(getChar)), ['m'])

  @cytest.setio(stdout='')
  def test_putChar(self):
    putChar = curry.symbol('Prelude.putChar')
    IO = curry.symbol('Prelude.IO')
    Unit = curry.symbol('Prelude.()')
    self.assertEqual(list(curry.eval(putChar, 'x')), [curry.raw_expr(Unit)])
    self.assertEqual(curry.getInterpreter().stdout.getvalue(), 'x')
