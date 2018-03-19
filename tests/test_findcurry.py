# Encoding: utf-8
import cytest
from curry import findfiles

class TestFindCurry(cytest.TestCase):
  def test_findFile(self):
    '''
    Tests the low-level findfile function with the following tree:

        data/filetree
        ├── a
        │   └── a.foo
        ├── b
        │   ├── a
        │   │   ├── a.curry
        │   │   └── a.foo
        │   └── a.curry
        └── c
            └── c.curry
    '''
    ff = findfiles.findfile
    self.assertEqual(list(ff(['data/filetree/a'], 'a')), [])
    self.assertEqual(
        list(ff(['data/filetree/b'], 'a'))
      , ['data/filetree/b/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/b/a'], 'a'))
      , ['data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/b'], 'a/a'))
      , ['data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(
            ['data/filetree/a', 'data/filetree/b', 'data/filetree/b/a']
          , 'a'
          ))
      , ['data/filetree/b/a.curry', 'data/filetree/b/a/a.curry']
      )
    self.assertEqual(
        list(ff(['data/filetree/a'], 'a', ['foo']))
      , ['data/filetree/a/a.foo']
      )
    self.assertEqual(
        list(ff(
            ['data/filetree/a', 'data/filetree/b/a']
          , 'a'
          , ['curry', 'foo']
          ))
      , [   'data/filetree/a/a.foo'
          , 'data/filetree/b/a/a.curry'
          , 'data/filetree/b/a/a.foo'
          ]
      )

