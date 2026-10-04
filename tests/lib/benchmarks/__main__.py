'''
The entry point: ``python -m benchmarks [run|compare|counters|list] ...``.
Without a command, ``run`` is assumed.
'''

import sys

def main(argv=None):
  argv = list(sys.argv[1:] if argv is None else argv)
  from . import compare, counters, run
  if argv and argv[0] == 'compare':
    return compare.main(argv[1:])
  if argv and argv[0] == 'counters':
    return counters.main(argv[1:])
  if argv and argv[0] == 'list':
    return run.main(['--list'] + argv[1:])
  if argv and argv[0] == 'run':
    argv = argv[1:]
  return run.main(argv)

if __name__ == '__main__':
  sys.exit(main())
