import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.toolchain import plans
from curry.utility import filesys
from curry.utility.binding import binding
import tempfile
import curry, gc, importlib, os, shutil, stat, time, unittest

GENERATE_GOLDENS = False

def reorder_ctimes(files):
  '''
  Moves the change times of ``files`` to now, one file after the other, so
  that their order by change time is the order given.  Each file gets a
  chmod to the mode it has, which moves the change time of the inode and
  leaves the modification time alone, as the prefix patch of a package
  manager does (issue #66).  A chmod is repeated until the clock moved past
  the file before.  A file system that keeps the change time on such a
  chmod skips the test.
  '''
  last = 0
  for filename in files:
    before = os.stat(filename)
    mode = stat.S_IMODE(before.st_mode)
    floor = max(last, before.st_ctime_ns)
    for _ in range(500):
      os.chmod(filename, mode)
      after = os.stat(filename)
      if after.st_ctime_ns > floor:
        break
      time.sleep(0.002)
    else:
      raise unittest.SkipTest(
          'a chmod to the same mode keeps the change time of %r' % filename
        )
    assert after.st_mtime_ns == before.st_mtime_ns, filename
    last = after.st_ctime_ns

class RefusingStep(object):
  '''A step of a plan that refuses the files named in ``stale``.'''
  def __init__(self):
    self.stale = set()
  def is_stale(self, filename):
    return os.path.basename(filename) in self.stale
  def __call__(self, *args, **kwds):
    raise AssertionError('no step runs')

class TestFindCurry(cytest.TestCase):
  def test_findFile(self):
    '''
    Tests the low-level findfile function with the following tree:

        data/findFile
        ├── a
        │   ├── a.foo
        │   └── .curry
        │       └── sprite
        │           └── a.json
        ├── b
        │   ├── a
        │   │   ├── a.curry
        │   │   └── a.foo
        │   └── a.curry
        └── c
            ├── a
            └── c.curry
    '''
    ff = filesys.findfiles
    self.assertEqual(
        list(ff(
            names=['a.curry']
          , searchpaths=['data/findFile/a']
          ))
      , []
      )
    self.assertEqual(list(ff(['data/findFile/a'], ['a.curry'])), [])
    self.assertEqual(
        list(ff(['data/findFile/b'], ['a.curry']))
      , ['data/findFile/b/a.curry']
      )
    self.assertEqual(
        list(ff(['data/findFile/b/a'], ['a.curry']))
      , ['data/findFile/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/findFile/b'], ['a/a.curry']))
      , ['data/findFile/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(
            ['data/findFile/a', 'data/findFile/b', 'data/findFile/b/a']
          , ['a.curry']
          ))
      , ['data/findFile/b/a.curry', 'data/findFile/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/findFile/a'], ['a.foo']))
      , ['data/findFile/a/a.foo']
      )
    self.assertEqual(
        list(ff(
            ['data/findFile/a', 'data/findFile/b/a']
          , ['a.curry', 'a.foo']
          ))
      , [   'data/findFile/a/a.foo'
          , 'data/findFile/b/a/a.curry'
          , 'data/findFile/b/a/a.foo'
          ]
      )
    self.assertEqual(
        list(ff(['data/findFile/c'], ['a']))
      , ['data/findFile/c/a']
      )

  def setUp(self):
    super().setUp()
    # currentfile needs a build plan.  Searching for the ICurry-JSON file
    # requires a plan that reaches the JSON stage.
    self.plan = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON)
    # Copy the findFile tree to a temporary directory and add the gitignored
    # fixture a/.curry/<intermediate_subdir>/a.json, which has no a.curry.
    self.tmpdir = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmpdir.cleanup)
    self.root = os.path.join(self.tmpdir.name, 'findFile')
    shutil.copytree(
        'data/findFile', self.root, ignore=shutil.ignore_patterns('.curry')
      )
    self.jsondir_a = os.path.join(
        self.root, 'a', '.curry', config.intermediate_subdir()
      )
    os.makedirs(self.jsondir_a)
    self.json_a = os.path.join(self.jsondir_a, 'a.json')
    with open(self.json_a, 'w') as ostream:
      ostream.write('{}')

  def test_findCurry(self):
    sub = lambda *parts: os.path.join(self.root, *parts)
    self.assertEqual(
        toolchain.currentfile(self.plan, 'c', currypath=[sub('c')])
      , sub('c', 'c.curry')
      )
    self.assertEqual(
        toolchain.currentfile(self.plan, 'a', currypath=[sub('b')])
      , sub('b', 'a.curry')
      )
    # Under a/ there is no a.curry, but there is .curry/<subdir>/a.json.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        toolchain.currentfile(
            self.plan, 'a', currypath=[sub(a_or_b) for a_or_b in 'ab']
          )
      , self.json_a
      )

  def test_getICurryForModule(self):
    '''Check that the toolchain is invoked to produce ICurry-JSON files.'''
    # If the JSON file already exists, currentfile finds it.
    self.assertEqual(
        toolchain.currentfile(self.plan, 'a', [os.path.join(self.root, 'a')])
      , self.json_a
      )

    # Otherwise, makecurry builds the JSON.  Work on a copy of hello.curry so
    # that the cached build under data/curry is left alone.
    srcdir = os.path.join(self.tmpdir.name, 'hello')
    os.makedirs(srcdir)
    shutil.copy('data/curry/hello.curry', srcdir)
    jsonfile = os.path.join(
        srcdir, '.curry', config.intermediate_subdir(), 'hello.json'
      )
    goldenfile = 'data/curry/hello.json.au'
    self.assertFalse(os.path.exists(jsonfile))
    self.assertEqual(
        toolchain.makecurry(self.plan, 'hello', [srcdir], zip=False)
      , jsonfile
      )
    self.assertTrue(os.path.exists(jsonfile))
    # The golden tracks the output of Sprite's own icurry.json encoder
    # (toolchain._icurry2json writes the file internally).  The "aliases" key
    # comes from IModule._fields_.
    self.assertEqualToFile(cytest.readfile(jsonfile), goldenfile, GENERATE_GOLDENS)
    icur = toolchain.loadcurry(self.plan, 'hello', [srcdir])
    icur.filename = None
    au = icurry.json.loads(cytest.readfile(goldenfile))
    self.assertEqual(icur, au)

  def test_illegal_name(self):
    self.assertRaisesRegex(
        ValueError, r"'kiel/rev' is not a legal module name."
      , lambda: curry.import_('kiel/rev')
      )
    self.assertRaisesRegex(
        ValueError, r"'.' is not a legal module name."
      , lambda: curry.import_('.')
      )
    self.assertRaisesRegex(
        ValueError, r"'..' is not a legal module name."
      , lambda: curry.import_('..')
      )

  def test_import_with_currypath(self):
    self.assertRaisesRegex(
        ValueError
      , r"module 'import_test' not found"
      , lambda: curry.import_('import_test')
      )
    self.assertRaisesRegex(
        TypeError
      , r"'currypath' must be a string or sequence of strings, got 1."
      , lambda: curry.import_('import_test', currypath=1)
      )
    self.assertMayRaise(
        None
      , lambda: curry.import_('import_test', currypath=['data/import_'])
      )
    del curry.modules['import_test']
    self.assertMayRaise(
        None
      , lambda: curry.import_('import_test', currypath='data/import_')
      )

  def test_newer(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      a = os.path.join(tmpdir, 'a')
      b = os.path.join(tmpdir, 'b')
      open(a, 'w').close()
      time.sleep(0.01)
      open(b, 'w').close()
      self.assertTrue(filesys.newer(b, a))
      self.assertFalse(filesys.newer(a, b))
    #
    self.assertTrue(
        filesys.newer('data/curry/hello.curry', 'this_file_does_not_exist')
      )
    # The modification time decides, not the change time of the inode
    # (issue #66).  Of two files with the same time, newest takes the later
    # one in the collection.
    with tempfile.TemporaryDirectory() as tmpdir:
      a = os.path.join(tmpdir, 'a')
      b = os.path.join(tmpdir, 'b')
      base = int(time.time()) - 100
      for i, filename in enumerate([a, b]):
        open(filename, 'w').close()
        os.utime(filename, (base + i, base + i))
      self.assertTrue(filesys.newer(b, a))
      self.assertEqual(filesys.newest([a, b]), b)
      self.assertEqual(filesys.newest([b, a]), b)
      # Now a has the later change time and the earlier modification time.
      reorder_ctimes([b, a])
      self.assertGreater(os.stat(a).st_ctime_ns, os.stat(b).st_ctime_ns)
      self.assertTrue(filesys.newer(b, a))
      self.assertFalse(filesys.newer(a, b))
      self.assertEqual(filesys.newest([a, b]), b)
      self.assertEqual(filesys.newest([b, a]), b)
      os.utime(a, (base + 1, base + 1))
      self.assertFalse(filesys.newer(a, b))
      self.assertFalse(filesys.newer(b, a))
      self.assertEqual(filesys.newest([a, b]), b)
      self.assertEqual(filesys.newest([b, a]), a)

  def test_refused_files(self):
    '''
    currentfile drops a file that a step of the plan refuses, and the files
    after it, then takes the newest of the rest.  The last stage has no step,
    so the step that made its file answers for it; the C++ backend refuses an
    object compiled against other runtime headers this way.  The age of the
    runtime library does not count.  A newer source still wins.
    '''
    class Step(object):
      def __init__(self):
        self.stale = set()
      def is_stale(self, filename):
        return os.path.basename(filename) in self.stale
      def __call__(self, *args, **kwds):
        raise AssertionError('no step runs')
    icy_step, json_step = Step(), Step()
    plan = plans.Plan(None, 0, [
        plans.Stage(['.curry'], object())
      , plans.Stage(['.icy'], icy_step)
      , plans.Stage(['.json'], json_step)
      , plans.Stage(['.so'], None)
      ])
    srcdir = os.path.join(self.tmpdir.name, 'refused')
    subdir = os.path.join(srcdir, '.curry', config.intermediate_subdir())
    os.makedirs(subdir)
    curryfile = os.path.join(srcdir, 'm.curry')
    files = [curryfile] + [
        os.path.join(subdir, 'm' + suffix)
            for suffix in ['.icy', '.json', '.so']
      ]
    self.assertEqual(plan.filelist(curryfile), files)
    # Make the files in the order of the plan, so that the object is the
    # newest.
    for filename in files:
      open(filename, 'w').close()
      time.sleep(0.01)
    current = lambda: toolchain.currentfile(
        plan, curryfile, [], is_sourcefile=True
      )
    self.assertEqual(current(), files[3])
    # The step that made the object refuses it.
    json_step.stale.add('m.so')
    self.assertEqual(current(), files[2])
    # A refused file takes the files after it along.
    icy_step.stale.add('m.icy')
    self.assertEqual(current(), files[0])
    icy_step.stale.clear()
    self.assertEqual(current(), files[2])
    json_step.stale.clear()
    self.assertEqual(current(), files[3])
    # SPRITE_FORCE_RECOMPILE_CXX leaves out the C++ files.
    with binding(os.environ, 'SPRITE_FORCE_RECOMPILE_CXX', '1'):
      self.assertEqual(current(), files[2])
    # A newer source wins over an accepted object.
    time.sleep(0.01)
    os.utime(curryfile, None)
    self.assertEqual(current(), curryfile)

  def test_change_times_do_not_count(self):
    '''
    currentfile judges the chain of a module by modification times.  The
    change times of the inodes move with a chmod, a rename, or the prefix
    patch of a package manager, in an order of their own (issue #66); here
    they are put in the reverse order of the chain, the source last.  The
    newest product by modification time is still the current file, a
    refused object still goes, and an edited source still wins.
    '''
    json_step = RefusingStep()
    plan = plans.Plan(None, 0, [
        plans.Stage(['.curry'], object())
      , plans.Stage(['.icy'], object())
      , plans.Stage(['.json'], json_step)
      , plans.Stage(['.so'], None)
      ])
    srcdir = os.path.join(self.tmpdir.name, 'reordered')
    subdir = os.path.join(srcdir, '.curry', config.intermediate_subdir())
    os.makedirs(subdir)
    curryfile = os.path.join(srcdir, 'm.curry')
    files = plan.filelist(curryfile)
    self.assertEqual(len(files), 4)
    base = int(time.time()) - 100
    for i, filename in enumerate(files):
      open(filename, 'w').close()
      os.utime(filename, (base + i, base + i))
    reorder_ctimes(list(reversed(files)))
    ctimes = [os.stat(f).st_ctime_ns for f in files]
    self.assertEqual(ctimes, sorted(ctimes, reverse=True))
    self.assertEqual(
        [os.stat(f).st_mtime_ns for f in files]
      , [(base + i) * 10 ** 9 for i in range(4)]
      )
    current = lambda: toolchain.currentfile(
        plan, curryfile, [], is_sourcefile=True
      )
    self.assertEqual(current(), files[3])
    json_step.stale.add('m.so')
    self.assertEqual(current(), files[2])
    json_step.stale.clear()
    self.assertEqual(current(), files[3])
    # An edit writes the source: its modification time is now.
    with open(curryfile, 'w') as stream:
      stream.write('-- edited\n')
    self.assertEqual(current(), curryfile)

class TestReorderedChangeTimes(cytest.TestCase):
  '''
  The products of a module are judged by their modification times (issue
  #66).  A package manager that writes its prefix into the installed files
  of a module, as conda does, gives them their final change times in an
  order of its own.  By change times it was a lottery whether the .cpp or
  the .so of a module counted as newer, and a module whose ABI stamp was
  accepted was compiled again at its first import.  Here the change times
  of a built chain are put in the reverse order: the module is not made
  again; an edited source is, through every step; and on the C++ backend an
  object whose stamp differs is.
  '''
  NAME = 'ChangeTimes'

  def setUp(self):
    super().setUp()
    if curry.flags['backend'] == 'cxx':
      # The compile steps run in this process.  Under the default of the
      # flag ``interpret`` (tiered) the plan of a module ends at its JSON
      # and the object is compiled in the background; see
      # unit_cxx_toolchain.  The cleanup restores the default.
      curry.reload({'interpret': 'off'})
      curry.import_('Prelude')
      self.addCleanup(self.reload_curry)
    self.plan = plans.makeplan(
        curry.getInterpreter(), plans.MAKE_ALL | plans.ZIP_JSON
      )
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-findcurry-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
    self.srcdir = os.path.join(self.tmpdir, 'src')
    os.mkdir(self.srcdir)
    self.curryfile = os.path.join(self.srcdir, self.NAME + '.curry')

  @staticmethod
  def reload_curry():
    importlib.reload(curry)
    gc.collect()

  def write_source(self, value):
    with open(self.curryfile, 'w') as stream:
      stream.write('goal :: Int\ngoal = %d\n' % value)

  def currentfile(self):
    return toolchain.currentfile(self.plan, self.NAME, [self.srcdir])

  def make(self):
    return toolchain.makecurry(self.plan, self.NAME, [self.srcdir])

  def mtimes(self, files):
    return [os.stat(f).st_mtime_ns for f in files]

  def test_kept_under_reordered_change_times(self):
    files = self.plan.filelist(self.curryfile)
    self.assertEqual(files[0], self.curryfile)
    self.assertGreaterEqual(len(files), 4)
    self.write_source(1)
    self.assertEqual(self.make(), files[-1])
    for filename in files:
      self.assertTrue(os.path.isfile(filename), filename)
    built = self.mtimes(files)
    self.assertEqual(built, sorted(built))
    # The change times in the reverse order of the chain, the source last.
    reorder_ctimes(list(reversed(files)))
    self.assertEqual(self.mtimes(files), built)
    ctimes = [os.stat(f).st_ctime_ns for f in files]
    self.assertEqual(ctimes, sorted(ctimes, reverse=True))
    # The module is current.  Nothing is made again.
    self.assertEqual(self.currentfile(), files[-1])
    self.assertEqual(self.make(), files[-1])
    self.assertEqual(self.mtimes(files), built)
    # An edited source is made again, through every step.
    self.write_source(2)
    if os.stat(self.curryfile).st_mtime_ns <= built[-1]:
      # A coarse clock gave the edit the time of the last product.
      later = built[-1] + 1
      os.utime(self.curryfile, ns=(later, later))
    self.assertEqual(self.currentfile(), self.curryfile)
    self.assertEqual(self.make(), files[-1])
    remade = self.mtimes(files)
    for old, new, filename in zip(built, remade, files):
      self.assertGreater(new, old, filename)
    self.assertEqual(remade, sorted(remade))
    self.assertEqual(self.currentfile(), files[-1])
    module = curry.import_(self.NAME, currypath=[self.srcdir])
    self.assertEqual(
        list(curry.eval(module.goal, converter='topython')), [2]
      )
    if curry.flags['backend'] == 'cxx':
      # An object whose ABI stamp differs goes, whatever the times say.
      from curry.backends.cxx.toolchain import Cpp2So
      self.assertTrue(files[-1].endswith('.so'))
      with open(Cpp2So.stampfile(files[-1]), 'w') as stream:
        stream.write('0123456789abcdef\n')
      self.assertEqual(self.currentfile(), files[-2])
      self.assertTrue(files[-2].endswith('.cpp'))
