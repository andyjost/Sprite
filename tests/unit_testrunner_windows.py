"""Exercise Windows runner branches on every test platform."""
import cytest
from testrunner import cli, prepare, procs, scheduler, selection
from testrunner.manifest import Manifest
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock


class TestWindowsRunner(unittest.TestCase):
  def test_native_tool_commands(self):
    command = ['sprite-exec', '-g', 'main']
    with mock.patch.object(sys, 'platform', 'win32'):
      self.assertEqual(cytest.tool_command(command),
          [sys.executable, '-m', 'curry', '-g', 'main'])
      self.assertEqual(cytest.tool_command(['sprite-make', '--image', 'M']),
          [sys.executable, '-m', 'curry.tools.make', '--image', 'M'])
      self.assertEqual(cytest.tool_command(['python', '-m', 'curry.tools.repl']),
          [sys.executable, '-m', 'curry.tools.repl'])
    with mock.patch.object(sys, 'platform', 'linux'):
      self.assertEqual(cytest.tool_command(command), command)

  def test_windows_interrupt_signals(self):
    signals = types.SimpleNamespace(SIGINT=2, SIGBREAK=21, SIGTERM=15)
    with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(scheduler, 'signal', signals):
      self.assertEqual(scheduler.interrupt_signals(), (2, 21))

  def test_windows_notice_once(self):
    with tempfile.TemporaryDirectory() as directory, \
         mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(cli.shutil, 'which', return_value=None), \
         mock.patch.object(sys, 'stdout', io.StringIO()) as out:
      self.assertEqual(cli.main(['--list', '--fast', '--logdir', directory]), 0)
    self.assertEqual(out.getvalue().count('no Job Object hard memory cap'), 1)

  def test_no_prlimit_and_native_python(self):
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(cli.shutil, 'which', side_effect=AssertionError('prlimit')):
      self.assertEqual(cli.backstop_prefix(1024, '1'), [])
      from curry import config
      with mock.patch.object(config, 'module_object_suffix', return_value='.dll'):
        self.assertEqual(prepare.product_suffixes('cxx', 'interpret:off'), ('.dll',))
      self.assertEqual(prepare.product_suffixes('cxx', 'interpret:new'), ('.img',))
      self.assertEqual(procs.toolchain_in(['python', 'clang-cl', 'link']), ['clang-cl', 'link'])
      job = cli.test_job('unit_x.py', 'cxx', 'stage', Manifest({}), 10, 'logs', {})
      self.assertEqual(job.argv[0], sys.executable)
      self.assertEqual(prepare.command('stage', 'cxx', ['M.curry'])[:3],
                       [sys.executable, '-m', 'curry.tools.make'])

  def test_path_separator(self):
    with mock.patch.object(os, 'pathsep', ';'):
      self.assertEqual(cli.prepend_path('new', 'first;second'), 'new;first;second')
      self.assertEqual(cli.prepend_path('first', 'first;second'), 'first;second')

  def test_start_poll_and_reap(self):
    job = scheduler.Job('unit_x.py', 'cxx', ['python'], 1024, 10, None)
    sched = scheduler.Scheduler([], 2048, 1)
    child = mock.Mock(pid=123)
    child.poll.side_effect = [None, 7]
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(scheduler.subprocess, 'Popen', return_value=child) as popen, \
         mock.patch.object(procs, 'kill_session') as kill:
      sched.start(job)
      options = popen.call_args.kwargs
      self.assertEqual(options['creationflags'], 0x200)
      self.assertNotIn('start_new_session', options)
      sched.running.append(job)
      sched.reap()
      self.assertEqual(sched.running, [job])
      sched.reap()
      self.assertEqual(job.returncode, 7)
      self.assertEqual(job.status, 'FAILED')
      kill.assert_not_called()

  def test_blocking_reap(self):
    job = scheduler.Job('x', 'cxx', [], 1024, 10, None)
    job.proc = mock.Mock(pid=123)
    job.proc.wait.return_value = 0
    job.pid, job.started = 123, time.monotonic()
    sched = scheduler.Scheduler([], 2048, 1)
    sched.running = [job]
    with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(procs, 'kill_session'):
      sched.reap(block=True)
    job.proc.wait.assert_called_once_with()
    self.assertTrue(job.ok)

  def test_unknown_memory_still_times_out(self):
    job = scheduler.Job('x', 'cxx', [], 1024, 1, None)
    job.pid, job.started = 123, 0
    job.proc = mock.Mock()
    job.proc.poll.return_value = None
    sched = scheduler.Scheduler([], 2048, 1)
    sched.running = [job]
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(procs, 'psutil', None), \
         mock.patch.object(procs.subprocess, 'run') as run:
      self.assertEqual(procs.meminfo(), {})
      self.assertFalse(procs.is_alive(123))
      scheduler.Watchdog(sched).tick(now=2)
    self.assertIsNone(job.peak)
    self.assertEqual(job.kill_reason, 'timeout')
    self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '123', '/T', '/F'])

  def test_psutil_descendants_and_orphan_roots(self):
    def process(pid, parent, name, rss):
      return types.SimpleNamespace(info=dict(pid=pid, ppid=parent, name=name,
                                             memory_info=types.SimpleNamespace(rss=rss)))
    psutil = mock.Mock()
    psutil.process_iter.return_value = [process(1, 0, 'python.exe', 10),
                                       process(2, 1, 'clang-cl.exe', 20),
                                       process(3, 0, 'link.exe', 30)]
    psutil.virtual_memory.return_value = types.SimpleNamespace(total=100, available=50)
    with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(procs, 'psutil', psutil):
      self.assertEqual(procs.mem_available(), 50)
      psutil.pid_exists.return_value = True
      self.assertTrue(procs.is_alive(1))
      psutil.pid_exists.return_value = False
      self.assertFalse(procs.is_alive(1))
      self.assertEqual(procs.scan_sessions([1], roots={1: [3]})[1],
                       (60, [1, 2, 3], {1: 'python', 2: 'clang-cl', 3: 'link'}))

  def test_taskkill_includes_known_children(self):
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(procs.subprocess, 'run') as run:
      procs.kill_session(1, roots={1, 2})
    self.assertEqual([call.args[0] for call in run.call_args_list],
                     [['taskkill', '/PID', '2', '/T', '/F'],
                      ['taskkill', '/PID', '1', '/T', '/F']])

  def test_exited_leader_is_not_killed(self):
    child = mock.Mock()
    child.poll.return_value = 0
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(procs.subprocess, 'run') as run:
      self.assertEqual(procs.kill_session(1, roots={1, 2}, leader=child), [2])
    self.assertEqual([call.args[0] for call in run.call_args_list],
                     [['taskkill', '/PID', '2', '/T', '/F']])

  def test_windows_timeout_runs_body_without_alarm(self):
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(cytest.signal, 'setitimer', create=True) as timer:
      with cytest.timeout(1):
        pass
    timer.assert_not_called()

  def test_oracle_selection_does_not_import_cytest(self):
    script = """
import sys
from testrunner import cli
cli.main(['--list', 'func_*.py'])
assert 'cytest' not in sys.modules
"""
    import subprocess
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    self.assertEqual(result.returncode, 0, result.stderr)

  def test_marks(self):
    for platform in ('linux', 'darwin', 'win32'):
      with self.subTest(platform=platform), mock.patch.object(sys, 'platform', platform):
        posix = cytest.posix_only('POSIX')(lambda: None)
        windows = cytest.windows_only('Windows')(lambda: None)
        self.assertEqual(getattr(posix, '__unittest_skip__', False), platform == 'win32')
        self.assertEqual(getattr(windows, '__unittest_skip__', False), platform != 'win32')

  def test_functional_selection_without_oracle(self):
    args = cli.parse_args([])
    selected, notes = cli.select(args, ['cxx'], Manifest({}),
                                 ['unit_x.py', 'func_x.py'], False)
    self.assertEqual([item.filename for item in selected], ['unit_x.py'])
    self.assertEqual(len(notes), 1)
    self.assertIn('no PAKCS oracle', notes[0])
    selected, notes = cli.select(args, ['cxx'], Manifest({}), ['func_x.py'], True)
    self.assertEqual([item.filename for item in selected], ['func_x.py'])
    self.assertEqual(notes, [])

  def test_portable_entry(self):
    import run_tests
    with tempfile.TemporaryDirectory() as directory:
      home = Path(directory)
      with mock.patch.dict(os.environ, SPRITE_HOME=str(home)), \
           mock.patch.object(sys, 'platform', 'win32'), \
           mock.patch.object(run_tests.subprocess, 'call', return_value=0) as call, \
           mock.patch.object(sys, 'stderr', io.StringIO()):
        self.assertEqual(run_tests.main(['--fast']), 1)
        (home / 'lib').mkdir()
        (home / 'lib' / 'libcurryrt.dll').touch()
        self.assertEqual(run_tests.main(['--fast']), 0)
        self.assertEqual(call.call_args.args[0], [sys.executable, '-B', '-m', 'testrunner', '--fast'])
        self.assertEqual(call.call_args.kwargs['env']['SPRITE_HOME'], str(home.resolve()))


if __name__ == '__main__':
  unittest.main()
