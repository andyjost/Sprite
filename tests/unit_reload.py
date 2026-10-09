'''
An edited source is not read again by import_ or :load in one process, and
the process says so (issue #110).  curry.import_ of a loaded module returns
the module as it was loaded; when the file changed after the import, a
warning names the module and the file, once per edit, and the :load of the
REPL prints it once per :load.  On the C++ backend the background compile
of tiered execution never changes what a loaded module means: an object
compiled from the edited source is refused at the swap, and the module
stays interpreted.  Both backends run the tests of the warning.
'''
import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry.interpreter import import_ as importer
from curry.tools.icy import commands, repl
import curry, itertools, logging, os, shutil, tempfile, unittest

IS_CXX = curry.flags['backend'] == 'cxx'
COMPILE_SECONDS = 120
IMPORT_LOGGER = 'curry.interpreter.import_'
TIERED_LOGGER = 'curry.backends.cxx.tiered'

TEXT = 'module %%(name)s where\n\nf :: Int\nf = %d\n'

def write(filename, text):
  '''
  Writes a file.  The modification time moves forward by at least a
  nanosecond, so that a rewrite within the granularity of the clock counts
  as an edit on a file system with a coarse time stamp.
  '''
  try:
    before = os.stat(filename).st_mtime_ns
  except OSError:
    before = None
  with open(filename, 'w') as stream:
    stream.write(text)
  st = os.stat(filename)
  if before is not None and st.st_mtime_ns <= before:
    os.utime(filename, ns=(st.st_atime_ns, before + 1))


class EditedSourceTestCase(cytest.TestCase):
  '''A temporary source directory with one fresh module per name.'''
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-reload-test-')
    curry.path.insert(0, self.tmpdir)

  def tearDown(self):
    if IS_CXX:
      # No compile may run while the directory goes.
      from curry.backends.cxx import tiered
      tiered.cancel()
      tiered.wait(10)
    super().tearDown()
    shutil.rmtree(self.tmpdir, ignore_errors=True)

  def write_module(self, text):
    '''Writes a module with a new name.  Returns the name.'''
    name = 'Reload%d' % next(self.counter)
    write(os.path.join(self.tmpdir, name + '.curry'), text % {'name': name})
    return name

  def edit_module(self, name, text):
    '''Writes a new text for the module ``name``.'''
    write(os.path.join(self.tmpdir, name + '.curry'), text % {'name': name})

  def source(self, name):
    return os.path.join(self.tmpdir, name + '.curry')

  def value(self, goal, *args):
    '''The first value of a goal, as a Python object.'''
    return next(curry.eval(goal, *args, converter='topython'))


class TestImportAfterEdit(EditedSourceTestCase):
  def test_import_warns_once_per_edit(self):
    name = self.write_module(TEXT % 1)
    M = curry.import_(name)
    self.assertEqual(self.value(M.f), 1)
    self.assertIsNone(importer.edited_source(M))
    self.edit_module(name, TEXT % 2)
    self.assertEqual(importer.edited_source(M), self.source(name))
    with capture_log(IMPORT_LOGGER) as log:
      # The loaded module comes back, and one warning says that the file
      # was not read again.
      self.assertIs(curry.import_(name), M)
      # A second import of the same edit says nothing more, nor does the
      # import of a module that imports it.
      self.assertIs(curry.import_(name), M)
      dep = self.write_module(
          'module %%(name)s where\nimport %s\n\ng :: Int\ng = f\n' % name
        )
      curry.import_(dep)
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 1, warnings)
    self.assertIn('module %r was not read again' % name, warnings[0])
    self.assertIn(self.source(name), warnings[0])
    self.assertIn('a new process reads the edited file', warnings[0])
    self.assertEqual(self.value(M.f), 1)
    # The next edit is reported again.
    self.edit_module(name, TEXT % 3)
    with capture_log(IMPORT_LOGGER) as log:
      self.assertIs(curry.import_(name), M)
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertEqual(self.value(M.f), 1)

  def test_unchanged_source_is_silent(self):
    name = self.write_module(TEXT % 1)
    M = curry.import_(name)
    with capture_log(IMPORT_LOGGER) as log:
      self.assertIs(curry.import_(name), M)
      self.assertIs(curry.import_(name), M)
    self.assertEqual(log.data[logging.WARNING], [])
    # A module without a source file records no time and is never stale.
    S = curry.compile('h :: Int\nh = 7\n', mode='module')
    self.assertIsNone(importer.edited_source(S))


class TestReplLoadAfterEdit(EditedSourceTestCase):
  def test_load_warns_once_per_load(self):
    name = self.write_module(TEXT % 1)
    filename = self.source(name)
    session = repl.REPL([':load', filename])
    M = session.module
    self.assertEqual(M.__name__, name)
    self.assertEqual(self.value(M.f), 1)
    self.edit_module(name, TEXT % 2)
    with capture_log(IMPORT_LOGGER) as log:
      # Every :load after the edit prints the warning once.
      commands.load(session, filename)
      self.assertIs(session.module, M)
      commands.load(session, filename)
      self.assertIs(session.module, M)
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 2, warnings)
    for warning in warnings:
      self.assertIn('module %r was not read again' % name, warning)
      self.assertIn(filename, warning)
    self.assertEqual(self.value(M.f), 1)
    # A :load of an unchanged module prints nothing.
    other = self.write_module(TEXT % 5)
    with capture_log(IMPORT_LOGGER) as log:
      commands.load(session, self.source(other))
      commands.load(session, self.source(other))
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertEqual(self.value(session.module.f), 5)

  def test_load_of_another_file_warns(self):
    # Two files of one module name.  The second :load names a file the
    # process never reads: the loaded module comes back, and a warning
    # names both files.  import_ of the file says the same.
    name = self.write_module(TEXT % 1)
    first = self.source(name)
    otherdir = os.path.join(self.tmpdir, 'other')
    os.mkdir(otherdir)
    second = os.path.join(otherdir, name + '.curry')
    write(second, TEXT % 2 % {'name': name})
    session = repl.REPL([':load', first])
    M = session.module
    self.assertEqual(self.value(M.f), 1)
    with capture_log(IMPORT_LOGGER) as log:
      commands.load(session, second)
      self.assertIs(session.module, M)
      self.assertIs(curry.import_(second, is_sourcefile=True), M)
      # The file it was read from is not another file.
      commands.load(session, first)
      self.assertIs(curry.import_(first, is_sourcefile=True), M)
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 2, warnings)
    for warning in warnings:
      self.assertIn('module %r was not read from %s' % (name, second), warning)
      self.assertIn(first, warning)
    self.assertEqual(self.value(M.f), 1)


@unittest.skipUnless(IS_CXX, 'the background compile belongs to the C++ backend')
class TestSwapAfterEdit(EditedSourceTestCase):
  def setUp(self):
    super().setUp()
    curry.reload({'backend': 'cxx', 'interpret': 'tiered'})
    curry.path.insert(0, self.tmpdir)

  @cytest.hardreset
  def test_swap_refused_after_an_edit(self):
    '''
    The child of the background compile reads the source as it is when the
    child runs.  An edit between the import and the compile gave the swap
    the code of the edited file, and a loaded module changed meaning
    without a load.  The swap refuses such an object now; the module stays
    interpreted with the code the import read, and a warning says so.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt, tiered
    # Dep imports Base.  The compile of Dep waits behind the compile of
    # Base, so an edit of Dep right after the import lands before the child
    # of Dep runs.
    base = self.write_module(
        'module %(name)s where\n\ng :: Int -> Int\ng x = x + 1\n'
      )
    def dep_text(n):
      return (
          'module %%(name)s where\nimport ' + base
        + '\n\nh :: Int -> Int\nh x = g x + %d\n'
        ) % n
    dep = self.write_module(dep_text(10))
    D = curry.import_(dep)
    B = curry.import_(base)
    self.assertTrue(tiered.pending(dep))
    before = tiered.status()
    self.edit_module(dep, dep_text(20))
    self.assertEqual(self.value(D.h, 1), 12)
    with capture_log(TIERED_LOGGER) as log:
      self.assertTrue(
          tiered.wait(COMPILE_SECONDS, curry.getInterpreter())
        , 'the background compiles did not end in %s s' % COMPILE_SECONDS
        )
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 1)
    self.assertEqual(after['failed_modules'], before['failed_modules'] + 1)
    self.assertFalse(cyrt.icurry_is_interpreted(B.g.info))
    self.assertTrue(cyrt.icurry_is_interpreted(D.h.info))
    self.assertFalse(tiered.pending(dep))
    warnings = log.data[logging.WARNING]
    self.assertEqual(len(warnings), 1, warnings)
    self.assertIn('the background compile of module %r is not applied' % dep, warnings[0])
    self.assertIn('never changes what a loaded module means', warnings[0])
    # The values are the ones the import read, and the import after the
    # edit returns the loaded module and says so.
    self.assertEqual(self.value(D.h, 1), 12)
    with capture_log(IMPORT_LOGGER) as log:
      self.assertIs(curry.import_(dep), D)
    self.assertEqual(len(log.data[logging.WARNING]), 1)
    self.assertEqual(self.value(D.h, 1), 12)

  @cytest.hardreset
  def test_edit_of_a_comment_keeps_the_swap(self):
    '''
    An edit that changes no code, a comment or a touch, makes the child run
    the front end again, which writes the same ICurry.  The swap checks the
    ICurry file, not the JSON the child writes in another spacing, so the
    object is applied and the module runs compiled.
    '''
    from curry.backends.cxx import cyrtbindings as cyrt, tiered
    base = self.write_module(
        'module %(name)s where\n\ng :: Int -> Int\ng x = x + 1\n'
      )
    def dep_text(comment):
      return (
          'module %%(name)s where\nimport ' + base
        + '\n%s\nh :: Int -> Int\nh x = g x + 10\n'
        ) % comment
    dep = self.write_module(dep_text(''))
    D = curry.import_(dep)
    B = curry.import_(base)
    self.assertTrue(tiered.pending(dep))
    before = tiered.status()
    self.edit_module(dep, dep_text('-- a comment, no code changed'))
    with capture_log(TIERED_LOGGER) as log:
      self.assertTrue(
          tiered.wait(COMPILE_SECONDS, curry.getInterpreter())
        , 'the background compiles did not end in %s s' % COMPILE_SECONDS
        )
    after = tiered.status()
    self.assertEqual(after['swapped_modules'], before['swapped_modules'] + 2)
    self.assertEqual(after['failed_modules'], before['failed_modules'])
    self.assertEqual(log.data[logging.WARNING], [])
    self.assertFalse(cyrt.icurry_is_interpreted(B.g.info))
    self.assertFalse(cyrt.icurry_is_interpreted(D.h.info))
    self.assertEqual(self.value(D.h, 1), 12)
