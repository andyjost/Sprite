'''
Compatibility entry point of the benchmark harness.

The harness lives in the ``benchmarks`` package beside this file.  This
module forwards to it, so ``python -m benchmark`` and a direct call of this
file keep working:

    install/bin/python tests/lib/benchmark.py [run|compare|list] ...

See ``benchmarks/__init__.py`` for the usage.
'''

import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmarks.__main__ import main

if __name__ == '__main__':
  sys.exit(main())
