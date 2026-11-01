import cytest # from ./lib; must be first
import curry
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
        '.cpm/packages/beta-1.0.0/src')]

  def test_sources(self):
    before = list(curry.path)
    with self.assertLogs('curry.config', level='INFO') as log:
      self.assertEqual(curry.cpm_path(self.root), self.expected())
    self.assertEqual(curry.path, before)
    self.assertIn('alpha-1.0.0, beta-1.0.0', '\n'.join(log.output))

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
    self.assertEqual(paths[:5], [str(self.root / 'override')] + self.expected())
    self.assertGreater(len(paths), 5)

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
