'''The Curry 2.0.0 front end, distributed separately from Sprite.'''

import os
from pathlib import Path
import sys


def main():
  binary = Path(__file__).with_name('bin') / 'curry-frontend'
  os.execv(str(binary), [str(binary), *sys.argv[1:]])
