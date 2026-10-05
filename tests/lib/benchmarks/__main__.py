'''
The entry point: ``python -m benchmarks [run|compare|counters|split|history|
list] ...``.
Without a command, ``run`` is assumed.
'''

import sys

def main(argv=None):
  argv = list(sys.argv[1:] if argv is None else argv)
  from . import compare, counters, history, run, split
  if argv and argv[0] == 'compare':
    return compare.main(argv[1:])
  if argv and argv[0] == 'counters':
    return counters.main(argv[1:])
  if argv and argv[0] == 'split':
    return split.main(argv[1:])
  if argv and argv[0] == 'history':
    return history.main(argv[1:])
  if argv and argv[0] == 'list':
    return run.main(['--list'] + argv[1:])
  if argv and argv[0] == 'run':
    argv = argv[1:]
  return run.main(argv)

if __name__ == '__main__':
  sys.exit(main())
