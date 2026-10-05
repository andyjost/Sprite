'''The entry point: ``python -m testrunner [options] [PATTERN ...]``.'''

import sys
from .cli import main

if __name__ == '__main__':
  sys.exit(main())
