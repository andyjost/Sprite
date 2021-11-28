# Encoding: utf-8
import cytest # from ./lib; must be first
from curry import config, icurry, toolchain
from curry.utility import filesys, _tempfile
import curry, os, shutil, time

GENERATE_GOLDENS = False

def set_intermediate_subdir(f, value='sprite'):
  def replacement(*args, **kwds):
    old_value = config.intermediate_subdir
    try:
      config.intermediate_subdir = lambda: value
    finally:
      config.intermediate_subdir = old_value
  return replacement

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

  @set_intermediate_subdir
  def test_findCurry(self):
    self.assertEqual(
        toolchain.currentfile('c', currypath=['data/findFile/c'])
      , os.path.abspath('data/findFile/c/c.curry')
      )
    self.assertEqual(
        toolchain.currentfile('a', currypath=['data/findFile/b'])
      , os.path.abspath('data/findFile/b/a.curry')
      )
    # Under a/ there is no a.curry, but there is .curry/sprite/a.json.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        toolchain.currentfile(
            'a'
          , currypath=['data/findFile/'+a_or_b for a_or_b in 'ab']
          )
      , os.path.abspath('data/findFile/a/.curry/sprite/a.json')
      )

  @set_intermediate_subdir
  def test_getICurryForModule(self):
    '''Check that curry2json is invoked to produce ICurry-JSON files.'''
    # If the JSON file already exists, this should find it, just like
    # findCurryModule does.
    self.assertEqual(
        toolchain.currentfile('a', ['data/findFile/a'], zip=False)
      , os.path.abspath('data/findFile/a/.curry/sprite/a.json')
      )

    jsondir = 'data/curry/.curry/sprite'
    jsonfile = os.path.join(jsondir, 'hello.json')
    goldenfile = 'data/curry/hello.json.au'
    def rmfiles():
      try:
        shutil.rmtree(jsondir)
      except OSError:
        pass

    try:
      # Otherwise, it builds the JSON.
      rmfiles()
      self.assertFalse(os.path.exists(jsonfile))
      self.assertEqual(
          toolchain.currentfile('hello', ['data/curry'], zip=False)
        , os.path.abspath(jsonfile)
        )
      self.assertTrue(os.path.exists(jsonfile))
      self.assertEqualToFile(
          cytest.readfile('data/curry/.curry/sprite/hello.json')
        , goldenfile
        , GENERATE_GOLDENS
        )
      rmfiles()
      # Check loadModule.
      icur = toolchain.loadicurry('hello', ['data/curry'])
      icur.filename = None
      au = icurry.json.parse(cytest.readfile(goldenfile))
      self.assertEqual(icur, au)

    finally:
      rmfiles()

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

  def test_bad_alias(self):
    self.assertRaisesRegex(
        ValueError
      , r"cannot alias previously defined name 'head'"
      , lambda: curry.import_('head', alias=[('head', 'foo')])
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
    with _tempfile.TemporaryDirectory() as tmpdir:
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
