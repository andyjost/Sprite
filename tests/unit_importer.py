# Encoding: utf-8
import cytest # from ./lib; must be first
from curry import icurry
from curry import importer
from curry.utility import _tempfile
import curry
import os
import shutil
import time

GENERATE_GOLDENS = False

class TestFindCurry(cytest.TestCase):
  def test_findFile(self):
    '''
    Tests the low-level findfile function with the following tree:

        data/findFile
        ├── a
        │   ├── a.foo
        │   └── .curry
        │       └── a.json
        ├── b
        │   ├── a
        │   │   ├── a.curry
        │   │   └── a.foo
        │   └── a.curry
        └── c
            ├── a
            └── c.curry
    '''
    ff = importer.findfiles
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

  def test_findCurryModule(self):
    self.assertEqual(
        importer.findCurryModule('c', currypath=['data/findFile/c'])
      , os.path.abspath('data/findFile/c/c.curry')
      )
    self.assertEqual(
        importer.findCurryModule('a', currypath=['data/findFile/b'])
      , os.path.abspath('data/findFile/b/a.curry')
      )
    # Under a/ there is no a.curry, but there is a .curry/a.json file.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        importer.findCurryModule(
            'a'
          , currypath=['data/findFile/'+a_or_b for a_or_b in 'ab']
          )
      , os.path.abspath('data/findFile/a/.curry/a.json')
      )

  def test_getICurryForModule(self):
    '''Check that curry2json is invoked to produce ICurry-JSON files.'''
    # If the JSON file already exists, this should find it, just like
    # findCurryModule does.
    self.assertEqual(
        importer.findOrBuildICurryForModule('a', ['data/findFile/a'])
      , os.path.abspath('data/findFile/a/.curry/a.json')
      )

    jsondir = 'data/curry/.curry'
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
          importer.findOrBuildICurryForModule('hello', ['data/curry'])
        , os.path.abspath(jsonfile)
        )
      self.assertTrue(os.path.exists(jsonfile))
      self.compareEqualToFile(
          open('data/curry/.curry/hello.json').read()
        , goldenfile
        , GENERATE_GOLDENS
        )
      rmfiles()
      # Check getICurryForModule.  It just parses the file found by
      # findOrBuildICurryForModule.
      icur = importer.getICurryForModule('hello', ['data/curry'])
      icur.filename = None
      au = icurry.parse(open(goldenfile, 'r').read())
      assert len(au) == 1
      self.assertEqual(icur, au[0])

    finally:
      rmfiles()

  def test_illegal_name(self):
    self.assertRaisesRegexp(
        ValueError, r'"kiel/rev" is not a legal module name.'
      , lambda: curry.import_('kiel/rev')
      )
    self.assertRaisesRegexp(
        ValueError, r'"." is not a legal module name.'
      , lambda: curry.import_('.')
      )
    self.assertRaisesRegexp(
        ValueError, r'".." is not a legal module name.'
      , lambda: curry.import_('..')
      )

  def test_bad_alias(self):
    self.assertRaisesRegexp(
        ValueError
      , r"cannot alias previously defined name 'head'"
      , lambda: curry.import_('head', alias=[('head', 'foo')])
      )

  def test_import_with_currypath(self):
    self.assertRaisesRegexp(
        ValueError
      , r"module \"import_test\" not found"
      , lambda: curry.import_('import_test')
      )
    self.assertRaisesRegexp(
        TypeError
      , r"'currypath' must be a string or list, got 'int'."
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
      self.assertTrue(importer.newer(b, a))
      self.assertFalse(importer.newer(a, b))
    #
    self.assertTrue(
        importer.newer('data/curry/hello.curry', 'this_file_does_not_exist')
      )
