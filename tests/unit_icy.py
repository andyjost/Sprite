import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
import subprocess
import sys
import tempfile


class TestREPLArguments(cytest.TestCase):
  def test_environment_through_eval(self):
    with tempfile.TemporaryDirectory() as directory:
      source = Path(directory) / 'REPLArguments.curry'
      source.write_text('module REPLArguments where\nimport System.Environment\n'
          'args :: IO [String]\nargs = getArgs\nname :: IO String\nname = getProgName\n')
      commands = ':load %s\n:eval args\n:eval name\n:quit\n' % source
      for command, inputs in (
          ([sys.executable, '-m', 'curry.tools.icy', ':load', str(source)],
           ':eval args\n:eval name\n:quit\n'),
          ([config.sprite_exec()], commands)):
        result = subprocess.run(command, input=inputs, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('> []', result.stdout)
        self.assertIn('> "REPLArguments"', result.stdout)
