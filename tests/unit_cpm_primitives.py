"""Regression tests for the library readers used by CPM tools (#214)."""
import cytest # from ./lib; must be first
from pathlib import Path
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from unittest import mock
import curry
from curry import config


class TestCPMLibraryReaders(cytest.TestCase):
  def test_private_cpm_selects_sprite(self):
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as directory:
      prefix = Path(directory)
      launcher = prefix / 'curry/bin/cypm'
      launcher.parent.mkdir(parents=True)
      shutil.copyfile(root / 'src/export/bin/cypm.script', launcher)
      stock = prefix / 'stock/cypm'
      stock.parent.mkdir()
      stock.write_text('#!/bin/sh\nexit 0\n', encoding='ascii')
      stock.chmod(0o755)
      for options in ([], ['-d', 'CURRYBIN=chosen'],
                      ['--define=CURRYBIN=chosen'], ['-dCURRYBIN=chosen']):
        with self.subTest(options=options), \
             mock.patch.dict(os.environ, SPRITE_CPM_FORWARDED=''), \
             mock.patch.object(config, 'installed_path', return_value=str(stock.with_name('pakcs'))), \
             mock.patch.object(sys, 'argv', [str(launcher), *options, 'test']), \
             mock.patch('os.execv', side_effect=SystemExit(0)) as execute:
          with self.assertRaises(SystemExit):
            runpy.run_path(str(launcher), run_name='__main__')
          defaults = [] if options else ['-d', 'CURRYBIN=' + str(prefix / 'curry/bin/curry')]
          execute.assert_called_once_with(str(stock), [str(stock), *defaults, *options, 'test'])

  def test_library_home(self):
    distribution = curry.import_('Curry.Compiler.Distribution')
    home = Path(curry.eval(distribution.installDir).one())
    self.assertEqual(home, Path(config.prefix()) / 'curry')
    self.assertEqual(home / 'lib', Path(config.system_curry_path()))
    for name in ('curry', 'cleancurry', 'sprite-frontend', 'cypm'):
      self.assertTrue((home / 'bin' / name).is_file(), name)
    for name in config.syslibs():
      relative = Path(*name.split('.'))
      self.assertTrue((home / 'lib' / relative.with_suffix('.curry')).is_file())
      for suffix in ('.fcy', '.fint', '.acy'):
        self.assertTrue((home / 'lib/.curry' / config.analysis_subdir() /
                         relative.with_suffix(suffix)).is_file(), name + suffix)

  def test_legacy_package_source_lookup(self):
    # As with the CPM REPL test, dependencies live in a private test home.
    build = Path(__file__).resolve().parent.parent / 'object-root'
    home = Path(os.environ.get('CPM_TEST_HOME', str(build.resolve().parent / 'cpmhome')))
    packages = home / '.cpm/packages'
    sources = sorted(p / 'src' for p in packages.glob('*') if (p / 'src').is_dir() and not p.name.startswith('base-'))
    if not any((p / 'Analysis/Files.curry').is_file() for p in sources):
      self.skipTest('stock CPM reader packages are absent from the private test home')
    # Keep the readers' own path discovery independent of Sprite's Python path.
    # They must reach Prelude and Data.List through Distribution.installDir.
    search = os.pathsep.join(map(str, sources))
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      (root / 'Readers.curry').write_text('''module Readers where
import qualified AbstractCurry.Files as A
import qualified AbstractCurry.Select as A
import qualified FlatCurry.Files as F
import qualified FlatCurry.Goodies as F
import qualified Analysis.Files as C
main :: IO ()
main = mapM_ readModule ["Prelude", "Data.List"]
readModule m = do
  _ <- C.findModuleSourceInLoadPath m
  f <- F.readFlatCurry m
  i <- C.readNewestFlatCurryInt m
  a <- A.readCurry m
  print (F.progName f, F.progName i, A.progName a)
''', encoding='ascii')
      env = dict(os.environ, HOME=str(home), CURRYPATH=search,
                 LC_ALL='C.UTF-8', SPRITE_FRONTEND_WARNINGS='0')
      code = ("import curry, os; m = curry.import_('Readers.curry'); "
              "os.environ['SPRITE_FRONTEND'] = ''; curry.eval(m.main).one()")
      result = subprocess.run([sys.executable, '-c', code], cwd=root, env=env,
                              capture_output=True, text=True, timeout=300)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertEqual(result.stdout.splitlines(), [
          '("Prelude","Prelude","Prelude")',
          '("Data.List","Data.List","Data.List")'])
