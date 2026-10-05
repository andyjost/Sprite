'''
The command line and the course of one run: the selection, the jobs, the
budget, the prepare pass, the scheduler, the summary, the manifest update,
and the exit status.
'''

import argparse, itertools, os, resource, shutil, sys
from . import (
    BACKENDS, BACKSTOP, BACKSTOP_FACTOR, DEFAULT_CAP, DEFAULT_FAST_SECONDS
  , DEFAULT_JOBS, DEFAULT_MEM_FRACTION, DEFAULT_SPRITE_HOME, DEFAULT_TIMEOUT
  , GIB, LOGDIR, MANIFEST_FILE, TESTDIR
  )
from . import prepare, procs, report, selection
from .manifest import Manifest
from .scheduler import Job, Scheduler

__all__ = [
    'backstop_prefix', 'environment', 'exit_status', 'main', 'parse_args'
  , 'prepare_pass_jobs', 'test_job'
  ]

# The cap of a directory of the prepare pass, and the seconds it may take
# per module before it counts as hung.
PREPARE_CAP = 3 * GIB
PREPARE_SECONDS_PER_MODULE = 60

def epilog(jobs=DEFAULT_JOBS):
  '''The epilog of the help text; ``jobs`` is the default width.'''
  width = 'as many at a time as the memory budget allows, up to the core ' \
          'count' if jobs == 'auto' else '%s at a time' % jobs
  return '''
Without options every unit_*.py and func_*.py file runs, one file per
process, %(width)s, on the backend of SPRITE_INTERPRETER_FLAGS (the
Python backend by default).  A PATTERN is matched against the file names
(shell style).  The output of each file goes to .cache/runner/<backend>/
<file>.log.  See section 10 of README.
''' % {'width': width}

def parse_jobs(text):
  '''"auto", or a positive count.'''
  if text == 'auto':
    return text
  try:
    value = int(text)
  except ValueError:
    raise argparse.ArgumentTypeError('not a count or "auto": %r' % text)
  if value < 1:
    raise argparse.ArgumentTypeError('the width is at least 1')
  return value

def build_parser(jobs=DEFAULT_JOBS):
  '''The argument parser; ``jobs`` is the default width (a count or auto).'''
  parser = argparse.ArgumentParser(
      prog='run_tests', epilog=epilog(jobs)
    , description='Run the test files in child processes under a memory '
                  'budget and report one line per file.'
    , formatter_class=argparse.RawDescriptionHelpFormatter
    )
  parser.add_argument(
      'pattern', nargs='*', metavar='PATTERN'
    , help='a test file, or a shell-style pattern of file names'
    )
  parser.add_argument(
      '-j', '--jobs', type=parse_jobs, default=jobs, metavar='N|auto'
    , help='how many files run at once; auto lets the budget decide, up to '
           'the core count [default: %s]' % jobs
    )
  parser.add_argument(
      '--mem', type=float, default=None, metavar='GB'
    , help='the budget: the caps of the running files stay within it '
           '[default: %d%%%% of MemAvailable at the start]'
           % round(DEFAULT_MEM_FRACTION * 100)
    )
  parser.add_argument(
      '--backend', choices=BACKENDS + ('both',), default=None
    , help='the backend, or both [default: from SPRITE_INTERPRETER_FLAGS, '
           'else py]'
    )
  parser.add_argument(
      '--fast', nargs='?', const=DEFAULT_FAST_SECONDS, type=float
    , default=None, metavar='S'
    , help='only the files below S seconds in the manifest, and the files '
           'without an entry [S defaults to %g]' % DEFAULT_FAST_SECONDS
    )
  parser.add_argument(
      '--changed', nargs='?', const='HEAD', default=None, metavar='REV'
    , help='select the files for the paths that changed since REV '
           '[REV defaults to HEAD: the working tree]'
    )
  parser.add_argument(
      '--prepare', action='store_true'
    , help='first compile the shared Curry products, one directory at a '
           'time, so parallel files never write the same product at once'
    )
  parser.add_argument(
      '--prepare-only', action='store_true'
    , help='run the prepare pass alone, for the products the selection '
           'uses, and exit with its status; no test file runs'
    )
  parser.add_argument(
      '--update-manifest', action='store_true'
    , help='write the durations and peaks of this run to the manifest'
    )
  parser.add_argument(
      '--timeout', type=float, default=DEFAULT_TIMEOUT, metavar='S'
    , help='kill a file after S seconds [default: %g]' % DEFAULT_TIMEOUT
    )
  parser.add_argument(
      '--list', action='store_true'
    , help='show the selection, with the manifest numbers and the reasons, '
           'and exit'
    )
  parser.add_argument(
      '-v', '--verbose', action='store_true'
    , help='print the output of each file; at width 1, as it comes, and the '
           'file gets the standard input, so a breakpoint works'
    )
  parser.add_argument(
      '--manifest', default=MANIFEST_FILE, metavar='FILE'
    , help='the manifest file [default: tests/manifest.json]'
    )
  parser.add_argument(
      '--logdir', default=LOGDIR, metavar='DIR'
    , help='where the logs go [default: tests/.cache/runner]'
    )
  return parser

def parse_args(argv, jobs=DEFAULT_JOBS):
  return build_parser(jobs).parse_args(argv)

def flag_backend(flags):
  '''The backend named in a SPRITE_INTERPRETER_FLAGS value, or None.'''
  for item in (flags or '').split(','):
    name, _, value = item.partition(':')
    if name.strip() == 'backend' and value.strip():
      return value.strip()
  return None

def with_backend(flags, backend):
  '''The flags value with its backend set to ``backend``.'''
  items = [
      item for item in (flags or '').split(',')
           if item.strip() and item.partition(':')[0].strip() != 'backend'
    ]
  return ','.join(['backend:' + backend] + items)

def prepend_path(entry, value):
  '''``entry`` in front of a colon-separated path, once.'''
  parts = [part for part in (value or '').split(':') if part]
  normal = os.path.normpath(entry)
  if any(os.path.normpath(part) == normal for part in parts):
    return ':'.join(parts)
  return ':'.join([entry] + parts)

def environment(sprite_home, backend, base=None):
  '''
  The environment of a child: what the shell driver always set, with the
  backend in SPRITE_INTERPRETER_FLAGS.
  '''
  env = dict(os.environ if base is None else base)
  env['SPRITE_HOME'] = sprite_home
  env['PYTHONPATH'] = prepend_path(
      os.path.join(TESTDIR, 'lib'), env.get('PYTHONPATH')
    )
  env['CURRYPATH'] = prepend_path(
      os.path.join(TESTDIR, 'data', 'curry'), env.get('CURRYPATH')
    )
  env.setdefault('SPRITE_CACHE_FILE', os.path.join(TESTDIR, '.cache', 'icurry.db'))
  env['SPRITE_INTERPRETER_FLAGS'] = with_backend(
      env.get('SPRITE_INTERPRETER_FLAGS'), backend
    )
  return env

def backstop_prefix(cap, setting=None):
  '''
  The command prefix that caps the address space of a child: a backstop
  behind the watchdog.  ``setting`` is SPRITE_TEST_MAX_VMEM_KB (KiB, or
  "unlimited"); without it the limit is the larger of BACKSTOP and
  BACKSTOP_FACTOR times ``cap``, within the hard limit of this process.
  '''
  if setting is None:
    setting = os.environ.get('SPRITE_TEST_MAX_VMEM_KB')
  if setting == 'unlimited':
    return []
  if setting:
    limit = int(setting) * 1024
  else:
    limit = max(BACKSTOP, BACKSTOP_FACTOR * (cap or 0))
  _, hard = resource.getrlimit(resource.RLIMIT_AS)
  if hard != resource.RLIM_INFINITY:
    limit = min(limit, hard)
  if shutil.which('prlimit') is None:
    return []
  return ['prlimit', '--as=%d' % limit]

def test_job(filename, backend, sprite_home, manifest, timeout, logdir, env):
  '''The job of one test file on one backend.'''
  python = os.path.join(sprite_home, 'bin', 'python')
  cap = manifest.cap(filename, backend)
  argv = backstop_prefix(cap) + [
      python, '-B', '-m', 'unittest', 'discover', '-v', TESTDIR, filename
    ]
  return Job(
      filename, backend, argv, cap=cap, timeout=timeout
    , logfile=os.path.join(logdir, backend, filename + '.log'), cwd=TESTDIR
    , env=env, exclusive=filename in selection.EXCLUSIVE
    , hint=manifest.duration(filename, backend)
    )

def prepare_pass_jobs(args, names, backends, sprite_home):
  '''
  The jobs of the prepare pass for the selected files ``names``: one per
  directory and backend, with the environment of a child, a timeout that
  grows with the count of modules, and the reason for --list.
  '''
  base = dict(os.environ)
  jobs = prepare.jobs(
      names, backends, sprite_home, base, args.logdir, cap=PREPARE_CAP
    , timeout=None, prefix=backstop_prefix(PREPARE_CAP)
    )
  for job in jobs:
    count = len(job.argv) - job.argv.index(prepare.TARGET[job.backend]) - 1
    job.timeout = max(args.timeout, PREPARE_SECONDS_PER_MODULE * count)
    job.env = environment(sprite_home, job.backend, base=job.env)
    job.reasons = ['prepare pass']
  return jobs

def select(args, backends, manifest, files=None):
  '''
  The selection: a list of :class:`selection.Selected` and the notes that
  explain it.
  '''
  files = selection.test_files() if files is None else files
  notes = []
  if args.changed is not None:
    paths = selection.changed_paths(args.changed)
    if not paths:
      notes.append('nothing changed since %s' % args.changed)
    selected, notes_ = selection.select_changed(paths, files)
    notes.extend(notes_)
    if args.pattern:
      keep = set(selection.match_patterns(files, args.pattern))
      selected = [item for item in selected if item.filename in keep]
  else:
    chosen = selection.match_patterns(files, args.pattern)
    why = 'pattern' if args.pattern else 'every test file'
    selected = [selection.Selected(name, [why]) for name in chosen]
  if args.fast is not None:
    fast = set(selection.fast_tier(
        [item.filename for item in selected], backends, manifest, args.fast
      ))
    selected = [item for item in selected if item.filename in fast]
    for item in selected:
      item.reasons.append('fast tier (below %g s, or no entry)' % args.fast)
  return selected, notes

def budget_of(args, width):
  '''The budget in bytes and MemAvailable (None when unknown).'''
  available = procs.mem_available()
  if args.mem is not None:
    return int(args.mem * GIB), available
  if available is None:
    return width * DEFAULT_CAP, None
  return int(available * DEFAULT_MEM_FRACTION), available

def listing(jobs, manifest):
  '''The lines of --list.'''
  lines = ['%-4s %-28s %9s %8s  %s' % ('be', 'file', 'manifest', 'cap_mb', 'reasons')]
  for job in jobs:
    hint = '-' if job.hint is None else '%.1f s' % job.hint
    tags = list(job.reasons) if hasattr(job, 'reasons') else []
    if job.exclusive:
      tags.append('runs alone')
    lines.append('%-4s %-28s %9s %8d  %s' % (
        job.backend, job.filename, hint, round(job.cap / 1024 ** 2)
      , '; '.join(tags)
      ))
  return '\n'.join(lines)

def exit_status(jobs, interrupted=False):
  '''130 after an interrupt, 1 when a job did not pass, else 0.'''
  if interrupted:
    return 130
  return 0 if all(job.ok for job in jobs) else 1

def main(argv=None):
  args = parse_args(sys.argv[1:] if argv is None else argv)
  out = sys.stdout
  sprite_home = os.path.realpath(os.environ.get('SPRITE_HOME') or DEFAULT_SPRITE_HOME)
  if not os.path.isfile(os.path.join(sprite_home, 'bin', 'python')):
    sys.stderr.write(
        'run_tests: no installation at %s; set SPRITE_HOME or run make stage\n'
      % sprite_home
      )
    return 2
  if args.backend == 'both':
    backends = list(BACKENDS)
  elif args.backend:
    backends = [args.backend]
  else:
    backends = [flag_backend(os.environ.get('SPRITE_INTERPRETER_FLAGS')) or 'py']
  manifest = Manifest.load(args.manifest)
  files = selection.test_files()
  if args.pattern and args.changed is None \
     and not selection.match_patterns(files, args.pattern):
    # A typo in a pattern must not pass silently.
    sys.stderr.write(
        'run_tests: no test file matches %s\n' % ' '.join(args.pattern)
      )
    return 2
  try:
    selected, notes = select(args, backends, manifest, files)
  except RuntimeError as exc:
    sys.stderr.write('run_tests: %s\n' % exc)
    return 2
  names = [item.filename for item in selected]
  reasons = {item.filename: item.reasons for item in selected}
  envs = {backend: environment(sprite_home, backend) for backend in backends}
  # Under --prepare-only the selection names the products to prepare, and
  # no test file runs.
  jobs = [] if args.prepare_only else [
      test_job(
          name, backend, sprite_home, manifest, args.timeout, args.logdir
        , envs[backend]
        )
      for backend in backends for name in names
    ]
  for job in jobs:
    job.reasons = reasons[job.filename]
  jobs.sort(key=lambda job: manifest.order_key(job.filename, job.backend))
  if args.prepare_only:
    # The pass runs one process at a time.
    width = 1
  else:
    width = procs.cpu_count() if args.jobs == 'auto' else args.jobs
  budget, available = budget_of(args, width)
  prepare_jobs = []
  if args.prepare or args.prepare_only:
    prepare_jobs = prepare_pass_jobs(args, names, backends, sprite_home)
  for line in notes:
    out.write('changed: %s\n' % line)
  if args.list:
    out.write(listing(prepare_jobs + jobs, manifest) + '\n')
    return 0
  if args.prepare_only:
    out.write(report.prepare_header(prepare_jobs, args.logdir) + '\n')
  elif not jobs:
    out.write('run_tests: no file selected\n')
    return 0
  else:
    out.write(report.header(jobs, width, budget, args.timeout, args.logdir, available) + '\n')
  out.flush()
  total = len(prepare_jobs) + len(jobs)
  counter = itertools.count(1)
  # With -v at width 1 the output streams as it comes and the file gets the
  # standard input, so a breakpoint in a test works.  Without -v the output
  # goes to the log alone, and a breakpoint would wait there unseen: the
  # file reads an empty standard input instead and ends.
  echo = args.verbose and width == 1
  def on_finish(job):
    out.write(report.format_status(job, next(counter), total) + '\n')
    if args.verbose and not echo:
      out.write(report.tail(job.logfile, 10 ** 6) + '\n')
    elif not job.ok and not echo:
      out.write(report.tail(job.logfile) + '\n')
    out.flush()
  interrupted = False
  wall = 0.0
  if prepare_jobs:
    pre = Scheduler(prepare_jobs, budget, 1, on_finish=on_finish, echo=echo)
    pre.run()
    interrupted = pre.interrupted
    wall += pre.wall
  if jobs and not interrupted:
    sched = Scheduler(
        jobs, budget, width, on_finish=on_finish, echo=echo
      , inherit_stdin=echo
      )
    sched.run()
    interrupted = sched.interrupted
    wall += sched.wall
    done = sched.jobs
  else:
    done = jobs
  out.write('\n' + report.summary(prepare_jobs + done, wall, interrupted) + '\n')
  if args.update_manifest:
    measured = [job for job in done if job.finished and job.peak is not None]
    for job in measured:
      manifest.update(job.filename, job.backend, job)
    if measured:
      manifest.save(args.manifest)
      out.write('manifest: %d entr%s written to %s\n' % (
          len(measured), 'y' if len(measured) == 1 else 'ies'
        , report.relative(args.manifest)
        ))
  out.flush()
  # Under --prepare the pass is a warm-up: a directory that did not compile
  # whole is a note in the table, not a failure, and the test that needs the
  # module reports it.  Under --prepare-only the pass is the run, and such a
  # directory fails it.
  if args.prepare_only:
    return exit_status(prepare_jobs, interrupted)
  return exit_status(done, interrupted)
