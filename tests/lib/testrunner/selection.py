'''
Which files run.

Patterns select by file name, as the drivers always did (shell-style, through
fnmatch).  --fast keeps the files whose manifest duration is below a
threshold, with the files that have no entry, minus the files that compile
a corpus of their own (compiles_corpus).  --changed maps the paths that
changed since a revision to test files through RULES.  The selection always
prints why a file is in it when the user asked for --changed or --list.
'''

import fnmatch, os, subprocess
from . import TESTDIR, ROOTDIR
from . import prepare

__all__ = [
    'EXCLUSIVE', 'IGNORED', 'RULES', 'Selected', 'changed_paths'
  , 'compiles_corpus', 'fast_tier', 'match_patterns', 'select_changed'
  , 'test_files'
  ]

# Files that must run alone: nothing else runs while one of them runs.
EXCLUSIVE = {
    'unit_currylib.py':
        'removes and restores products of the installed Curry library'
  }

# The rules of --changed: a glob of a changed path, relative to the root of
# the repository, the globs of the test files it selects, and the reason that
# the selection prints.  The first rule whose path glob matches decides.  A
# path that no rule matches selects everything, and so does a rule whose
# globs match no test file: the policy for the unknown.  'tests/*.py'
# selects the changed test file itself.
ALL = '*'
TOOLCHAIN = [
    'unit_compile*.py', 'unit_cache.py', '*toolchain*.py', '*flat2icurry*.py'
  , '*curry2icurry*.py', 'unit_make.py', 'unit_prelude.py'
  ]
API = ['unit_expr.py', 'unit_api.py', '*conversions*.py', '*evaluation*.py']
RULES = [
    ('tests/unit_*.py', ['{name}'], 'the changed test file')
  , ('tests/func_*.py', ['{name}'], 'the changed test file')
  , ('tests/lib/benchmarks/*', ['unit_benchmarks.py'], 'the benchmark harness')
  , ('tests/lib/testrunner/*', ['unit_runner.py'], 'the test runner')
  , ('tests/lib/*', [ALL], 'the test harness')
  , ('examples/*', ['unit_examples.py'], 'the examples')
  , ('scripts/setup-dev-machine.sh', ['unit_setup_script.py'], 'the setup script')
  , ('conda/dev-environment.yml', ['unit_setup_script.py'], 'the setup script')
  , ('conda/*', ['unit_conda.py'], 'the conda recipes')
  , ( 'tests/data/curry/benchmarks/*'
    , ['unit_benchmarks.py', 'unit_cxx_variable.py'], 'the benchmark programs'
    )
  , ( 'tests/data/curry/flat2icurry/*'
    , ['*flat2icurry*.py', '*curry2icurry*.py']
    , 'the probe modules of the ICurry oracle'
    )
  , ('tests/data/curry/*/*', ['func_{dir}*.py'], 'the corpus of a functional test')
  , ('src/cyrt/*', ['unit_cxx_*.py'], 'the C++ runtime')
  , ('src/python/backends/cxx/*', ['unit_cxx_*.py'], 'the C++ backend')
  , ('src/python/backends/py/*', ['unit_py_*.py'], 'the Python backend')
  , ('src/python/toolchain/*', TOOLCHAIN + ['unit_plan.py'], 'the toolchain')
  , ( 'curry/*', TOOLCHAIN + ['unit_currylib.py', 'unit_prebuild.py']
    , 'the Curry library'
    )
  , ('src/python/icurry/*', TOOLCHAIN + ['unit_icurry.py'], 'the ICurry reader')
  , ('src/python/expressions.py', API, 'the expression builder')
  , ('src/python/interpreter/*', API + ['unit_loadsave.py'], 'the interpreter')
  , ('src/python/inspect/*', API + ['unit_inspect.py'], 'the inspection API')
  ]

# Changed paths that select nothing: documentation and metadata.
IGNORED = [
    'docs/*', '*.md', '*.rst', 'LICENSE', 'NOTES', 'TODO', 'README*'
  , '.github/*', '.gitignore', '.gitmodules', 'tests/manifest.json'
  , 'tests/README'
  ]

class Selected:
  '''One selected file and the reasons it was selected.'''
  def __init__(self, filename, reasons=()):
    self.filename = filename
    self.reasons = list(reasons)

  def __repr__(self):
    return 'Selected(%r, %r)' % (self.filename, self.reasons)

def test_files(testdir=TESTDIR):
  '''The test files: unit_*.py and func_*.py, sorted.'''
  names = os.listdir(testdir)
  return sorted(
      name for name in names
           if name.endswith('.py')
          and (name.startswith('unit_') or name.startswith('func_'))
    )

def match_patterns(files, patterns):
  '''
  The files that match any pattern, in the order of ``files``.  A pattern is
  shell-style; a bare name matches itself.  Without patterns, every file.
  '''
  if not patterns:
    return list(files)
  return [
      name for name in files
           if any(fnmatch.fnmatchcase(name, pat) for pat in patterns)
    ]

def compiles_corpus(name):
  '''
  True for a file that compiles a corpus of Curry modules of its own on a
  cold tree: every functional test, and the files that CORPUS in prepare.py
  names.  The manifest measures warm trees, so the duration of such a file
  does not predict a cold run: the math corpus (218 programs in three
  files) takes about 90 s on the C++ backend after a rebuild, where the
  entries of its files total 3 s.  The fast tier leaves these files out.
  '''
  return name.startswith('func_') or name in prepare.corpus_owners()

def fast_tier(files, backends, manifest, threshold):
  '''
  The files whose manifest duration is below ``threshold`` seconds on every
  backend of the run, minus the files that compile a corpus of their own
  (compiles_corpus).  A backend without an entry counts as fast: the file
  may be new.
  '''
  fast = []
  for name in files:
    if compiles_corpus(name):
      continue
    durations = [manifest.duration(name, backend) for backend in backends]
    if all(d is None or d < threshold for d in durations):
      fast.append(name)
  return fast

def changed_paths(rev='HEAD', rootdir=ROOTDIR):
  '''
  The paths, relative to the root, that differ between the working tree and
  ``rev``, with the untracked files that git does not ignore.
  '''
  diff = subprocess.run(
      ['git', '-C', rootdir, 'diff', '--name-only', rev, '--']
    , capture_output=True, text=True
    )
  if diff.returncode != 0:
    raise RuntimeError(
        'git diff failed: %s' % diff.stderr.strip()
      )
  others = subprocess.run(
      ['git', '-C', rootdir, 'ls-files', '--others', '--exclude-standard']
    , capture_output=True, text=True
    )
  paths = diff.stdout.split() + others.stdout.split()
  return sorted(set(paths))

def _rule_for(path):
  '''The rule that decides ``path``: (globs, reason), or None.'''
  for pattern, globs, reason in RULES:
    if fnmatch.fnmatchcase(path, pattern):
      return globs, reason
  return None

def select_changed(paths, files):
  '''
  Maps changed paths to test files.  Returns a pair: the list of
  :class:`Selected` in the order of ``files``, and the list of lines that
  explain the mapping, one per path.
  '''
  reasons = {}
  notes = []
  def add(names, why):
    for name in names:
      reasons.setdefault(name, [])
      if why not in reasons[name]:
        reasons[name].append(why)
  for path in paths:
    if any(fnmatch.fnmatchcase(path, pat) for pat in IGNORED):
      notes.append('%s: selects nothing' % path)
      continue
    rule = _rule_for(path)
    if rule is None:
      add(files, 'an unknown path changed: %s' % path)
      notes.append('%s: unknown, selects everything' % path)
      continue
    globs, reason = rule
    parts = path.split('/')
    context = {
        'name': parts[-1]
      , 'dir': parts[3] if len(parts) > 3 else ''
      }
    globs = [glob.format(**context) for glob in globs]
    chosen = match_patterns(files, globs)
    if not chosen:
      add(files, 'no test file matches %s for %s' % (' '.join(globs), path))
      notes.append(
          '%s: %s, no test file matches %s; selects everything'
        % (path, reason, ' '.join(globs))
        )
      continue
    add(chosen, '%s (%s)' % (reason, path))
    notes.append('%s: %s -> %s' % (path, reason, _names(chosen, files)))
  selected = [Selected(name, reasons[name]) for name in files if name in reasons]
  return selected, notes

def _names(chosen, files, limit=8):
  '''A short spelling of a list of files.'''
  if len(chosen) == len(files):
    return 'everything (%d files)' % len(files)
  if len(chosen) > limit:
    return '%s and %d more' % (' '.join(chosen[:limit]), len(chosen) - limit)
  return ' '.join(chosen)
