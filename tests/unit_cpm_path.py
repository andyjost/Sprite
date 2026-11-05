import cytest # from ./lib; must be first
import curry
from curry import config
from unittest import mock
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path


class TestCpmPath(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name) / 'project'
    shutil.copytree('data/cpm/project', self.root)

  def expected(self):
    return [str(self.root / p) for p in (
        'app', 'extra', '.cpm/packages/alpha-1.0.0/lib',
        '.cpm/packages/beta-1.0.0/src',
        '.cpm/packages/setfunctions-1.0.0/src')]

  def test_sources(self):
    before = list(curry.path)
    with self.assertLogs('curry.config', level='INFO') as log:
      self.assertEqual(curry.cpm_path(self.root), self.expected())
    self.assertEqual(curry.path, before)
    self.assertIn('alpha-1.0.0, beta-1.0.0, setfunctions-1.0.0', '\n'.join(log.output))

  def test_no_project(self):
    (self.root / 'package.json').unlink()
    self.assertEqual(curry.cpm_path(self.root), [])

  def test_no_packages(self):
    shutil.rmtree(self.root / '.cpm')
    self.assertEqual(curry.cpm_path(self.root), [])

  def child(self, code, **extra):
    env = dict(os.environ, CURRYPATH=str(self.root / 'override'), **extra)
    return subprocess.run([sys.executable, '-c', code], cwd=self.root,
                          env=env, text=True, capture_output=True, check=True).stdout

  def test_import_order_and_once(self):
    code = ('import curry, json, os; before = list(curry.path); '
            'os.chdir(".."); curry.reset(); '
            'assert before == curry.path; print(json.dumps(curry.path))')
    paths = json.loads(self.child(code, SPRITE_CPM_PATH='1'))
    # The child names the working directory as the system resolves it; macOS
    # reaches the temporary directory through a symbolic link.
    real = lambda ps: [os.path.realpath(p) for p in ps]
    self.assertEqual(real(paths[:6]), real([str(self.root / 'override')] + self.expected()))
    self.assertGreater(len(paths), 6)

  def test_switch(self):
    paths = json.loads(self.child('import curry, json; print(json.dumps(curry.path))',
                                  SPRITE_CPM_PATH='0'))
    for path in self.expected():
      self.assertNotIn(path, paths)

  def test_import_both_packages(self):
    output = self.child('import curry; M = curry.import_("CpmMain"); '
                        'print(curry.eval(M.main).one())', SPRITE_CPM_PATH='1')
    self.assertEqual(output.strip(), '42')

  def test_bad_metadata(self):
    (self.root / 'package.json').write_text('{', encoding='ascii')
    with self.assertLogs('curry.config', level='WARNING'):
      paths = curry.cpm_path(self.root)
    self.assertEqual(paths, self.expected()[2:])

  def test_installed_library_collision(self):
    self.assertEqual(curry.cpm_path(self.root), self.expected())
    paths = json.loads(self.child('import curry, json; print(json.dumps(curry.path))',
                                 SPRITE_CPM_PATH='1'))
    self.assertIn(os.path.realpath(self.expected()[-1]),
                  [os.path.realpath(path) for path in paths])

  def test_discovered_library_copy(self):
    source = Path(self.expected()[2]) / 'Data/Char.curry'
    source.parent.mkdir(parents=True)
    shutil.copyfile(config.installed_path('curry', 'lib', 'Data/Char.curry'), source)
    output = self.child('import curry; M = curry.import_("Data.Char"); '
                        'print(M.__file__)', SPRITE_CPM_PATH='1')
    self.assertEqual(Path(output.strip()).resolve(), source.resolve())

  def test_discovered_reserved_copy(self):
    source = Path(self.expected()[2]) / 'Prelude.curry'
    shutil.copyfile(config.installed_path('curry', 'lib', 'Prelude.curry'), source)
    code = ('import curry, os; assert %r in [os.path.realpath(p) for p in curry.path]; '
            'curry.import_("Prelude")') % os.path.realpath(source.parent)
    with self.assertRaises(subprocess.CalledProcessError) as caught:
      self.child(code, SPRITE_CPM_PATH='1')
    self.assertIn('has the name of a module the runtime implements', caught.exception.stderr)
    self.assertIn('cannot be replaced', caught.exception.stderr)

  def test_unreadable_packages(self):
    with mock.patch.object(config.os, 'listdir', side_effect=PermissionError('denied')):
      with self.assertLogs('curry.config', level='DEBUG'):
        self.assertEqual(curry.cpm_path(self.root), [])

  @cytest.posix_only('a removed working directory')
  def test_removed_cwd(self):
    code = ('import os, tempfile; root = tempfile.mkdtemp(); '
            'os.chdir(root); os.rmdir(root); import curry; assert curry.path')
    self.child(code, SPRITE_CPM_PATH='1')

  def test_duplicate_paths(self):
    env = dict(os.environ, CURRYPATH=os.pathsep.join(self.expected()),
               SPRITE_CPM_PATH='1')
    child = subprocess.run([sys.executable, '-c',
        'import curry, json; print(json.dumps(curry.path))'],
        cwd=self.root, env=env, text=True, capture_output=True, check=True)
    paths = json.loads(child.stdout)
    self.assertEqual(paths[:5], self.expected())
    self.assertEqual(len(paths), len(set(paths)))
