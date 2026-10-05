'''
IO on the Python backend: files and errors.  readFile, writeFile and
appendFile, a non-deterministic string in a write, the file kept across a
rotation of the queue, an I/O error and its catch.  The tests on the
standard streams are in unit_py_io.py.
'''
import tempfile
from import_blocker import with_import_blocked
import curry, os, unittest
import cytest

@unittest.skipIf(curry.flags['backend'] == 'cxx', 'TODO for C++')
class TestPyIOFiles(cytest.TestCase):
  @cytest.with_flags(defaultconverter='topython')
  def test_readfile(self):
    goal = curry.compile('readFile "data/sample.txt"', 'expr')
    result = list(curry.eval(goal))
    self.assertEqual(
      result, ["this is a file\ncontaining sample text\n\n(the end)\n"]
      )

  def test_writefile(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        txt = ('djiod', r' and finally,...')
        goal = curry.compile('writeFile "file.txt" ("%s" ++ "%s")' % txt, 'expr')
        next(curry.eval(goal))
        self.assertEqual(cytest.readfile('file.txt'), ''.join(txt))

        goal = curry.compile('writeFile "file.txt" ("%s" ? "%s")' % txt, 'expr')
        self.assertRaisesRegex(
            curry.EvaluationError
          , r'non-determinism in monadic actions occurred'
          , lambda: list(curry.eval(goal))
          )
      finally:
        os.chdir(cwd)

  @cytest.with_flags(step_budget=32)
  def test_writeFile_keeps_prefix_across_rotation(self):
    '''
    An audit finding: writeFile truncated the file each time its step ran.
    When the step budget rotated the queue in the middle of a write, the
    re-entry truncated the file again and the prefix was lost.  Two writes in
    parallel alternatives keep rotating until one of them ends.
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        goal = curry.compile(
            'writeFile "a.txt" (concat (replicate 50 "abcd"))'
            ' ? writeFile "b.txt" (concat (replicate 50 "wxyz"))'
          , 'expr'
          )
        results = list(curry.eval(goal))
        self.assertEqual(len(results), 2)
        self.assertEqual(cytest.readfile('a.txt'), 'abcd' * 50)
        self.assertEqual(cytest.readfile('b.txt'), 'wxyz' * 50)
      finally:
        os.chdir(cwd)

  def test_appendFile_nondet(self):
    # A non-deterministic string is an error for appendFile, as for writeFile.
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        goal = curry.compile('appendFile "file.txt" ("a" ? "b")', 'expr')
        self.assertRaisesRegex(
            curry.EvaluationError
          , r'non-determinism in monadic actions occurred'
          , lambda: list(curry.eval(goal))
          )
      finally:
        os.chdir(cwd)

  @cytest.with_flags(defaultconverter='topython')
  def test_io_error(self):
    goal = curry.compile('readFile "nofile"', 'expr')
    self.assertRaisesRegex(
        IOError
      , r"\[Errno 2\] No such file or directory: 'nofile'"
      , lambda: list(curry.eval(goal))
      )

  @cytest.with_flags(defaultconverter='topython')
  def test_catch(self):
    goal = curry.compile('readFile "nofile" <|> return "nothing"', 'expr')
    self.assertEqual(list(curry.eval(goal)), ["nothing"])

  @cytest.with_flags(defaultconverter='topython')
  def test_ioError(self):
    from curry.utility import maxrecursion
    with maxrecursion():
      goal = curry.compile('readFile "nofile" `catch` ioError', 'expr')
      self.assertRaisesRegex(
          curry.EvaluationError
        , r"i/o error: \[Errno 2\] No such file or directory: 'nofile'"
        , lambda: list(curry.eval(goal))
        )

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile(self):
    readFile = curry.symbol('Prelude.readFile')
    self.assertEqual(
        list(curry.eval(readFile, "data/sample.txt"))
      , ['this is a file\ncontaining sample text\n\n(the end)\n']
      )

  @with_import_blocked('mmap')
  def test_readFile_no_mmap(self):
    self.test_readFile()
