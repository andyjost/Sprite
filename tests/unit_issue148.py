'''Issue #148: malformed environment flags name the item, without a traceback.'''
import cytest # from ./lib; must be first
import curry
import os
import subprocess
import sys
import unittest


class TestIssue148(cytest.TestCase):
  def test_missing_colon_is_one_flag_error_sentence(self):
    run = subprocess.run([sys.executable, '-c', 'import curry'],
        env=dict(os.environ, SPRITE_INTERPRETER_FLAGS='debug'),
        capture_output=True, text=True)
    self.assertNotEqual(run.returncode, 0)
    self.assertEqual(run.stderr, "FlagError: 'debug' is not a flag setting; expected name:value\n")

  def test_value_after_colon_is_accepted(self):
    code = "import curry; print(curry.flags['debug'])"
    run = subprocess.run([sys.executable, '-c', code],
        env=dict(os.environ, SPRITE_INTERPRETER_FLAGS='debug:true'),
        check=True, capture_output=True, text=True)
    self.assertEqual(run.stdout, 'True\n')


if __name__ == '__main__':
  unittest.main()
