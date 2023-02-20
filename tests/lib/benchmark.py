import curry, glob, os, subprocess, sys, timeit

OUTPUT_FILE = 'benchmark_data.py'
REPEAT = 1
EXEC = curry.config.sprite_exec()
CURRYDIR = os.path.normpath(curry.config.installed_path('../tests/data/curry/benchmarks'))
CURRYFILES = glob.glob(os.path.join(CURRYDIR, '*.curry'))

def run_curry(mode, cymodule):
  if mode in ['cxx', 'py']:
    cmd = ' '.join([
        'CURRYPATH=%s' % CURRYDIR, 'SPRITE_INTERPRETER_FLAGS=backend:%s' % mode
      , EXEC, '-tm', cymodule
      ])
    t = subprocess.check_output(['/bin/sh', '-c', cmd])
    t = float(t)
  elif mode == 'pakcs':
    cmd = 'cd %s; pakcs :l %s :eval main :q > /dev/null' % (CURRYDIR, cymodule)
    t = timeit.timeit(lambda: os.system(cmd), number=1)
  return t

def measure(cymodule):
  print(cymodule)
  # for mode in ['cxx']:
  for mode in ['cxx', 'pakcs']:
    sys.stdout.write('    %-16s ' % mode)
    sys.stdout.flush()
    best = float('inf')
    for _ in range(REPEAT):
      sec = run_curry(mode, cymodule)
      best = min(best, sec)
      sys.stdout.write('%7.3f  ' % sec)
      sys.stdout.flush()
    sys.stdout.write('  |  %0.3f\n' % best)

for cyfile in [os.path.split(f)[1] for f in CURRYFILES]:
  cymodule = cyfile[:-6]
  measure(cymodule)
