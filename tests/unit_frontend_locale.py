import cytest # from ./lib; must be first
import curry
from curry import config
from curry.toolchain import _frontend
import os, subprocess, sys, unittest
from unittest import mock


class TestFrontendLocale(cytest.TestCase):
  def test_environment(self):
    for locale in ('C', 'POSIX', '', 'en_US.ISO8859-1'):
      with mock.patch.dict(os.environ, {'LANG': locale}, clear=True):
        self.assertEqual(_frontend.frontend_environment()['LC_ALL'],
                         'UTF-8' if sys.platform == 'darwin' else 'C.UTF-8')
        self.assertNotIn('LC_ALL', os.environ)
    for key in ('LANG', 'LC_CTYPE', 'LC_ALL'):
      env = {'LANG': 'C', key: 'en_US.UTF-8'}
      with mock.patch.dict(os.environ, env, clear=True):
        self.assertEqual(_frontend.frontend_environment(), env)
    with mock.patch.dict(os.environ, {'LC_ALL': 'C', 'LANG': 'C.UTF-8'}, clear=True):
      self.assertEqual(_frontend.frontend_environment()['LC_ALL'],
                         'UTF-8' if sys.platform == 'darwin' else 'C.UTF-8')

  def test_platform_fallback(self):
    for platform, expected in (('darwin', 'UTF-8'), ('linux', 'C.UTF-8')):
      with mock.patch.object(_frontend.sys, 'platform', platform):
        with mock.patch.dict(os.environ, {'LANG': 'C'}, clear=True):
          self.assertEqual(_frontend.frontend_environment()['LC_ALL'], expected)

  def test_clean_child(self):
    if config.curry_frontend() is None:
      self.skipTest('the Curry front end is not configured')
    env = {key: os.environ[key] for key in ('PATH', 'HOME') if key in os.environ}
    env['LANG'] = 'C'
    # Keep Python's startup locale coercion from masking the front-end fix.
    env['PYTHONCOERCECLOCALE'] = '0'
    env['PYTHONIOENCODING'] = 'utf-8'
    code = ('import sys; sys.path.insert(0, %r); ' %
            os.path.dirname(os.path.dirname(curry.__file__))) + (
            'import os; assert not os.environ.get("LC_ALL"); '
            'assert not os.environ.get("LC_CTYPE"); '
            'import curry; M = curry.compile(\'main :: String\\nmain = "h\\u00e9llo"\'); '
            'print(curry.eval(M.main).one())')
    child = subprocess.run([sys.executable, '-c', code], env=env,
                           capture_output=True, encoding='utf-8')
    self.assertEqual(child.returncode, 0, child.stderr)
    self.assertEqual(child.stdout.strip(), 'h\u00e9llo')
