# Encoding: utf-8
from curry import getsource
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
    ff = getsource.findfiles
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
        getsource.findCurryModule('c', searchpaths=['data/filetree/c'])
      , os.path.abspath('data/filetree/c/c.curry')
      )
    self.assertEqual(
        getsource.findCurryModule('a', searchpaths=['data/filetree/b'])
      , os.path.abspath('data/filetree/b/a.curry')
      )
    # Under a/ there is no a.curry, but there is a .curry/a.json file.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        getsource.findCurryModule(
            'a'
          , searchpaths=['data/filetree/'+a_or_b for a_or_b in 'ab']
          )
      , os.path.abspath('data/filetree/a/.curry/a.json')
      )

  def test_getICurryForModule(self):
    self.assertEqual(
        getsource.getICurryForModule('a', ['data/filetree/a'])
      , os.path.abspath('data/filetree/a/.curry/a.json')
      )
    #
    jsonfile = 'data/curry/.curry/hello.json'
    try:
      os.remove(jsonfile)
    except OSError:
      pass
    self.assertFalse(os.path.exists(jsonfile))
    self.assertEqual(
        getsource.getICurryForModule('hello', ['data/curry'])
      , os.path.abspath(jsonfile)
      )
    self.assertEqual(
        open('data/curry/hello.json.au', 'r').read()
      , open('data/curry/.curry/hello.json', 'r').read()
      )

