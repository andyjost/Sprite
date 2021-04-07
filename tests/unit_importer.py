# Encoding: utf-8
import cytest # from ./lib; must be first
from curry import config, importer
from curry import icurry
from curry.utility import filesys
from curry.utility import _tempfile
import curry
import glob
import os
import shutil
import subprocess
import time

GENERATE_GOLDENS = False
SUBDIR = os.path.join('.curry', config.intermediate_subdir())

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

  def test_findCurry(self):
    self.assertEqual(
        importer.findCurryModule('c', currypath=['data/findFile/c'])
      , os.path.abspath('data/findFile/c/c.curry')
      )
    self.assertEqual(
        importer.findCurryModule('a', currypath=['data/findFile/b'])
      , os.path.abspath('data/findFile/b/a.curry')
      )
    # Under a/ there is no a.curry, but there is .curry/sprite/a.json.
    # It should be found before b/a.curry is located.
    self.assertEqual(
        importer.findCurryModule(
            'a'
          , currypath=['data/findFile/'+a_or_b for a_or_b in 'ab']
          )
      , os.path.abspath('data/findFile/a/.curry/sprite/a.json')
      )

  def test_getICurryForModule(self):
    '''Check that curry2json is invoked to produce ICurry-JSON files.'''
    # If the JSON file already exists, this should find it, just like
    # findCurryModule does.
    self.assertEqual(
        importer.findOrBuildICurry('a', ['data/findFile/a'], zip=False)
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
          importer.findOrBuildICurry('hello', ['data/curry'], zip=False)
        , os.path.abspath(jsonfile)
        )
      self.assertTrue(os.path.exists(jsonfile))
      self.compareEqualToFile(
          open('data/curry/.curry/sprite/hello.json').read()
        , goldenfile
        , GENERATE_GOLDENS
        )
      rmfiles()
      # Check loadModule.
      icur = importer.loadModule('hello', ['data/curry'])
      icur.filename = None
      au = icurry.json.parse(open(goldenfile, 'r').read())
      self.assertEqual(icur, au)

    finally:
      rmfiles()

  def test_illegal_name(self):
    self.assertRaisesRegexp(
        ValueError, r"'kiel/rev' is not a legal module name."
      , lambda: curry.import_('kiel/rev')
      )
    self.assertRaisesRegexp(
        ValueError, r"'.' is not a legal module name."
      , lambda: curry.import_('.')
      )
    self.assertRaisesRegexp(
        ValueError, r"'..' is not a legal module name."
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
      self.assertTrue(filesys.newer(b, a))
      self.assertFalse(filesys.newer(a, b))
    #
    self.assertTrue(
        filesys.newer('data/curry/hello.curry', 'this_file_does_not_exist')
      )

class TestMake(cytest.TestCase):
  '''Tests for the make-like features to generate ICurry and JSON.'''

  def test_filename_funcs(self):
    '''
    It should be possible to derive any intermediate file name from any .curry, .icy,
    or .json file, with or without an additional .gz extension.
    '''
    prefixes = ['', '/path/to', 'a/b', '.', '..']
    for prefix in prefixes:
      curry_file = os.path.join(prefix, 'foo.curry')
      icy_file = os.path.join(prefix, SUBDIR, 'foo.icy')
      json_file = os.path.join(prefix, SUBDIR, 'foo.json')
      files = [curry_file, icy_file, json_file]
      files += [name + '.z' for name in files]
      for file_ in files:
        self.assertEqual(importer.curryFilename(file_), curry_file)
        self.assertEqual(importer.icurryFilename(file_), icy_file)
        self.assertEqual(importer.jsonFilename(file_), json_file)

  def test_make_icurry_and_json(self):
    '''Test the conversion from .curry to .icy.'''
    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with _tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        curry_file = os.path.join(tmpdir, filename)
        # Build .icy.
        ret = importer.curry2icurry(curry_file, currypath=[], quiet=True)
        file_out = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        self.assertTrue(os.path.exists(file_out))
        self.assertEqual(ret, file_out)
        # Repeat -- no exception.
        ret = importer.curry2icurry(curry_file, currypath=[], quiet=True)
        self.assertEqual(ret, file_out)

        # Build .json.
        ret = importer.icurry2json(curry_file, currypath=[], compact=False, zip=False)
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        shutil.move(json_file, json_file + '.nocompact')

        # Build compacted .json.
        self.assertFalse(os.path.exists(json_file))
        ret = importer.icurry2json(curry_file, currypath=[], compact=True, zip=False)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        if config.jq_tool() is not None:
          self.assertLess(
              os.stat(json_file).st_size
            , os.stat(json_file + '.nocompact').st_size
            )
        shutil.move(json_file, json_file + '.nozip')

        # Build compacted, compressed .json.
        ret = importer.icurry2json(curry_file, currypath=[], compact=True, zip=True)
        self.assertTrue(os.path.exists(json_file + '.z'))
        self.assertEqual(ret, json_file + '.z')
        self.assertLess(
            os.stat(json_file + '.z').st_size
          , os.stat(json_file + '.nozip').st_size
          )

  def test_findOrBuildICurry(self):
    '''Test the findOrBuildICurry function.'''
    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with _tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        icy_file = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        curry_file = os.path.join(tmpdir, filename)
        # Make .icy.  Returns None.
        ret = importer.findOrBuildICurry(curry_file, json=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertEqual(ret, None)
        # Repeat
        ret = importer.findOrBuildICurry(curry_file, json=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertIs(ret, None)

        # Make .json.  Returns the JSON file name.
        ret = importer.findOrBuildICurry(curry_file, zip=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        # Repeat
        ret = importer.findOrBuildICurry(curry_file, zip=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)

  def test_sprite_make(self):
    '''Test the sprite-make program.'''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    def sprite_make(*args):
      return subprocess.check_output((makeprg,) + args)

    self.assertEqual(sprite_make('--subdir'), SUBDIR)
    self.assertEqual(sprite_make('-S'), SUBDIR)

    maninfo = sprite_make('--man')
    self.assertEqual(sprite_make('-M'), maninfo)
    self.assertGreater(len(maninfo), 100)
    self.assertIn('Examples:', maninfo)
    self.assertIn('CURRYPATH', maninfo)
    self.assertIn('SPRITE_LOG_LEVEL', maninfo)

    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with _tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        curry_file = os.path.join(tmpdir, filename)
        icy_file = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')

        # Make .json and remove .icy.
        sprite_make('--json', '-t', curry_file)
        self.assertFalse(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file))
        os.unlink(json_file)

        # Make .icy.
        sprite_make('--icy', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertFalse(os.path.exists(json_file))

        # Make .json and keep .icy.
        sprite_make('--json', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file))

        # Make .json.z.  Tidy will not remove the .icy.
        sprite_make('--json', '-zt', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file + '.z'))
        os.unlink(icy_file)
        os.unlink(json_file)
        shutil.move(json_file + '.z', json_file + '.z.nocompact')

        # Make .json.z with all options.
        sprite_make('--json', '-czt', curry_file)
        self.assertFalse(os.path.exists(icy_file))
        self.assertFalse(os.path.exists(json_file))
        self.assertTrue(os.path.exists(json_file + '.z'))
        self.assertLess(
            os.stat(json_file + '.z').st_size
          , os.stat(json_file + '.z.nocompact').st_size
          )


