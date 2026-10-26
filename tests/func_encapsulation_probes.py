'''Weak encapsulation: measured systems are evidence, not the specification.

PROBES.md keeps every measured answer, including oracle disagreements.
Each oracle invocation uses a fresh source-only copy, timeout, and limits.
Set SPRITE_PROBES_KICS2 to an optional KiCS2 executable outside PATH.
'''
import cytest # from ./lib; must be first
from cytest.clean import clean
from curry import config
from func_community import oracle_source, sprite_results
import json, os, pathlib, re, shutil, subprocess, unittest

ROOT = pathlib.Path('data/curry/encapsulation')
SOURCE = ROOT / 'Probes.curry'
TIMEOUT = 60
ADDRESS_SPACE = 2 << 30
# Each exemption names a measured disagreement and its operational reason.
DIVERGENCES = {
    ('pakcs', goal): 'strict argument evaluation demands an unneeded failure'
    for goal in ('unusedFailure', 'nestedUnusedFailure', 'mixedValue',
                 'chrsFailureChoice', 'chrsFailureChoiceReversed')
  }
DIVERGENCES['pakcs', 'narrowedAfter'] = (
    'unbound outside argument suspends before the outer constraint')
DIVERGENCES['pakcs', 'bindingEscape'] = (
    'unbound outside argument suspends; this is a suspension, not a value; '
    'D54 follows D48\'s wider escape condition')
for goal in ('mixedFailure', 'mixedFailureReversed'):
  DIVERGENCES['kics2', goal] = (
      'an inside failure masks the argument failure; Sprite has D45')
DIVERGENCES['kics2', 'sharedLookup'] = (
    'returns Long, Short, Short; Sprite has exactly Short after D45')
VALUES = dict((name, json.loads(value)) for name, value in re.findall(
    r'^-- Value (\w+): (.*)$', SOURCE.read_text(), re.MULTILINE))
GOALS = list(VALUES)


def observations():
  '''Read JSON cells: [] is no answer; ["[]"] is one empty-list answer.'''
  rows = {}
  for line in (ROOT / 'PROBES.md').read_text().splitlines():
    if not line.startswith('| `'):
      continue
    cells = [cell.strip().strip('`') for cell in line.strip('|').split('|')]
    name, declarative, sprite, pakcs, kics2, verdict = cells
    rows[name] = dict(sprite=json.loads(sprite), pakcs=json.loads(pakcs),
                      kics2=json.loads(kics2), verdict=verdict)
  return rows


def normalized(values):
  return clean(values).splitlines()


def system_results(goal, system):
  '''Never let an oracle reuse Sprite's rewritten interfaces or products.'''
  with oracle_source(SOURCE) as (module, work):
    env = dict(os.environ, CURRYPATH=work, HOME=work)
    if system == 'pakcs':
      executable = config.installed_path('tools', 'pakcs')
      if not os.path.isfile(executable):
        executable = shutil.which('pakcs')
      if not executable:
        raise unittest.SkipTest('PAKCS unavailable')
      command = [executable, '--nocypm', '-q', ':set', 'safe']
      prefix = cytest.limit_prefix(ADDRESS_SPACE, TIMEOUT, kill_after=5)
    else:
      executable = os.environ.get('SPRITE_PROBES_KICS2') or shutil.which('kics2')
      if not executable:
        raise unittest.SkipTest('KiCS2 unavailable; measured column retained')
      # GHC reserves a large virtual address range. Cap data and RSS (the
      # runner watches the complete session) rather than address space.
      prefix = ['prlimit', '--data=%d' % ADDRESS_SPACE]
      prefix += cytest.limit_prefix(timeout=TIMEOUT, kill_after=5)
      command = [executable, '--noreadline', '--nocypm', ':set', 'v0']
    command += [':load', module.__name__, ':eval',
                module.__name__ + '.' + goal, ':quit']
    proc = subprocess.run(prefix + command, cwd=work, env=env,
                          capture_output=True, text=True)
    evidence = os.environ.get('SPRITE_PROBES_EVIDENCE')
    if evidence:
      with open(evidence + '.raw', 'a') as stream:
        stream.write(json.dumps(dict(goal=goal, system=system,
            status=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)) + '\n')
    if proc.returncode not in (0, 2):
      raise AssertionError('%s %s: status %s\n%s\n%s' % (
          system, goal, proc.returncode, proc.stdout, proc.stderr))
    # KiCS2 prints ! or (!) for failure; PAKCS prints no value line.
    lines = [line for line in proc.stdout.splitlines()
             if line.strip().strip('()').strip() != '!']
    return normalized(lines)


class TestEncapsulationOracles(cytest.TestCase):
  def check(self, goal, system):
    if config.frontend_version() != '3.1.0':
      self.skipTest('measurements require front end 3.1.0 and PAKCS 3.10.0')
    current = system_results(goal, system)
    evidence = os.environ.get('SPRITE_PROBES_EVIDENCE')
    if evidence:
      with open(evidence, 'a') as stream:
        stream.write(json.dumps(dict(goal=goal, system=system, values=current)) + '\n')
    row = observations()[goal]
    if row[system] is None:
      self.skipTest(system + ' has no recorded measurement')
    self.assertEqual(current, normalized(row[system]))
    proc, actual = sprite_results(SOURCE, goal, timeout=TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(normalized(actual.splitlines()), normalized(row['sprite']))
    if (system, goal) in DIVERGENCES:
      self.skipTest('documented divergence: ' + DIVERGENCES[system, goal])
    self.assertEqual(current, normalized(VALUES[goal]))
    self.assertEqual(normalized(actual.splitlines()), current)


for goal in GOALS:
  for system in ('pakcs', 'kics2'):
    def test(self, goal=goal, system=system):
      self.check(goal, system)
    setattr(TestEncapsulationOracles, 'test_' + system + '_' + goal, test)


if __name__ == '__main__':
  unittest.main()
