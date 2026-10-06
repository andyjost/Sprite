'''
Tests for IO actions combined with bind.

Covers a 2023 report by Michael Hanus: ``readFile f >>= return . length``
failed with "node index out of range" because ``readFile`` rewrote to a bare
list instead of an ``IO`` node, so ``bindIO`` passed the wrong successor to the
continuation.  ``getChar`` had the same defect, and ``appendFile`` opened the
file in write mode.

Also covers non-determinism in monadic actions.  A choice at the inductive
position of a monadic step is an error on both backends, with one text.

The programs are in data/curry/IOBind.curry.  One module serves every test,
so the Curry front end and the C++ compiler run once per build of the module,
not once per test.
'''
import cytest # from ./lib; must be first
from curry import common
from curry.exceptions import NondetMonadError
import contextlib, curry, os, tempfile, unittest

# The text of the error for a choice in a monadic action.  The C++ runtime
# defines the same text (NONDET_MONAD_ERROR_TEXT in cyrt/builtins.hpp).
NONDET_TEXT = str(NondetMonadError())

@contextlib.contextmanager
def fresh_directory():
  '''Runs the body in a new, empty working directory.'''
  with tempfile.TemporaryDirectory() as tmpdir:
    cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
      yield tmpdir
    finally:
      os.chdir(cwd)

class IOBindTestCase(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Build the module once.  A test that resets the interpreter imports it
    # again from the cache.
    curry.import_('IOBind')

  @property
  def M(self):
    return curry.import_('IOBind')

  def eval_(self, goal, *args, **kwds):
    return list(curry.eval(goal, *args, **kwds))

  def assertNondetError(self, goal, *args):
    '''Evaluates the goal and checks for the non-determinism error.'''
    with self.assertRaises(curry.EvaluationError) as cm:
      self.eval_(goal, *args)
    self.assertEqual(str(cm.exception), NONDET_TEXT)

class TestIOBind(IOBindTestCase):
  # The 121 bytes of Peano.curry, the file in the report.  On the Python
  # backend, ``length`` of a string this long needs the raised recursion limit
  # of the evaluator.
  INPUT = 'data/curry/io/readFile_bind.in'

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_bind_length(self):
    expected = len(cytest.readfile(self.INPUT))
    self.assertGreaterEqual(expected, 121)
    self.assertEqual(self.eval_(self.M.readLength, self.INPUT), [expected])

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_empty_file(self):
    '''
    An audit finding: the Python backend mapped the file into memory, and
    mmap rejects an empty file.
    '''
    with fresh_directory():
      open('empty.txt', 'w').close()
      value, = self.eval_(self.M.readText, 'empty.txt')
      # An empty string converts to an empty list: no character marks the
      # type.  Check the length, which both representations have.
      self.assertEqual(len(value), 0)
      self.assertEqual(self.eval_(self.M.readLength, 'empty.txt'), [0])

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_utf8_length(self):
    '''
    A file holds UTF-8, and length counts code points.  The Python backend
    read a file byte by byte, and the C++ backend stored each byte as a Char.
    '''
    text = '\u00e4\u00f6\u00fc\U0001f600\n'
    with fresh_directory():
      with open('utf8.txt', 'wb') as stream:
        stream.write(text.encode('utf-8'))
      self.assertEqual(os.path.getsize('utf8.txt'), 11)
      self.assertEqual(self.eval_(self.M.readLength, 'utf8.txt'), [5])
      self.assertEqual(self.eval_(self.M.readText, 'utf8.txt'), [text])

  @cytest.with_flags(defaultconverter='topython')
  def test_readFile_top_level(self):
    # The IO wrapper is stripped from a top-level value.
    self.assertEqual(
        self.eval_(self.M.readText, 'data/sample.txt')
      , [cytest.readfile('data/sample.txt')]
      )

  @unittest.skipIf(
      curry.flags['backend'] == 'cxx'
    , 'the C++ getChar reads the process stdin; setio cannot redirect it'
    )
  @cytest.with_flags(defaultconverter='topython')
  @cytest.setio(stdin='mu')
  def test_getChar_bind(self):
    self.assertEqual(self.eval_(self.M.getCharOrd), [ord('m')])

  def test_appendFile_appends(self):
    with fresh_directory():
      self.eval_(self.M.writeThenAppend, 'file.txt')
      self.assertEqual(cytest.readfile('file.txt'), 'abcd')

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'unit_py_io_files covers the Python backend with a small step budget'
    )
  @cytest.with_flags(defaultconverter='topython', rotation='steps:65536')
  def test_writeFile_keeps_prefix_across_rotation(self):
    '''
    An audit finding: the C++ writeFile opened the file in write mode on
    every entry of its step function.  When the scheduler rotated the queue
    in the middle of a write, the re-entry truncated the file and the prefix
    was lost.  In step mode the C++ backend rotates after every 65536
    completed steps, so two long writes in parallel alternatives interrupt
    each other several times.  The test forces step mode: in time mode a
    rotation lands inside the write only by chance (see
    unit_cxx_rotation.py for the modes).
    '''
    n = 40000
    with fresh_directory():
      results = self.eval_(self.M.twoWrites, n)
      self.assertEqual(len(results), 2)
      self.assertEqual(cytest.readfile('a.txt'), 'abcd' * n)
      self.assertEqual(cytest.readfile('b.txt'), 'wxyz' * n)

  def test_io_builtins_are_monadic(self):
    '''
    The IO built-ins carry F_MONADIC on both backends.  The C++ hnf reads the
    flag of the redex to decide whether a choice is an error.
    '''
    for name in [
        'bindIO', 'catch', 'getChar', 'prim_appendFile', 'prim_ioError'
      , 'prim_putChar', 'prim_readFile', 'prim_writeFile', 'returnIO'
      ]:
      info = curry.symbol('Prelude.' + name).info
      self.assertTrue(info.flags & common.F_MONADIC, name)
    for name in ['$!', '$!!', '$##', 'apply', 'ensureNotFree']:
      info = curry.symbol('Prelude.' + name).info
      self.assertFalse(info.flags & common.F_MONADIC, name)

  @cytest.setio(stdout='')
  def test_putChar_nondet_is_an_error(self):
    '''
    An audit finding: on the C++ backend, hnf pull-tabbed the choice to the
    root of the step and forked the action.  putChar applies prim_putChar
    with ($!), whose retry after the pull-tab read a dead variable and
    crashed the process.  Now ($!) evaluates the argument on behalf of the
    monadic function, and hnf reports the error, as the Python backend does.
    '''
    self.assertNondetError(self.M.putCharNondet)

  @cytest.setio(stdout='')
  def test_putStrLn_nondet_is_an_error(self):
    '''A choice at the inductive position of putStr, a compiled function.'''
    self.assertNondetError(self.M.putStrLnNondet)

  def test_bindIO_nondet_action_is_an_error(self):
    '''A choice between two actions at the first argument of bindIO.'''
    self.assertNondetError(self.M.bindNondet)

  def test_readFile_nondet_name_is_an_error(self):
    '''
    readFile applies prim_readFile with ($##).  The choice turns up while the
    argument is normalized.
    '''
    self.assertNondetError(self.M.readFileNondet)

  def test_writeFile_nondet_string_is_an_error(self):
    '''
    An audit finding: a choice inside the string forked the C++ evaluation,
    and both alternatives wrote to the file.  The characters before the
    choice are written, then the error is raised.  appendFile shares the
    step.
    '''
    with fresh_directory():
      self.assertNondetError(self.M.writeNondet, 'file.txt')
      self.assertEqual(cytest.readfile('file.txt'), 'ab')
      self.assertNondetError(self.M.appendNondet, 'file.txt')
      self.assertEqual(cytest.readfile('file.txt'), 'ab')

  @unittest.expectedFailure
  def test_mapM_nondet_is_an_error(self):
    '''
    A choice met by a Curry-defined IO combinator.  mapM_ hands the list to
    map and foldr, which are not monadic steps, so the choice is pull-tabbed
    to the top and the action forks: both alternatives run, and the goal
    yields two values.  PAKCS reports the non-determinism error.  Recorded
    in TODO; the rule covers only the step that meets the choice.
    '''
    with fresh_directory():
      self.assertNondetError(self.M.mapMNondet, 'file.txt')

  def test_catch_hands_NondetError_to_the_handler(self):
    '''
    catch catches the error.  The handler receives the NondetError value with
    the same text, and show adds the kind.
    '''
    with fresh_directory():
      self.assertEqual(len(self.eval_(self.M.catchNondet)), 1)
      self.assertEqual(
          cytest.readfile('err.txt'), 'nondet error: ' + NONDET_TEXT
        )

@unittest.skipIf(
    curry.flags['backend'] != 'cxx'
  , 'the Python backend keys its rule on function names, and its catch '
    'catches only IOError and MonadError'
  )
class TestCxxMonadic(IOBindTestCase):
  '''
  The C++ runtime applies the rule to every monadic step, and its catch
  hands the error value to the handler.
  '''
  def run_in_fresh_directory(self, goal):
    '''Evaluates ``goal`` in a new directory.  Returns the values and the files.'''
    with fresh_directory():
      values = self.eval_(goal)
      files = {
          name: cytest.readfile(name) for name in os.listdir('.')
              if name.endswith('.txt')
        }
      return values, files

  def test_monadic_function_nondet_is_an_error(self):
    '''
    The rule covers every function that calls an IO function: guarded has
    F_MONADIC, so the choice it evaluates in its guard is an error.  The
    Python backend keys the rule on a list of Prelude names and forks here.
    '''
    with self.assertRaises(curry.EvaluationError) as cm:
      self.eval_(self.M.monadicGuard)
    self.assertEqual(str(cm.exception), NONDET_TEXT)

  def test_catch_hands_the_error_value_to_the_handler(self):
    '''
    An audit finding: catch applied the handler to the action instead of the
    error value, so a handler that read its argument crashed the process.
    ioError keeps the IOError value.
    '''
    values, files = self.run_in_fresh_directory(self.M.catchValue)
    self.assertEqual(len(values), 1)
    self.assertEqual(files, {'err.txt': 'user error: boom'})

  def test_catch_error_without_a_value(self):
    '''
    Prelude.error sets a message and no value.  The handler receives an
    IOError with the message, as with the PAKCS catch.  The message carries
    no quotes (an audit finding: the C++ error step quoted it).
    '''
    values, files = self.run_in_fresh_directory(self.M.catchError)
    self.assertEqual(len(values), 1)
    self.assertEqual(files, {'err.txt': 'i/o error: boom'})

  def test_catch_clears_the_error(self):
    '''
    An audit finding: the error stayed set after catch handled it, so an
    error raised by the handler failed an assertion in set_error.
    '''
    with self.assertRaises(curry.EvaluationError) as cm:
      self.eval_(self.M.catchTwice)
    self.assertEqual(str(cm.exception), 'user error: second')
