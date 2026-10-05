'''
Tests for the nightly performance job: the chart page under
docs/source/extra/perf (its functions run under node on points made from
hand-made records and from the baseline records), the scripts under
.github/scripts that run the suites and publish the history (the publish
script against a bare repository made for the test), and the workflow that
ties them together.  The page tests need node; the publish test needs git
2.42 or later.
'''
import cytest # from ./lib; must be first
from benchmarks import NIGHTLY, ROOTDIR, history, records
import json, os, re, shutil, subprocess, sys, tempfile, unittest

PERF_DIR = os.path.join(ROOTDIR, 'docs', 'source', 'extra', 'perf')
PERF_JS = os.path.join(PERF_DIR, 'perf.js')
PERF_HTML = os.path.join(PERF_DIR, 'index.html')
SCRIPTS = os.path.join(ROOTDIR, '.github', 'scripts')
PUBLISH = os.path.join(SCRIPTS, 'perf-history.sh')
RUN_PERF = os.path.join(SCRIPTS, 'run-perf.sh')
WORKFLOWS = os.path.join(ROOTDIR, '.github', 'workflows')
WORKFLOW = os.path.join(WORKFLOWS, 'perf.yml')
RESULTS = os.path.join(
    ROOTDIR, 'tests', 'data', 'curry', 'benchmarks', 'results'
  )
BRANCH = 'perf-history'
NODE = shutil.which('node')
GIT = shutil.which('git')
TIMEOUT = 120
# Renders the points of a JSON file with the options it holds and prints the
# markup with the layout of every panel.
DRIVER = '''
const perf = require(process.argv[2]);
const input = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
if (typeof input.options.now === 'string') {
  input.options.now = Date.parse(input.options.now);
}
const registry = {};
const html = perf.renderPage(input.points, input.options, registry);
const panels = {};
Object.keys(registry).forEach(function (id) {
  const e = registry[id];
  panels[id] = {
    suite: e.series.suite, program: e.series.program, backend: e.series.backend
  , variant: e.series.variant, metric: e.metric, ymax: e.layout.ymax
  , marks: e.layout.marks
  };
});
process.stdout.write(JSON.stringify({html: html, panels: panels}));
'''


def read(filename):
  with open(filename) as stream:
    return stream.read()


def git_version():
  '''The version of git as a tuple, or None.'''
  if not GIT:
    return None
  proc = subprocess.run(
      [GIT, '--version'], capture_output=True, text=True, timeout=TIMEOUT
    )
  found = re.search(r'(\d+)\.(\d+)', proc.stdout)
  return tuple(int(x) for x in found.groups()) if found else None


def make_point(
    program, date, cpu, steps=5, status='ok', suite='throughput'
  , backend='cxx', variant=None, error=None, commit='abc123def456'
  ):
  '''A point of the page, as history.point makes it.'''
  point = dict.fromkeys(history.POINT_FIELDS)
  point.update(
      suite=suite, program=program, backend=backend, variant=variant
    , date=date, commit=commit, label='nightly-1', status=status, error=error
    , wall=None if cpu is None else cpu * 2, cpu=cpu, eval_wall=None
    , compile=None, peak_rss=None if cpu is None else int(cpu * 1048576)
    , steps=None if status != 'ok' else steps, forks=0
    )
  return point


def make_record(program, cpu, status='ok', steps=5):
  '''A record with one sample, for the publish test.'''
  sample = {
      'status': status, 'returncode': 0 if status == 'ok' else 1
    , 'error': None if status == 'ok' else 'boom', 'wall': cpu * 2, 'cpu': cpu
    , 'peak_rss': 1000, 'eval_wall': None, 'eval_cpu': None, 'compile': None
    , 'steps': steps, 'forks': 0, 'collections': None, 'extra': {}
    }
  return records.summarize(
      'throughput', program, 'cxx', None, [sample], {}, commit='abc'
    )


@unittest.skipUnless(NODE, 'node is not installed')
class TestPage(unittest.TestCase):
  '''The chart page: its functions under node.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-perf-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  def node(self, script, *args):
    proc = subprocess.run(
        [NODE] + list(script) + list(args), capture_output=True, text=True
      , timeout=TIMEOUT, cwd=self.tmpdir
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def evaluate(self, expression):
    '''The JSON value of a JavaScript expression over the module perf.'''
    code = 'const perf = require(%s); ' % json.dumps(PERF_JS) \
         + 'process.stdout.write(JSON.stringify(%s));' % expression
    return json.loads(self.node(['-e', code]))

  def render(self, points, **options):
    '''The markup and the panels of the page for the points.'''
    driver = os.path.join(self.tmpdir, 'driver.js')
    with open(driver, 'w') as stream:
      stream.write(DRIVER)
    data = os.path.join(self.tmpdir, 'input.json')
    with open(data, 'w') as stream:
      json.dump({'points': points, 'options': options}, stream)
    return json.loads(self.node([driver], PERF_JS, data))

  def test_baseline(self):
    '''
    The baseline records render: one figure per suite, one panel per item.
    The later record sets of the directory are left out, so that every item
    has one point.
    '''
    recs = []
    for name in sorted(os.listdir(RESULTS)):
      if name.startswith('baseline-') and name.endswith('.jsonl'):
        recs.extend(records.read(os.path.join(RESULTS, name)))
    out = self.render(
        history.points(recs), metric='default', range='all'
      , now='2026-10-04T00:00:00Z'
      )
    html = out['html']
    self.assertEqual(
        re.findall(r'<figure class="suite" id="suite-([a-z]+)">', html)
      , ['throughput', 'compile', 'import', 'memory']
      )
    items = set(records.key(r) for r in recs)
    self.assertEqual(len(out['panels']), len(items))
    self.assertEqual(html.count('<svg class="panel-chart"'), len(items))
    self.assertEqual(html.count('<tr><td>'), len(items))
    good = sum(1 for r in recs if r['status'] == 'ok')
    self.assertEqual(html.count('class="lone"'), good)
    self.assertEqual(html.count('class="fail"'), len(recs) - good)
    self.assertNotIn('class="line"', html)
    throughput = html[:html.index('id="suite-compile"')]
    self.assertIn('Metric: CPU seconds.', throughput)
    memory = html[html.index('id="suite-memory"'):]
    self.assertIn('Metric: peak RSS.', memory)
    # The baseline holds three backends, so the titles name them.
    self.assertIn('<span class="name">Fib [cxx]</span>', throughput)
    self.assertIn('<span class="name">Half (collector=on) [cxx]</span>', memory)
    key = ('throughput', 'Fib', 'cxx', None)
    fib = [r for r in recs if records.key(r) == key][0]
    label = '%s s' % float('%.3g' % fib['cpu'])
    self.assertIn('>' + label + '</text>', throughput)
    panel = [
        p for p in out['panels'].values()
          if (p['suite'], p['program'], p['backend']) == key[:3]
      ][0]
    self.assertEqual(panel['metric'], 'cpu')
    self.assertEqual(len(panel['marks']), 1)
    self.assertEqual(panel['marks'][0]['value'], fib['cpu'])
    self.assertGreaterEqual(panel['ymax'], fib['cpu'])
    # A failed item says so.
    poker = throughput[throughput.index('PokerChoice [cxx]'):]
    self.assertIn('<span class="status critical">failed</span>', poker[:200])

  def test_two_runs(self):
    '''Lines, deltas, changed counters, failures, escaping, and the range.'''
    points = [
        make_point('Fib', '2026-10-01T05:00:00Z', 1.0)
      , make_point('Fib', '2026-10-02T05:00:00Z', 1.5)
      , make_point('Rev', '2026-10-01T05:00:00Z', 1.0)
      , make_point('Rev', '2026-10-02T05:00:00Z', 0.95)
      , make_point('Chg', '2026-10-01T05:00:00Z', 1.0, steps=5)
      , make_point('Chg', '2026-10-02T05:00:00Z', 1.0, steps=6)
      , make_point(
            'Tak', '2026-10-03T05:00:00Z', None, status='fail'
          , error='exit status 1: boom'
          )
      , make_point('Tak', '2026-10-02T05:00:00Z', 2.0)
      , make_point('Tak', '2026-10-01T05:00:00Z', 1.0)
      , make_point('A<B', '2026-10-02T05:00:00Z', 1.0)
      ]
    out = self.render(
        points, metric='default', range='all', now='2026-10-04T00:00:00Z'
      )
    html = out['html']
    self.assertEqual(html.count('<figure '), 1)
    self.assertEqual(len(out['panels']), 5)
    # One backend: the titles name the program alone, escaped.
    self.assertIn('<span class="name">Fib</span>', html)
    self.assertIn('<span class="name">A&lt;B</span>', html)
    self.assertNotIn('A<B', html)
    # The dates of the figure.
    self.assertIn('>2026-10-01</text>', html)
    self.assertIn('>2026-10-03</text>', html)
    # Fib: a line of two points and a delta beyond the noise band.
    fib = html[html.index('<span class="name">Fib</span>'):]
    fib = fib[:fib.index('</svg>')]
    self.assertIn(
        '<span class="delta slower" title="against the previous run">'
        '+50% slower</span>'
      , fib
      )
    line = r'<path class="line" d="M[\d.]+ [\d.]+ L[\d.]+ [\d.]+"/>'
    self.assertEqual(len(re.findall(line, fib)), 1)
    self.assertIn('>1.5 s</text>', fib)
    self.assertNotIn('class="changed"', fib)
    # Rev: within the band, no verdict word.
    rev = html[html.index('<span class="name">Rev</span>'):]
    self.assertIn(
        '<span class="delta same" title="against the previous run">-5%</span>'
      , rev[:300]
      )
    # Chg: the steps changed.
    chg = html[html.index('<span class="name">Chg</span>'):]
    chg = chg[:chg.index('</svg>')]
    self.assertIn('<span class="note">steps changed</span>', chg)
    self.assertEqual(chg.count('class="changed"'), 1)
    panels = out['panels'].values()
    marks = [p for p in panels if p['program'] == 'Chg'][0]['marks']
    self.assertEqual([m['changed'] for m in marks], [False, True])
    self.assertEqual(marks[1]['previousSteps'], 5)
    # Tak: the points are sorted by date, the last run failed, the line
    # covers the two good runs, the cross sits on the baseline.
    tak = [p for p in panels if p['program'] == 'Tak'][0]
    self.assertEqual([m['value'] for m in tak['marks']], [1.0, 2.0, None])
    self.assertEqual(tak['ymax'], 2)
    section = html[html.index('<span class="name">Tak</span>'):]
    section = section[:section.index('</svg>')]
    self.assertIn('<span class="status critical">failed</span>', section)
    self.assertEqual(section.count('class="fail"'), 1)
    self.assertEqual(section.count('<path class="line"'), 1)
    self.assertIn('>2 s</text>', section)
    # The table: the last run of every item against the previous one.
    opening = '<table class="table-view" id="table-throughput" hidden>'
    table = html[html.index(opening):]
    rows = re.findall(r'<tr><td>(.*?)</td></tr>', table)
    self.assertEqual(len(rows), 5)
    by_name = {row.split('</td>')[0]: row for row in rows}
    self.assertIn(
        '<td class="num">1.5 s</td><td class="num">1 s</td>'
        '<td class="num">1.50 slower</td>'
      , by_name['Fib']
      )
    self.assertIn('<td class="num">6 (changed from 5)</td>', by_name['Chg'])
    self.assertIn(
        '<td class="num">-</td><td class="num">2 s</td><td class="num">-</td>'
        '<td class="num">-</td><td>fail: exit status 1: boom'
      , by_name['Tak']
      )
    self.assertIn('<code>abc123def456</code>', by_name['Fib'])
    # Another metric and a range without runs.
    out = self.render(
        points, metric='steps', range='month', now='2027-01-01T00:00:00Z'
      )
    html = out['html']
    self.assertIn('Metric: rewrite steps.', html)
    self.assertEqual(html.count('no runs in this range'), 5)
    self.assertNotIn('class="line"', html)
    self.assertEqual(sum(len(p['marks']) for p in out['panels'].values()), 0)
    # The table ignores the range; the steps have no unit.
    self.assertIn(
        '<td class="num">6</td><td class="num">5</td>'
        '<td class="num">1.20 slower</td>'
      , html
      )
    self.assertIn(
        '<p class="empty">The history has no records yet.</p>'
      , self.render([])['html']
      )

  def test_functions(self):
    '''The data URLs, the formats, the ceilings, the verdicts.'''
    urls = self.evaluate(
        "perf.historyUrls({hostname: 'owner.github.io', "
        "pathname: '/Repo/perf/index.html', search: ''}, '')"
      )
    self.assertEqual(urls, [
        'https://raw.githubusercontent.com/owner/Repo/%s/points.json' % BRANCH
      , 'points.json'
      ])
    self.assertEqual(
        self.evaluate(
            "perf.historyUrls({hostname: 'localhost', pathname: '/perf/', "
            "search: '?history=x.json'}, 'cfg.json')"
          )
      , ['x.json']
      )
    self.assertEqual(
        self.evaluate(
            "perf.historyUrls({hostname: 'localhost', pathname: '/perf/', "
            "search: ''}, 'cfg.json')"
          )
      , ['cfg.json', 'points.json']
      )
    self.assertEqual(
        self.evaluate(
            "perf.historyUrls({hostname: 'docs.example.org', "
            "pathname: '/Repo/perf/', search: ''}, '')"
          )
      , ['points.json']
      )
    self.assertEqual(self.evaluate("perf.BRANCH"), BRANCH)
    self.assertEqual(
        self.evaluate(
            "[perf.formatValue(1.3125, 'cpu'),"
            " perf.formatValue(0.024419, 'cpu'),"
            " perf.formatValue(36.001872, 'wall'),"
            " perf.formatValue(352.5, 'peak_rss'),"
            " perf.formatValue(12.345, 'peak_rss'),"
            " perf.formatValue(33629915, 'steps'),"
            " perf.formatValue(null, 'cpu'),"
            " perf.formatNumber(1500000, 'forks')]"
          )
      , ['1.31 s', '0.0244 s', '36 s', '353 MB', '12.3 MB', '33,629,915', '-'
        , '1,500,000'
        ]
      )
    self.assertEqual(
        self.evaluate(
            "[2, 0.3, 0, 7.1, 123, 1, 0.0244].map(perf.niceCeiling)"
          )
      , [2, 0.30000000000000004, 1, 8, 150, 1, 0.025]
      )
    self.assertEqual(
        self.evaluate("[1.05, 1.11, 0.89, 0.9].map(perf.verdictOf)")
      , ['same', 'slower', 'faster', 'same']
      )
    self.assertEqual(
        self.evaluate(
            "[perf.metricOf('throughput', 'default'),"
            " perf.metricOf('memory', 'default'),"
            " perf.metricOf('memory', 'wall'),"
            " perf.metricOf('compile', 'bogus')]"
          )
      , ['cpu', 'peak_rss', 'wall', 'cpu']
      )
    point = make_point('Fib', '2026-10-01T05:00:00Z', 2.0)
    self.assertEqual(
        self.evaluate(
            "[perf.valueOf(%s, 'cpu'), perf.valueOf(%s, 'peak_rss'),"
            " perf.valueOf(%s, 'eval_wall')]" % ((json.dumps(point),) * 3)
          )
      , [2.0, 2.0, None]
      )

  def test_markup(self):
    '''The page names the script, the controls, and the metrics.'''
    html = read(PERF_HTML)
    self.assertIn('<script src="perf.js"></script>', html)
    for name in ('charts', 'metric', 'range', 'status', 'tooltip', 'data-link'):
      self.assertIn('id="%s"' % name, html)
    metrics = self.evaluate('Object.keys(perf.METRICS)')
    options = re.findall(r'<option value="([a-z_]+)">', html)
    ranges = self.evaluate('Object.keys(perf.RANGES)')
    self.assertEqual(options, ranges + ['default'] + metrics)
    self.assertIn('prefers-color-scheme: dark', html)
    self.assertIn(BRANCH, html)


class TestScripts(unittest.TestCase):
  '''The scripts of the job.'''

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-perf-test-')
    self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

  def test_scripts(self):
    '''Executable, parsable, and refusing a call without arguments.'''
    for script in (RUN_PERF, PUBLISH):
      self.assertTrue(os.access(script, os.X_OK), script)
      self.assertTrue(read(script).startswith('#!/bin/bash\n'))
      proc = subprocess.run(
          ['bash', '-n', script], capture_output=True, text=True
        , timeout=TIMEOUT
        )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      proc = subprocess.run(
          ['bash', script], capture_output=True, text=True, timeout=TIMEOUT
        , cwd=self.tmpdir
        )
      self.assertEqual(proc.returncode, 2)
      self.assertIn('usage:', proc.stderr)
    text = read(RUN_PERF)
    for suite in ('throughput', 'compile', 'import'):
      self.assertIn('suite %s' % suite, text)
    self.assertIn('--nightly', text)
    self.assertIn('-b cxx', text)

  def git(self, *args, **kwds):
    proc = subprocess.run(
        [GIT] + list(args), capture_output=True, text=True, timeout=TIMEOUT
      , **kwds
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    return proc.stdout

  def commits(self, remote):
    '''The number of commits of the history branch of ``remote``.'''
    return self.git('-C', remote, 'rev-list', '--count', BRANCH).strip()

  def show(self, remote, path):
    '''The content of ``path`` on the history branch of ``remote``.'''
    return self.git('-C', remote, 'show', '%s:%s' % (BRANCH, path))

  def worktrees(self, work):
    '''The number of worktrees of the checkout.'''
    return len(self.git('-C', work, 'worktree', 'list').splitlines())

  def publish(self, work, env, *files):
    return subprocess.run(
        ['bash', PUBLISH] + list(files), capture_output=True, text=True
      , timeout=TIMEOUT, cwd=work, env=env
      )

  @unittest.skipUnless(GIT, 'git is not installed')
  def test_publish(self):
    '''
    The publish script against a bare repository: the first run starts the
    branch, the second appends and reports the change, a bad file changes
    nothing.
    '''
    version = git_version()
    if version is None or version < (2, 42):
      self.skipTest('the orphan worktree needs git 2.42')
    remote = os.path.join(self.tmpdir, 'remote.git')
    work = os.path.join(self.tmpdir, 'work')
    runner = os.path.join(self.tmpdir, 'runner')
    os.makedirs(runner)
    # A repository with the harness and the script, and its bare origin.
    package = os.path.join(work, 'tests', 'lib', 'benchmarks')
    shutil.copytree(
        os.path.join(ROOTDIR, 'tests', 'lib', 'benchmarks'), package
      , ignore=shutil.ignore_patterns('__pycache__')
      )
    os.makedirs(os.path.join(work, '.github', 'scripts'))
    shutil.copy(PUBLISH, os.path.join(work, '.github', 'scripts'))
    self.git('init', '-q', '-b', 'main', work)
    self.git('-C', work, 'add', '-A')
    self.git(
        '-C', work, '-c', 'user.name=t', '-c', 'user.email=t@example.org'
      , 'commit', '-q', '-m', 'init'
      )
    self.git('init', '-q', '--bare', remote)
    self.git('-C', work, 'remote', 'add', 'origin', remote)
    self.git('-C', work, 'push', '-q', 'origin', 'main')
    env = dict(os.environ)
    env.update(
        PYTHON=sys.executable, RUNNER_TEMP=runner, HISTORY_BRANCH=BRANCH
      , GITHUB_STEP_SUMMARY=os.path.join(self.tmpdir, 'summary.md')
      , GITHUB_RUN_ID='123', GITHUB_REPOSITORY='owner/repo'
      , GITHUB_SERVER_URL='https://github.com'
      )
    env.pop('PYTHONPATH', None)
    first = os.path.join(self.tmpdir, 'first.jsonl')
    with open(first, 'w') as stream:
      records.write(stream, make_record('A', 1.0))
      records.write(stream, make_record('B', 1.0))
    # The first run starts the branch.
    proc = self.publish(work, env, first)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertIn('origin has no branch %s: starting it' % BRANCH, proc.stdout)
    self.assertIn(
        'first.jsonl: 2 records against the previous run', proc.stdout
      )
    self.assertIn('only-new', proc.stdout)
    self.assertIn('pushed %s of origin' % BRANCH, proc.stdout)
    files = self.git('-C', remote, 'ls-tree', '-r', '--name-only', BRANCH)
    self.assertEqual(
        files.split(), ['README.md', 'points.json', 'records/throughput.jsonl']
      )
    self.assertEqual(self.commits(remote), '1')
    shown = self.show(remote, 'records/throughput.jsonl')
    self.assertEqual(len(shown.strip().splitlines()), 2)
    message = self.git('-C', remote, 'log', '-1', '--format=%B', BRANCH)
    self.assertIn('https://github.com/owner/repo/actions/runs/123', message)
    summary = read(env['GITHUB_STEP_SUMMARY'])
    self.assertIn('## Against the previous run', summary)
    self.assertIn('```\nfirst.jsonl: 2 records', summary)
    # The worktree and the branch are gone from the checkout.
    self.assertEqual(self.worktrees(work), 1)
    self.assertEqual(self.git('-C', work, 'branch', '--list', BRANCH), '')
    self.assertFalse(os.path.exists(os.path.join(runner, 'perf-history')))
    # The second run appends and reports the change.
    second = os.path.join(self.tmpdir, 'second.jsonl')
    with open(second, 'w') as stream:
      records.write(stream, make_record('A', 1.5, steps=6))
      records.write(stream, make_record('B', 1.0))
    proc = self.publish(work, env, second)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertNotIn('starting it', proc.stdout)
    self.assertIn('slower', proc.stdout)
    self.assertIn('steps 5->6', proc.stdout)
    self.assertIn('pushed %s of origin' % BRANCH, proc.stdout)
    self.assertEqual(self.commits(remote), '2')
    shown = self.show(remote, 'records/throughput.jsonl')
    self.assertEqual(len(shown.strip().splitlines()), 4)
    points = json.loads(self.show(remote, 'points.json'))
    self.assertEqual(
        [(p['program'], p['cpu']) for p in points['points']]
      , [('A', 1.0), ('A', 1.5), ('B', 1.0), ('B', 1.0)]
      )
    self.assertEqual(self.worktrees(work), 1)
    # A file that cannot be read: a failure and no commit.
    bad = os.path.join(self.tmpdir, 'bad.jsonl')
    with open(bad, 'w') as stream:
      stream.write('{}\n')
    proc = self.publish(work, env, bad)
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn('history: ', proc.stderr)
    self.assertEqual(self.commits(remote), '2')
    self.assertEqual(self.worktrees(work), 1)


class TestWorkflow(unittest.TestCase):
  '''The workflow and the names shared between its parts.'''

  def test_workflow(self):
    text = read(WORKFLOW)
    for needle in (
        'schedule:', 'cron:', 'workflow_dispatch:', 'permissions:'
      , 'contents: write', 'concurrency:', 'continue-on-error: true'
      , 'run-perf.sh', 'perf-history.sh', 'HISTORY_BRANCH: ' + BRANCH
      , 'upload-artifact', 'steps.measure.outcome'
      ):
      self.assertIn(needle, text)
    self.assertNotIn('secrets.', text)
    # The push jobs are unchanged: the CI workflow knows nothing of the job.
    ci = read(os.path.join(WORKFLOWS, 'ci.yml'))
    self.assertNotIn('run-perf.sh', ci)
    self.assertNotIn('perf-history', ci)

  def test_interpreter_job(self):
    '''
    The CI workflow runs the interpreter tests and the functional suites
    with every module interpreted on request (the input ``interpreter``),
    through the extra flags of run-tests.sh.
    '''
    ci = read(os.path.join(WORKFLOWS, 'ci.yml'))
    self.assertIn('      interpreter:\n', ci)
    self.assertIn("inputs.interpreter", ci)
    self.assertIn('  interpreter:\n    name: cxx backend, interpreter', ci)
    self.assertIn('SPRITE_TEST_FLAGS: interpret:all', ci)
    self.assertIn("run-tests.sh cxx 'unit_cxx_interp.py' 1/1", ci)
    self.assertIn("run-tests.sh cxx 'func_*.py' 1/1", ci)
    # The push jobs are unchanged: the job runs on request only.
    job = ci[ci.index('  interpreter:\n'):ci.index('  docs:\n')]
    self.assertIn(
        "if: github.event_name == 'workflow_dispatch' && inputs.interpreter"
      , job
      )
    script = read(os.path.join(SCRIPTS, 'run-tests.sh'))
    self.assertIn('${SPRITE_TEST_FLAGS:+,$SPRITE_TEST_FLAGS}', script)
    # The expansion the script uses, with the variable unset, empty, and set.
    cmd = 'echo "backend:cxx${SPRITE_TEST_FLAGS:+,$SPRITE_TEST_FLAGS}"'
    for extra, expected in [
        (None, 'backend:cxx'), ('', 'backend:cxx')
      , ('interpret:all', 'backend:cxx,interpret:all')
      ]:
      env = dict(os.environ)
      env.pop('SPRITE_TEST_FLAGS', None)
      if extra is not None:
        env['SPRITE_TEST_FLAGS'] = extra
      proc = subprocess.run(
          ['bash', '-c', cmd], capture_output=True, text=True, env=env
        , timeout=TIMEOUT
        )
      self.assertEqual(proc.stdout.strip(), expected, extra)

  def test_names_agree(self):
    '''The branch and the selection are spelled alike everywhere.'''
    self.assertIn("var BRANCH = '%s';" % BRANCH, read(PERF_JS))
    self.assertIn('${HISTORY_BRANCH:-%s}' % BRANCH, read(PUBLISH))
    self.assertIn(BRANCH, history.README)
    readme = read(os.path.join(ROOTDIR, 'tests', 'README'))
    self.assertIn(BRANCH, readme)
    self.assertIn('--nightly', readme)
    self.assertIn('history DIR FILE...', readme)
    self.assertEqual(len(NIGHTLY), 10)

  def test_docs(self):
    '''The page is copied with the documentation and linked from it.'''
    source = os.path.join(ROOTDIR, 'docs', 'source')
    conf = read(os.path.join(source, 'conf.py'))
    self.assertIn("html_extra_path = ['extra']", conf)
    self.assertIn('   Performance\n', read(os.path.join(source, 'index.rst')))
    page = read(os.path.join(source, 'Performance.rst'))
    self.assertIn('<perf/index.html>', page)
    self.assertIn(BRANCH, page)
    self.assertTrue(os.path.isfile(PERF_HTML))
    self.assertTrue(os.path.isfile(PERF_JS))


if __name__ == '__main__':
  unittest.main()
