# Encoding: utf-8
from curry import icurry
from curry import importer
import cytest
import os
import shutil

class TestFindCurry(cytest.TestCase):
  def test_findFile(self):
    '''
    Tests the low-level findfile function with the following tree:

        data/filetree
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
          , searchpaths=['data/filetree/a']
          ))
      , []
      )
    self.assertEqual(list(ff(['data/filetree/a'], ['a.curry'])), [])
    self.assertEqual(
        list(ff(['data/filetree/b'], ['a.curry']))
      , ['data/filetree/b/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/b/a'], ['a.curry']))
      , ['data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/b'], ['a/a.curry']))
      , ['data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(
            ['data/filetree/a', 'data/filetree/b', 'data/filetree/b/a']
          , ['a.curry']
          ))
      , ['data/filetree/b/a.curry', 'data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/a'], ['a.foo']))
      , ['data/filetree/a/a.foo']
      )
    self.assertEqual(
        list(ff(
            ['data/filetree/a', 'data/filetree/b/a']
          , ['a.curry', 'a.foo']
          ))
      , [   'data/filetree/a/a.foo'
          , 'data/filetree/b/a/a.curry'
          , 'data/filetree/b/a/a.foo'
          ]
      )
    self.assertEqual(
        list(ff(['data/filetree/c'], ['a']))
      , ['data/filetree/c/a']
      )

  def test_findCurryModule(self):
    self.assertEqual(
        importer.findCurryModule('c', searchpaths=['data/filetree/c'])
      , os.path.abspath('data/filetree/c/c.curry')
      )
    self.assertEqual(
        importer.findCurryModule('a', searchpaths=['data/filetree/b'])
      , os.path.abspath('data/filetree/b/a.curry')
      )
    # Under a/ there is no a.curry, but there is a .curry/a.json file.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        importer.findCurryModule(
            'a'
          , searchpaths=['data/filetree/'+a_or_b for a_or_b in 'ab']
          )
      , os.path.abspath('data/filetree/a/.curry/a.json')
      )

  def test_getICurryForModule(self):
    '''Check that curry2json is invoked to produce ICurry-JSON files.'''
    # If the JSON file already exists, this should find it, just like
    # findCurryModule does.
    self.assertEqual(
        importer.findOrBuildICurryForModule('a', ['data/filetree/a'])
      , os.path.abspath('data/filetree/a/.curry/a.json')
      )
    # Otherwise, it builds the JSON.
    jsondir = 'data/curry/.curry'
    jsonfile = os.path.join(jsondir, 'hello.json')
    goldenfile = 'data/curry/hello.json.au'
    def rmfiles():
      try:
        shutil.rmtree(jsondir)
      except OSError:
        pass
    try:
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
      # Finally, check getICurryForModule.  It just parses the file found by
      # findOrBuildICurryForModule.
      icur = importer.getICurryForModule('hello', ['data/curry'])
      au = icurry.parse(open(goldenfile, 'r').read())
      self.assertEqual(icur, au)
    finally:
      rmfiles()

