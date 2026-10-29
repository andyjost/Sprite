'''The Curry 2.0.0 front end, distributed separately from Sprite.'''

import os
from pathlib import Path
import sys


def main():
  name = 'curry-frontend.exe' if sys.platform == 'win32' else 'curry-frontend'
  binary = Path(__file__).with_name('bin') / name
  if sys.platform == 'win32':
    # Windows has no exec that replaces the process: run the child and
    # return its status, so that pipes and exit codes reach the caller.
    import subprocess
    sys.exit(subprocess.run([str(binary), *sys.argv[1:]]).returncode)
  os.execv(str(binary), [str(binary), *sys.argv[1:]])
