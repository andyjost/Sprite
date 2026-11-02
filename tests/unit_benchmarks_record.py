'''The performance record's comparisons, mode, and advisory warnings.'''
import cytest
from benchmarks import counterparts, history, records, suites, run as harness
from unit_perf_history import make_record
import contextlib, io, os, tempfile, types, unittest
from unittest import mock


class TestPerformanceRecord(unittest.TestCase):
  def test_windows_settings_use_running_interpreter(self):
    with mock.patch.object(suites.sys, 'platform', 'win32'):
      self.assertEqual(suites.Settings('install').python, suites.sys.executable)

  def test_counterparts(self):
    import sys
    previous = sys.getrecursionlimit()
    try:
      sys.setrecursionlimit(10000)
      for name, function in counterparts.PROGRAMS.items():
        counterparts.check(name, function())
        with self.assertRaisesRegex(ValueError, 'counterpart value'):
          counterparts.check(name, -1)
    finally:
      sys.setrecursionlimit(previous)

  def test_curry_values(self):
    self.assertEqual(counterparts.curry_value('Tak1', '16\n0.01s\n'), 16)
    self.assertEqual(counterparts.curry_value('Peano', 'S (S O)\n'), 2)
    with self.assertRaises(ValueError):
      counterparts.check('Tak1', counterparts.curry_value('Tak1', 'wrong'))

  def test_wrong_value_refused(self):
    settings = suites.Settings('install')
    item = suites.PythonItem('Tak1', 'python', settings)
    run = types.SimpleNamespace(status='ok', stdout='{"value": 0}',
        returncode=0, error=None, wall=1, cpu=1, peak_rss=1,
        instructions=None, perf=False)
    with mock.patch.object(settings, 'run', return_value=run):
      sample = item.measure()
    self.assertEqual(sample['status'], 'fail')
    self.assertIn('counterpart value', sample['error'])
    run.stdout = '0\n'
    sprite = suites.SpriteExecItem('Tak1', 'cxx', settings)
    with mock.patch.object(settings, 'run', return_value=run):
      invalid = sprite.validate_counterpart()
    self.assertEqual(invalid['status'], 'fail')
    self.assertIn('counterpart value', invalid['error'])
    values = counterparts.EXPECTED['Qsortlet']
    import json
    run.stdout = json.dumps(dict(value=values, eval_cpu=1, eval_wall=1))
    item = suites.PythonItem('Qsortlet', 'python', settings)
    fields = item.parse(run)
    self.assertEqual(fields['extra']['value_count'], 1000)
    self.assertEqual(len(fields['extra']['value_digest']), 64)
    self.assertNotIn('value', fields['extra'])

  def test_ratios_and_old_records(self):
    c = make_record('Tak1', 2)
    p = make_record('Tak1', 1)
    p['backend'] = 'python'
    c['eval_wall'], p['eval_wall'] = 2, 1
    c['eval_wall_clock'] = p['eval_wall_clock'] = 'wall'
    records.add_ratios([c, p])
    self.assertEqual(c['ratios'], {'python': 2})
    other = make_record('Tak1', 3)
    other['commit'] = 'other'
    records.add_ratios([other, p])
    self.assertNotIn('ratios', other)
    stream = io.StringIO()
    records.write_ratios(stream, [c, p])
    self.assertIn('Tak1 Curry / python: 2.000x', stream.getvalue())
    c['meta']['mode'] = {'flags': {'interpret': 'off'}, 'backend': 'llvm',
        'llvmlite': True, 'execution': 'aot'}
    with tempfile.TemporaryDirectory() as d:
      path = os.path.join(d, 'records.jsonl')
      old = make_record('Old', 1)
      with open(path, 'w') as f:
        records.write(f, old)
        records.write(f, c)
      reread = records.read(path)
      self.assertEqual(reread, [old, c])
      self.assertNotIn('mode', history.point(reread[0]))
      self.assertEqual(history.point(reread[1])['ratios'], {'python': 2})
      self.assertEqual(history.point(reread[1])['mode'], c['meta']['mode'])

  def test_warnings(self):
    old, new = make_record('Tak1', 1), make_record('Tak1', 2)
    self.assertEqual(history.timing_warnings(old, new), [])
    old['collections'] = new['collections'] = 0
    old['commit'], new['commit'] = 'before', 'after'
    text = '\n'.join(history.timing_warnings(old, new))
    for word in ('WARNING', 'Tak1', 'before', 'after', '1 s', '2 s'):
      self.assertIn(word, text)
    stream = io.StringIO()
    history.report(stream, {records.key(old): old}, [new], 'test', 'cpu', 0.1)
    self.assertIn('WARNING throughput/Tak1', stream.getvalue())
    new['cpu'], new['wall'] = 1.99, 3.98
    self.assertEqual(history.timing_warnings(old, new), [])
    new['cpu'] = 0.5
    self.assertTrue(history.timing_warnings(old, new))
    new['steps'] += 1
    self.assertEqual(history.timing_warnings(old, new), [])
    new['steps'] = old['steps']
    new['collections'] = 1
    self.assertEqual(history.timing_warnings(old, new), [])
    new['collections'] = old['collections']
    new['forks'] = None
    self.assertEqual(history.timing_warnings(old, new), [])
    self.assertEqual(history.timing_warnings(None, new), [])

  def test_pakcs_cpu_clock(self):
    settings = suites.Settings('install', pakcs='pakcs')
    sprite = suites.SpriteExecItem('Peano', 'cxx', settings)
    pakcs = suites.PakcsItem('Peano', 'pakcs', settings)
    self.assertIn(suites.comparison_goal('Peano'), sprite.command()[0])
    self.assertIn(suites.comparison_goal('Peano'), pakcs.command()[0])
    c = sprite.parse(types.SimpleNamespace(
        stdout='{"eval_cpu": 2, "eval_wall": 3}', stderr=''))
    p = pakcs.parse(types.SimpleNamespace(
        stdout='Execution time: 500 msec. / elapsed: 1000 msec.'))
    recs = []
    for backend, fields in [('cxx', c), ('pakcs', p)]:
      sample = records.sample(types.SimpleNamespace(status='ok', returncode=0,
          error=None, wall=4, cpu=3, peak_rss=1, instructions=None, perf=False), fields)
      recs.append(records.summarize('throughput', 'Peano', backend, None, [sample], {}))
    for record in recs:
      self.assertEqual(record['eval_cpu_clock'], 'cpu_user_system')
    self.assertIsNone(recs[1]['eval_wall'])
    records.add_ratios(recs)
    self.assertEqual(recs[0]['ratios']['pakcs'], 2)
    for clock in ('wall', None):
      for record in recs:
        record.pop('ratios', None)
      recs[1]['eval_cpu_clock'] = clock
      records.add_ratios(recs)
      self.assertNotIn('ratios', recs[0])

  def test_pakcs_timeout_is_advisory(self):
    settings = suites.Settings('install', pakcs='pakcs', warmup=0)
    items = [suites.SpriteExecItem('Peano', 'cxx', settings),
             suites.PakcsItem('Peano', 'pakcs', settings)]
    good = records.sample(types.SimpleNamespace(status='ok', returncode=0,
        error=None, wall=1, cpu=1, peak_rss=1, instructions=None, perf=False))
    timeout = dict(good, status='timeout', error='timed out')
    for sprite_status, expected in [('ok', 0), ('fail', 1)]:
      output = io.StringIO()
      with mock.patch.object(suites, 'build', return_value=items), \
           mock.patch.object(suites.Settings, 'metadata', return_value={
               'cpu_model': None, 'cores': None, 'mem_gb': None}), \
           mock.patch.object(suites.Settings, 'mode', return_value={}), \
           mock.patch.object(suites.Item, 'unavailable', return_value=None), \
           mock.patch.object(harness.os, 'access', return_value=True), \
           mock.patch.object(records, 'commit', return_value='review'), \
           mock.patch.object(harness, 'measure_item', side_effect=[
               [dict(good, status=sprite_status)], [timeout]]), \
           contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
        status = harness.main(['Peano', '-b', 'cxx', '-b', 'pakcs',
            '--pakcs', 'pakcs', '--no-perf', '-r', '1', '-w', '0'])
      self.assertEqual(status, expected)
      import json
      written = [json.loads(line) for line in output.getvalue().splitlines()]
      self.assertEqual(written[1]['backend'], 'pakcs')
      self.assertEqual(written[1]['status'], 'timeout')
      self.assertEqual(written[1]['error'], 'timed out')

  def test_throughput_pinned_and_mode(self):
    from benchmarks import DEFAULT_SPRITE_HOME
    settings = suites.Settings(DEFAULT_SPRITE_HOME,
        env={'SPRITE_INTERPRETER_FLAGS': 'interpret:all,jit:off'})
    item = suites.SpriteExecItem('Tak1', 'cxx', settings)
    _, env, _ = item.command()
    self.assertIn('interpret:off', env['SPRITE_INTERPRETER_FLAGS'])
    self.assertNotIn('interpret:all', env['SPRITE_INTERPRETER_FLAGS'])
    mode = settings.mode(env)
    self.assertEqual(mode['flags']['interpret'], 'off')
    self.assertEqual(mode['flags']['jit'], 'off')
    self.assertEqual(mode['execution'], 'aot')
    self.assertIsInstance(mode['llvmlite'], bool)
    self.assertIn(mode['backend'], ('llvm', 'cxx', None))

  def test_nightly_opponents(self):
    settings = suites.Settings('install', pakcs='pakcs')
    with tempfile.TemporaryDirectory() as d:
      items = suites.build('throughput', ['Tak1', 'Hello', 'Peano', 'PaliFunPats', 'Fib'],
          ['cxx', 'python', 'pakcs'], settings, d, nightly=True)
    self.assertEqual([i.program for i in items if i.backend == 'pakcs'],
        list(suites.PAKCS_NIGHTLY))
    self.assertEqual([i.program for i in items if i.backend == 'python'],
        ['Tak1', 'Peano'])
    settings.timeout = 300
    with mock.patch.object(suites.measure, 'run_command') as run:
      settings.run(['pakcs'], {}, '.')
    self.assertEqual(run.call_args.kwargs['timeout'], 60)
