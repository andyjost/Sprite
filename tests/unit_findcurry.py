import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.toolchain import plans
from curry.utility import filesys
from curry.utility.binding import binding
import tempfile
import curry, os, shutil, time, unittest

GENERATE_GOLDENS = False

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
