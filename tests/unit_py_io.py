import cytest # from ./lib; must be first
from cStringIO import StringIO
from curry.utility import _tempfile
import curry
import os
import unittest

class TestPyIO(cytest.TestCase):
  def test_monadic_property1(self):
    stab = getattr(curry.getInterpreter().prelude, '.symbols')
    monadic_symbols = sorted([
        symbol for symbol, obj in stab.items()
            if obj.icurry.metadata.get('all.monadic', False)
      ])
    correct = [
          'appendFile', 'prim_appendFile', 'prim_putChar', 'prim_readFile'
        , 'prim_writeFile', 'print', 'putChar', 'putStr', 'putStrLn'
        , 'readFile', 'writeFile'
        ]
    self.assertEqual(monadic_symbols, correct)

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
    self.assertEqual(str(result), 'IO ()')

  @cytest.with_flags(defaultconverter='topython')
  def test_readfile(self):
    goal = curry.compile('readFile "data/sample.txt"', 'expr')
    result = list(curry.eval(goal))
    self.assertEqual(
      result, ["this is a file\ncontaining sample text\n\n(the end)\n"]
      )

  def test_writefile(self):
    with _tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        txt = ('djiod', r' and finally,...')
        goal = curry.compile('writeFile "file.txt" ("%s" ++ "%s")' % txt, 'expr')
        next(curry.eval(goal))
        self.assertEqual(open('file.txt', 'r').read(), ''.join(txt))

        goal = curry.compile('writeFile "file.txt" ("%s" ? "%s")' % txt, 'expr')
        self.assertRaisesRegexp(
            RuntimeError
          , r'non-determinism in monadic actions occurred'
          , lambda: list(curry.eval(goal))
          )
      finally:
        os.chdir(cwd)

  @cytest.setio(stdout='')
  def test_nd_io(self):
    goal = curry.compile("putChar ('a' ? 'b')", 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in monadic actions occurred'
      , lambda: list(curry.eval(goal))
      )

  @cytest.setio(stdout='')
  def test_nd_io2(self):
    goal = curry.compile('''putStrLn ("one" ? "two")''', 'expr')
    self.assertRaisesRegexp(
        RuntimeError
      , r'non-determinism in monadic actions occurred'
      , lambda: list(curry.eval(goal))
      )

