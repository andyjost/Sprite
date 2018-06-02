# Encoding: utf-8
import cytest # from ./lib; must be first
import curry
from curry import icurry
from curry import importer
import os
import shutil

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
      self.assertEqual(
          open(goldenfile, 'r').read()
        , open('data/curry/.curry/hello.json', 'r').read()
        )
      rmfiles()
      # Check getICurryForModule.  It just parses the file found by
      # findOrBuildICurryForModule.
      icur = importer.getICurryForModule('hello', ['data/curry'])
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
