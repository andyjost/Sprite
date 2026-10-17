'''Issue #147: every session flag route uses the same validator.'''
import cytest # from ./lib; must be first
import curry
from curry.interpreter import Interpreter
import os
import subprocess
import sys
import unittest


class TestIssue147(cytest.TestCase):
  def test_unknown_flag_is_refused_on_every_route(self):
    with self.assertRaises(TypeError):
      curry.flags['nosuch'] = 1
    for call in (lambda: curry.reset(nosuch=1),
                 lambda: Interpreter(flags={'nosuch': 1})):
      with self.assertRaises(curry.FlagError) as caught:
        call()
      self.assertTrue(str(caught.exception).startswith("'nosuch' is not a flag;"))
    run = subprocess.run([sys.executable, '-c', 'import curry'],
        env=dict(os.environ, SPRITE_INTERPRETER_FLAGS='nosuch:1'),
        capture_output=True, text=True)
    self.assertNotEqual(run.returncode, 0)
    self.assertEqual(len(run.stderr.splitlines()), 1)
    self.assertTrue(run.stderr.startswith("FlagError: 'nosuch' is not a flag;"))


if __name__ == '__main__':
  unittest.main()
