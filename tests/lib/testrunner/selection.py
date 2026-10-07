'''
Which files run.

Patterns select by file name, as the drivers always did (shell-style, through
fnmatch).  --fast keeps the files whose manifest duration is below a
threshold, with the files that have no entry, minus the files that compile
a corpus of their own (compiles_corpus).  --changed maps the paths that
changed since a revision to test files through RULES.  The selection always
prints why a file is in it when the user asked for --changed or --list.
'''

import fnmatch, os, re, subprocess
from . import TESTDIR, ROOTDIR
from . import prepare

__all__ = [
    'EXCLUSIVE', 'IGNORED', 'NAMED', 'POOL', 'POOL_CHECKS', 'RULES', 'Selected'
  , 'changed_paths', 'compiles_corpus', 'fast_tier', 'files_naming'
  , 'match_patterns', 'pool_importers', 'select_changed', 'test_files'
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
# selects the changed test file itself.  NAMED in the place of the globs
# selects the test files whose text names the module of the changed source
# or a module of the pool that imports it (files_naming, pool_importers),
# with the files of POOL_CHECKS: the shared pool under tests/data/curry has
# no test of its own, a module there is named by the files that use it,
# and a file may reach it through an importing module.
ALL = '*'
NAMED = object()
# The shared pool of Curry modules, whose import lines a NAMED rule reads.
POOL = os.path.join(TESTDIR, 'data', 'curry')
# The test files that check the products of every module of the pool
# (test_products_on_disk of func_flat2icurry.py pairs each FlatCurry file
# with the ICurry beside it); a NAMED match selects them too.
POOL_CHECKS = ['func_flat2icurry.py']
# An import line of a Curry module: import M, import qualified M, import M
# (f), import M as N.
IMPORT = re.compile(r'^import\s+(?:qualified\s+)?([\w.]+)', re.M)
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
    , [ 'unit_benchmarks.py', 'unit_cxx_heap.py', 'unit_cxx_passthrough.py'
      , 'unit_cxx_variable.py'
      ]
    , 'the benchmark programs'
    )
  , ( 'tests/data/curry/flat2icurry/*'
    , ['*flat2icurry*.py', '*curry2icurry*.py']
    , 'the probe modules of the ICurry oracle'
    )
  , ('tests/data/curry/*/*', ['func_{dir}*.py'], 'the corpus of a functional test')
  , ('tests/data/curry/*.curry', NAMED, 'the test files that name the module')
  , ('src/cyrt/*', ['unit_cxx_*.py'], 'the C++ runtime')
  , ('src/python/backends/cxx/*', ['unit_cxx_*.py'], 'the C++ backend')
  , ('src/python/backends/py/*', ['unit_py_*.py'], 'the Python backend')
  , ('src/python/toolchain/*', TOOLCHAIN + ['unit_plan.py'], 'the toolchain')
  , ( 'curry/*', TOOLCHAIN + ['unit_currylib.py', 'unit_prebuild.py']
    , 'the Curry library'
    )
  , ( 'src/python/icurry/analysis/*', ['unit_icurry.py', 'unit_optimize*.py']
    , 'the ICurry analyses'
    )
  , ('src/python/icurry/*', TOOLCHAIN + ['unit_icurry.py'], 'the ICurry reader')
  , ('src/python/expressions.py', API, 'the expression builder')
  , ( 'src/python/show.py', ['unit_show_float.py', 'unit_goals.py']
    , 'the show module'
    )
  , ( 'src/python/interpreter/optimize.py', API + ['unit_optimize*.py']
    , 'the optimizer'
    )
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

def files_naming(module, files, testdir=TESTDIR):
  '''
  The test files among ``files`` whose text names ``module`` as a word, in
  the order of ``files``.  A file that cannot be read names nothing.
  '''
  pattern = re.compile(r'(?<![\w.])%s(?![\w])' % re.escape(module))
  named = []
  for name in files:
    try:
      with open(os.path.join(testdir, name), 'r', encoding='utf-8') as stream:
        text = stream.read()
    except (OSError, UnicodeDecodeError):
      continue
    if pattern.search(text):
      named.append(name)
  return named

def pool_importers(module, pooldir=POOL):
  '''
  The modules of the pool under ``pooldir`` that import ``module``, directly
  or through another module of the pool, sorted.  A file that cannot be
  read imports nothing; a missing directory holds no module.
  '''
  try:
    names = os.listdir(pooldir)
  except OSError:
    return []
  imports = {}
  for name in names:
    if not name.endswith('.curry'):
      continue
    try:
      with open(os.path.join(pooldir, name), 'r', encoding='utf-8') as stream:
        text = stream.read()
    except (OSError, UnicodeDecodeError):
      continue
    imports[name[:-len('.curry')]] = set(IMPORT.findall(text))
  found = set()
  frontier = [module]
  while frontier:
    target = frontier.pop()
    for name, imported in imports.items():
      if target in imported and name not in found:
        found.add(name)
        frontier.append(name)
  return sorted(found)

def select_changed(paths, files, testdir=TESTDIR, pooldir=POOL):
  '''
  Maps changed paths to test files.  Returns a pair: the list of
  :class:`Selected` in the order of ``files``, and the list of lines that
  explain the mapping, one per path.  ``testdir`` holds the test files,
  which a NAMED rule reads, and ``pooldir`` the modules of the shared pool,
  whose import lines it reads.
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
    if globs is NAMED:
      module = parts[-1][:-len('.curry')]
      importers = pool_importers(module, pooldir)
      naming = set()
      for name in [module] + importers:
        naming.update(files_naming(name, files, testdir))
      if not naming:
        add(files, 'no test file names the module %s of %s' % (module, path))
        notes.append(
            '%s: no test file names the module %s; selects everything'
          % (path, module)
          )
        continue
      if importers:
        reason = '%s or an importer (%s)' % (reason, ' '.join(importers))
      checks = match_patterns(files, POOL_CHECKS)
      add([name for name in files if name in naming], '%s (%s)' % (reason, path))
      add(checks, 'the check of the products of the pool (%s)' % path)
      chosen = [name for name in files if name in naming or name in checks]
      notes.append('%s: %s -> %s' % (path, reason, _names(chosen, files)))
      continue
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
