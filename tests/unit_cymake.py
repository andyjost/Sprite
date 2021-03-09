import cytest # from ./lib; must be first
from curry import config, cymake
from curry.utility import _tempfile
import curry
import glob
import os
import shutil
import subprocess

SUBDIR = os.path.join('.curry', config.intermediate_subdir())

class CyMakeTestCase(cytest.TestCase):
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
        self.assertEqual(cymake.curryFilename(file_), curry_file)
        self.assertEqual(cymake.icurryFilename(file_), icy_file)
        self.assertEqual(cymake.jsonFilename(file_), json_file)

  def test_make_icurry_and_json(self):
    '''Test the conversion from .curry to .icy.'''
    for input_file in glob.glob('data/cymake/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with _tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        curry_file = os.path.join(tmpdir, filename)
        # Build .icy.
        ret = cymake.curry2icurry(curry_file, currypath=[], quiet=True)
        file_out = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        self.assertTrue(os.path.exists(file_out))
        self.assertEqual(ret, file_out)
        # Repeat -- no exception.
        ret = cymake.curry2icurry(curry_file, currypath=[], quiet=True)
        self.assertEqual(ret, file_out)

        # Build .json.
        ret = cymake.icurry2json(curry_file, currypath=[], compact=False, zip=False)
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        shutil.move(json_file, json_file + '.nocompact')

        # Build compacted .json.
        self.assertFalse(os.path.exists(json_file))
        ret = cymake.icurry2json(curry_file, currypath=[], compact=True, zip=False)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        if config.jq_tool() is not None:
          self.assertLess(
              os.stat(json_file).st_size
            , os.stat(json_file + '.nocompact').st_size
            )
        shutil.move(json_file, json_file + '.nozip')

        # Build compacted, compressed .json.
        ret = cymake.icurry2json(curry_file, currypath=[], compact=True, zip=True)
        self.assertTrue(os.path.exists(json_file + '.z'))
        self.assertEqual(ret, json_file + '.z')
        self.assertLess(
            os.stat(json_file + '.z').st_size
          , os.stat(json_file + '.nozip').st_size
          )

  def test_updateTarget(self):
    '''Test the updateTarget function.'''
    for input_file in glob.glob('data/cymake/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with _tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        icy_file = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        curry_file = os.path.join(tmpdir, filename)
        # Make .icy.  Returns None.
        ret = cymake.updateTarget(curry_file, json=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertEqual(ret, None)
        # Repeat
        ret = cymake.updateTarget(curry_file, json=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertIs(ret, None)

        # Make .json.  Returns the JSON file name.
        ret = cymake.updateTarget(curry_file, zip=False, is_sourcefile=True)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        # Repeat
        ret = cymake.updateTarget(curry_file, zip=False, is_sourcefile=True)
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

    for input_file in glob.glob('data/cymake/*.curry'):
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


