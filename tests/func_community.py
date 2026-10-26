'''Community programs selected by the CURRYUP-H survey.

GOALS.tsv selects finite examples, not arbitrary nullary data (some are
infinite). Each test runs one original module or its nullary adapter.
SPRITE_COMMUNITY_VERIFY_ORACLE=1 rechecks committed goldens with the active
oracle without replacing them, for the second tool configuration.
'''
import cytest # from ./lib; must be first
from cytest import oracle
from cytest.clean import clean
import contextlib, csv, json, os, pathlib, shutil, tempfile
from types import SimpleNamespace
import curry
from curry.toolchain import _preprocessor
from unit_community_compile import (
    current_only, frontend_sources, support_paths, ORIGIN
  )

ROOT = pathlib.Path('data/curry/community')
# Reproduced with a 30-second bound; unit_community retains an expected failure.
RUNTIME_FAILURES = {
    'justZeroGoal': 'non-linear functional pattern loops (unit_community)'
  , 'justFailedGoal': 'non-linear functional pattern loops (unit_community)'
  }
with (ROOT / 'GOALS.tsv').open() as stream:
  GOALS = list(csv.DictReader(stream, delimiter='\t'))


@cytest.with_flags(interpret='off')
def check_program(self, filename, entries):
  source = ROOT / filename
  reason = current_only(source)
  if reason and curry.config.frontend_version() == '2.0.0':
    self.skipTest(reason)
  if ORIGIN in source.parts:
    with frontend_sources(source) as (local, root):
      curry.path.insert(0, str(root))
      with oracle_source(local) as (module, work):
        check_goals(self, source, entries, module, work, local)
  else:
    curry.path[:0] = support_paths(source)
    with oracle_source(source) as (module, work):
      check_goals(self, source, entries, module, work)


@contextlib.contextmanager
def oracle_source(source):
  # PAKCS must not read the sidecars Sprite generated against its own base.
  with tempfile.TemporaryDirectory() as work:
    for original in source.parent.rglob('*.curry'):
      if not original.is_file() or original.name == 'Prelude.curry':
        continue
      target = pathlib.Path(work) / original.relative_to(source.parent)
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copyfile(original, target)
    module = SimpleNamespace(__name__=source.stem,
        __file__=str(pathlib.Path(work) / source.name))
    yield module, work


def check_goals(self, source, entries, module, work, runtime_source=None):
  for entry in entries:
    goal = entry['goal']
    with self.subTest(goal=goal):
      golden = source.with_name(source.stem + '.' + goal + '.au-gen')
      reason = (_preprocessor.missing(ROOT / entry['program'])
                or _preprocessor.missing(source))
      if reason and (not golden.exists()
                     or os.environ.get('SPRITE_COMMUNITY_VERIFY_ORACLE') == '1'):
        self.skipTest(reason)
      if not golden.exists():
        oracle.divine(module, module.__name__ + '.' + goal, [work], timeout=20,
                      goldenfile=str(golden), record_errors=True)
      expected = golden.read_text()
      current = expected
      if os.environ.get('SPRITE_COMMUNITY_VERIFY_ORACLE') == '1':
        current = oracle.divine(module, module.__name__ + '.' + goal, [work], timeout=20,
                                record_errors=True)
        if isinstance(current, bytes):
          current = current.decode()
      if expected.startswith('!error\n'):
        self.assertEqual(clean(expected), clean(current))
        record(entry, current, 'skipped: oracle rejection')
        self.skipTest(expected.partition('\n')[2].strip()
                      or 'oracle rejected the goal without a diagnostic')
      if source.stem == 'TestFuncPatternGoals' and goal in RUNTIME_FAILURES:
        self.assertSameResultMultiset(current, expected)
        record(entry, current, 'known runtime timeout; see unit_community')
        self.skipTest(RUNTIME_FAILURES[goal])
      # A community example may expose a looping or crashing runtime defect.
      # Keep that goal within the runner's process limits and give it a timeout.
      proc, actual = sprite_results(runtime_source or source, goal)
      if proc.returncode != 0 and reason and (
          reason in proc.stderr
          or 'Preprocessor exited with exit code 127' in proc.stderr
        ):
        record(entry, current, 'skipped: ' + reason)
        self.skipTest(reason)
      record(entry, current, actual)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      if not expected.startswith('!error\n'):
        self.assertSameResultMultiset(current, expected)
      self.assertSameResultMultiset(actual, expected)


def sprite_results(source, goal, timeout=30, interpret='off', address_space=2 << 30):
  code = (
      'import curry, json\n'
      'curry.reset(interpret=%r)\n'
      'curry.path[:0] = %r\n'
      'module = curry.import_(%r)\n'
      'print(json.dumps([curry.show(v) for v in curry.eval('
      'getattr(module, %r))]))\n'
    ) % (interpret, support_paths(source) if ROOT in source.parents
         else [str(source.parent)], source.stem, goal)
  proc = cytest.run_in_subprocess(code, timeout=timeout, address_space=address_space)
  actual = ('\n'.join(json.loads(proc.stdout)) if proc.returncode == 0
            else '!status %s\n%s' % (proc.returncode, proc.stderr))
  return proc, actual


def record(entry, expected, actual):
  evidence = os.environ.get('SPRITE_COMMUNITY_EVIDENCE')
  if evidence:
    with open(evidence, 'a') as stream:
      stream.write(json.dumps(dict(entry, oracle=expected, sprite=actual)) + '\n')


class TestCommunity(cytest.TestCase):
  '''One test per source module, isolated by cytest's interpreter reset.'''


programs = {}
for entry in GOALS:
  if pathlib.Path(entry['module']).stem == 'TestMPTCCoerceGoals':
    continue # Covered by unit_community under the new front end.
  programs.setdefault(entry['module'], []).append(entry)
for filename, entries in programs.items():
  name = 'test_' + filename[:-6].replace('/', '_').replace('-', '_')
  def test(self, filename=filename, entries=entries):
    check_program(self, filename, entries)
  setattr(TestCommunity, name, oracle.require(test))
