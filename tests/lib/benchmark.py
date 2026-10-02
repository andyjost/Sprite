'''
Time the Curry benchmark programs under tests/data/curry/benchmarks.

Usage, from the tests directory:

    ./run_benchmarks [options] [MODULE ...]

or, from anywhere:

    install/bin/python tests/lib/benchmark.py [options] [MODULE ...]

MODULE names select programs (shell-style patterns are allowed).  With no
MODULE, every top-level program runs.  The default backend is cxx.  The pakcs
backend needs the --pakcs option.
'''

import argparse
import fnmatch
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CURRYDIR = os.path.normpath(os.path.join(HERE, '..', 'data', 'curry', 'benchmarks'))
DEFAULT_SPRITE_HOME = os.path.normpath(os.path.join(HERE, '..', '..', 'install'))
PAKCSTIME = re.compile(r'Execution time: (\d+) msec')
BACKENDS = ['cxx', 'py', 'pakcs']


def all_modules():
  files = sorted(glob.glob(os.path.join(CURRYDIR, '*.curry')))
  return [os.path.basename(f)[:-len('.curry')] for f in files]


def select_modules(patterns):
  modules = all_modules()
  if not patterns:
    return modules
  selected = []
  for pattern in patterns:
    matches = fnmatch.filter(modules, pattern)
    if not matches:
      sys.exit('benchmark: no program matches %r' % pattern)
    selected.extend(m for m in matches if m not in selected)
  return selected


def sprite_exec(args):
  home = args.sprite_home or os.environ.get('SPRITE_HOME') or DEFAULT_SPRITE_HOME
  return os.path.join(home, 'bin', 'sprite-exec')


def run_sprite(args, backend, module):
  env = dict(os.environ)
  env['CURRYPATH'] = CURRYDIR
  env['SPRITE_INTERPRETER_FLAGS'] = 'backend:%s' % backend
  cmd = [sprite_exec(args), '-t', '-m', module]
  result = subprocess.run(
      cmd, env=env, cwd=CURRYDIR, capture_output=True, text=True, check=True
    , timeout=args.timeout
    )
  return float(result.stdout.strip().splitlines()[-1])


def run_pakcs(args, module):
  env = dict(os.environ)
  env['CURRYPATH'] = CURRYDIR
  cmd = [args.pakcs, ':set', '+time', ':l', module, ':eval', 'main', ':q']
  result = subprocess.run(
      cmd, env=env, cwd=CURRYDIR, capture_output=True, text=True, check=True
    , timeout=args.timeout
    )
  match = PAKCSTIME.search(result.stdout)
  if match is None:
    raise RuntimeError('no execution time in PAKCS output')
  return float(match.group(1)) / 1000


def run_one(args, backend, module):
  if backend == 'pakcs':
    return run_pakcs(args, module)
  return run_sprite(args, backend, module)


def measure(args, module):
  print(module)
  for backend in args.backend:
    sys.stdout.write('    %-8s' % backend)
    sys.stdout.flush()
    best = float('inf')
    for _ in range(args.repeat):
      try:
        sec = run_one(args, backend, module)
      except Exception as e:
        sys.stdout.write('  %7s' % 'fail')
        if args.verbose:
          sys.stdout.write('  (%s)' % e)
      else:
        best = min(best, sec)
        sys.stdout.write('  %7.3f' % sec)
      sys.stdout.flush()
    if args.repeat > 1 and best != float('inf'):
      sys.stdout.write('  |  best %0.3f' % best)
    sys.stdout.write('\n')
    sys.stdout.flush()


def parse_args(argv):
  parser = argparse.ArgumentParser(
      prog='run_benchmarks'
    , description='Time the Curry benchmark programs.  Times are in seconds.'
    )
  parser.add_argument(
      'module', nargs='*', metavar='MODULE'
    , help='program to run (shell-style patterns allowed); default: all'
    )
  parser.add_argument(
      '-b', '--backend', action='append', choices=BACKENDS, default=None
    , help='backend to time; repeat for several [default: cxx]'
    )
  parser.add_argument(
      '-r', '--repeat', type=int, default=1, metavar='N'
    , help='run each program N times and report the best [default: 1]'
    )
  parser.add_argument(
      '--pakcs', metavar='EXE', default=None
    , help='PAKCS executable; required for the pakcs backend'
    )
  parser.add_argument(
      '--sprite-home', metavar='DIR', default=None
    , help='Sprite installation [default: $SPRITE_HOME or the staged install/]'
    )
  parser.add_argument(
      '--timeout', type=float, default=None, metavar='SEC'
    , help='kill a run after SEC seconds and report it as a failure'
    )
  parser.add_argument(
      '-l', '--list', action='store_true', help='list the programs and exit'
    )
  parser.add_argument(
      '-v', '--verbose', action='store_true', help='show the reason for a failure'
    )
  args = parser.parse_args(argv)
  if args.backend is None:
    args.backend = ['cxx']
  if 'pakcs' in args.backend and not args.pakcs:
    parser.error('the pakcs backend requires --pakcs EXE')
  if args.repeat < 1:
    parser.error('--repeat must be at least 1')
  return args


def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  modules = select_modules(args.module)
  if args.list:
    print('\n'.join(modules))
    return 0
  exe = sprite_exec(args)
  if any(b != 'pakcs' for b in args.backend) and not os.access(exe, os.X_OK):
    sys.exit('benchmark: sprite-exec not found at %s' % exe)
  print('programs: %s' % CURRYDIR)
  print('backends: %s' % ', '.join(args.backend))
  for module in modules:
    measure(args, module)
  return 0


if __name__ == '__main__':
  sys.exit(main())
