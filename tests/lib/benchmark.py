import curry, glob, os, re, subprocess, sys, timeit

OUTPUT_FILE = 'benchmark_data.py'
REPEAT = 1
EXEC = curry.config.sprite_exec()
CURRYDIR = os.path.normpath(curry.config.installed_path('../tests/data/curry/benchmarks'))
CURRYFILES = sorted(glob.glob(os.path.join(CURRYDIR, '*.curry')))
PAKCSTIME = re.compile(r'Execution time: (\d+) msec')
LOG = 'benchmark.log'

def run_curry(mode, cymodule):
  if mode in ['cxx', 'py']:
    cmd = ' '.join([
        'CURRYPATH=%s' % CURRYDIR, 'SPRITE_INTERPRETER_FLAGS=backend:%s' % mode
      , EXEC, '-tm', cymodule
      ])
    sec = subprocess.check_output(['/bin/zsh', '-c', cmd])
    return float(sec)
  elif mode == 'pakcs':
    cmd = 'cd %s; pakcs :set +time :l %s :eval main :q' % (CURRYDIR, cymodule)
    text = subprocess.check_output(['/bin/zsh', '-c', cmd])
    msec = re.search(PAKCSTIME, str(text)).group(1)
    return float(msec) / 1000

def measure(cymodule):
  print(cymodule)
  for mode in ['cxx']:
  # for mode in ['cxx', 'pakcs']:
    sys.stdout.write('    %-16s ' % mode)
    sys.stdout.flush()
    best = float('inf')
    for _ in range(REPEAT):
      try:
        sec = run_curry(mode, cymodule)
      except Exception as e:
        sys.stdout.write('%-7s  ' % 'fail')
      else:
        best = min(best, sec)
        sys.stdout.write('%7.3f  ' % sec)
      sys.stdout.flush()
    if REPEAT > 1:
      sys.stdout.write('  |  %0.3f\n' % best)
    else:
      sys.stdout.write('\n')

for cyfile in [os.path.split(f)[1] for f in CURRYFILES]:
  cymodule = cyfile[:-6]
  # if cymodule.startswith('ReverseBuiltin'):
  measure(cymodule)
