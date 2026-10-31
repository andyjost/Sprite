'''System library checks accept equivalent paths and report import failures.'''
import cytest # from ./lib; must be first
import curry, os, subprocess, sys, tempfile


class TestIssue174(cytest.TestCase):
  def setUp(self):
    self.env = dict(os.environ, SPRITE_HOME=curry.config.prefix(),
        PYTHONPATH=os.path.dirname(os.path.dirname(curry.__file__)), CURRYPATH='')
    self.env.pop('SPRITE_DISABLE_SYSLIB_CHECKS', None)

  def child(self, code='import curry', **env):
    command = cytest.limit_prefix(address_space=6 << 30, timeout=30)
    return subprocess.run(command + [sys.executable, '-B', '-c', code],
        env=dict(self.env, **env), capture_output=True, text=True, timeout=40)

  def test_parent_segment(self):
    home = os.path.join(self.env['SPRITE_HOME'], 'curry', os.pardir)
    proc = self.child(SPRITE_HOME=home)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, '')
    self.assertEqual(proc.stderr, '')

  def test_shadowed_prelude(self):
    with tempfile.TemporaryDirectory() as directory:
      with open(os.path.join(directory, 'Prelude.curry'), 'w'):
        pass
      path = os.pathsep.join([directory, curry.config.system_curry_path()])
      proc = self.child(CURRYPATH=path)
      self.assertEqual(proc.returncode, 1, proc.stderr)
      self.assertEqual(proc.stdout, '')
      self.assertIn("ImportError: System library 'Prelude.curry' is shadowed", proc.stderr)
      self.assertIn('The CURRYPATH is', proc.stderr)
      self.assertIn(repr(directory)[1:-1], proc.stderr)
      self.assertIn('SPRITE_DISABLE_SYSLIB_CHECKS', proc.stderr)
      proc = self.child(CURRYPATH=path, SPRITE_DISABLE_SYSLIB_CHECKS='1')
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertEqual(proc.stdout, '')
      self.assertEqual(proc.stderr, '')

  def test_missing_system_library(self):
    # Keep the installation intact: simulate no match, or only a user copy.
    for found in ([], [os.path.join('user', 'Prelude.curry')]):
      with self.subTest(found=found):
        proc = self.child('''
import curry
from unittest import mock
with mock.patch('curry.config.syslibs', return_value=['Prelude']), \\
     mock.patch('curry.utility.filesys.findfiles', return_value=%r):
  curry.config.verify_syslibs()
''' % found)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("ImportError: System library 'Prelude.curry' was not found", proc.stderr)
        self.assertIn('The CURRYPATH is', proc.stderr)
        self.assertIn('SPRITE_DISABLE_SYSLIB_CHECKS', proc.stderr)
