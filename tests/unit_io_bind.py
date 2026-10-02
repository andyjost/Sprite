'''
Tests for IO actions combined with bind.

Covers a 2023 report by Michael Hanus: ``readFile f >>= return . length``
failed with "node index out of range" because ``readFile`` rewrote to a bare
list instead of an ``IO`` node, so ``bindIO`` passed the wrong successor to the
continuation.  ``getChar`` had the same defect, and ``appendFile`` opened the
file in write mode.
'''
import cytest # from ./lib; must be first
import curry, os, tempfile, unittest

class TestIOBind(cytest.TestCase):
  # The 121 bytes of Peano.curry, the file in the report.  On the Python
  # backend, ``length`` of a string this long needs the raised recursion limit
  # of the evaluator.
  INPUT = 'data/curry/io/readFile_bind.in'

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_bind_length(self):
    goal = curry.compile('readFile "%s" >>= return . length' % self.INPUT, 'expr')
    expected = len(cytest.readfile(self.INPUT))
    self.assertGreaterEqual(expected, 121)
    self.assertEqual(list(curry.eval(goal)), [expected])

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_empty_file(self):
    '''
    An audit finding: the Python backend mapped the file into memory, and
    mmap rejects an empty file.
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        open('empty.txt', 'w').close()
        goal = curry.compile('readFile "empty.txt"', 'expr')
        value, = curry.eval(goal)
        # An empty string converts to an empty list: no character marks the
        # type.  Check the length, which both representations have.
        self.assertEqual(len(value), 0)
        goal = curry.compile('readFile "empty.txt" >>= return . length', 'expr')
        self.assertEqual(list(curry.eval(goal)), [0])
      finally:
        os.chdir(cwd)

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_top_level(self):
    # The IO wrapper is stripped from a top-level value.
    goal = curry.compile('readFile "data/sample.txt"', 'expr')
    self.assertEqual(list(curry.eval(goal)), [cytest.readfile('data/sample.txt')])

  @unittest.skipIf(
      curry.flags['backend'] == 'cxx'
    , 'the C++ getChar reads the process stdin; setio cannot redirect it'
    )
  @cytest.with_flags(defaultconverter='topython')
  @cytest.setio(stdin='mu')
  def test_getChar_bind(self):
    goal = curry.compile('getChar >>= return . ord', 'expr')
    self.assertEqual(list(curry.eval(goal)), [ord('m')])

  def test_appendFile_appends(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        goal = curry.compile(
            'writeFile "file.txt" "ab" >> appendFile "file.txt" "cd"', 'expr'
          )
        list(curry.eval(goal))
        self.assertEqual(cytest.readfile('file.txt'), 'abcd')
      finally:
        os.chdir(cwd)

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'unit_py_io covers the Python backend with a small step budget'
    )
  @cytest.with_flags(defaultconverter='topython')
  def test_writeFile_keeps_prefix_across_rotation(self):
    '''
    An audit finding: the C++ writeFile opened the file in write mode on
    every entry of its step function.  When the scheduler rotated the queue
    in the middle of a write, the re-entry truncated the file and the prefix
    was lost.  The C++ backend rotates after every 65536 forward nodes it
    compresses (about one per rewrite step), so two long writes in parallel
    alternatives interrupt each other several times.
    '''
    n = 40000
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        goal = curry.compile(
            'writeFile "a.txt" (concat (replicate %d "abcd"))'
            ' ? writeFile "b.txt" (concat (replicate %d "wxyz"))' % (n, n)
          , 'expr'
          )
        results = list(curry.eval(goal))
        self.assertEqual(len(results), 2)
        self.assertEqual(cytest.readfile('a.txt'), 'abcd' * n)
        self.assertEqual(cytest.readfile('b.txt'), 'wxyz' * n)
      finally:
        os.chdir(cwd)

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'unit_py_io covers the Python backend'
    )
  @cytest.with_flags(defaultconverter='topython')
  def test_writeFile_nondet_string_is_an_error(self):
    '''
    An audit finding: a choice inside the string forked the C++ evaluation,
    and both alternatives wrote to the file.  Non-determinism in a monadic
    action is an error, as on the Python backend.  The texts of the errors
    differ between the backends (see TODO).
    '''
    with tempfile.TemporaryDirectory() as tmpdir:
      cwd = os.getcwd()
      os.chdir(tmpdir)
      try:
        goal = curry.compile(
            'writeFile "file.txt" ("ab" ++ ("c" ? "d"))', 'expr'
          )
        with self.assertRaisesRegex(curry.EvaluationError, 'nondet error'):
          list(curry.eval(goal))
      finally:
        os.chdir(cwd)
