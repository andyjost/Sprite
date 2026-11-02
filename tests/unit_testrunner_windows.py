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
      self.assertEqual(cytest.tool_command(['python', '-m', 'curry.tools.icy']),
          [sys.executable, '-m', 'curry.tools.icy'])
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
         mock.patch.object(procs, 'kill_session') as kill, \
         mock.patch.object(procs, 'start_windows'):
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
         mock.patch.dict(procs._WINDOWS, {123: {'job': None}}, clear=True), \
         mock.patch.object(procs.subprocess, 'run') as run:
      self.assertEqual(procs.meminfo(), {})
      self.assertFalse(procs.is_alive(123))
      scheduler.Watchdog(sched).tick(now=2)
    self.assertIsNone(job.peak)
    self.assertEqual(job.kill_reason, 'timeout')
    run.assert_not_called()
    job.proc.kill.assert_called_once_with()

  def test_fallback_rejects_old_children_and_recycled_members(self):
    def entry(parent, born, name='python'):
      return (parent, None, 10, b'R', name, born)
    state = {'job': None, 'born': 100, 'identities': {1: 100}}
    table = {1: entry(0, 100), 2: entry(1, 101), 3: entry(2, 50)}
    fake = mock.Mock()
    fake.NoSuchProcess = ProcessLookupError
    fake.AccessDenied = PermissionError
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.dict(procs._WINDOWS, {1: state}, clear=True), \
         mock.patch.object(procs, 'psutil', fake), \
         mock.patch.object(procs, '_table_windows', side_effect=lambda: table):
      self.assertEqual(procs.scan_sessions([1])[1][1], [1, 2])
      table[2] = entry(0, 200, 'unrelated')
      self.assertEqual(procs.scan_sessions([1], roots={1: [1, 2]})[1][1], [1])
      fake.Process.return_value.create_time.return_value = 100
      self.assertEqual(procs.kill_session(1), [1])
      fake.Process.assert_called_once_with(1)

  def test_job_members_and_termination(self):
    job = mock.Mock()
    job.members.return_value = [2]
    fake = mock.Mock()
    fake.NoSuchProcess = ProcessLookupError
    fake.AccessDenied = PermissionError
    fake.Process.return_value.memory_info.return_value.rss = 42
    fake.Process.return_value.name.return_value = 'child.exe'
    state = {'job': job, 'born': 100, 'identities': {1: 100}}
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.dict(procs._WINDOWS, {1: state}, clear=True), \
         mock.patch.object(procs, 'psutil', fake), \
         mock.patch.object(procs, '_table_windows', side_effect=AssertionError('parent walk')):
      self.assertEqual(procs.scan_sessions([1])[1], (42, [2], {2: 'child'}))
      self.assertEqual(procs.kill_session(1, reason='timeout'), [2])
      job.terminate.assert_called_once_with()
      procs.close_windows(1)
      job.close.assert_called_once_with()

  def test_kernel_job_calls(self):
    import ctypes
    kernel = mock.Mock()
    kernel.CreateJobObjectW.return_value = 77
    kernel.SetInformationJobObject.return_value = True
    kernel.AssignProcessToJobObject.return_value = True
    kernel.TerminateJobObject.return_value = True
    def query(handle, kind, buffer, size, returned):
      self.assertEqual((handle, kind), (77, 3))
      ctypes.c_uint32.from_buffer(buffer, 4).value = 1
      ctypes.c_size_t.from_buffer(buffer, 8).value = 123
      return True
    kernel.QueryInformationJobObject.side_effect = query
    with mock.patch.object(ctypes, 'WinDLL', return_value=kernel, create=True):
      job = procs.WindowsJob(types.SimpleNamespace(_handle=99))
      args = kernel.SetInformationJobObject.call_args.args
      self.assertEqual(args[:2], (77, 9))
      self.assertEqual(args[2]._obj.basic.flags, 0x2000)
      kernel.AssignProcessToJobObject.assert_called_once_with(77, 99)
      self.assertEqual(job.members(), [123])
      job.terminate()
      kernel.TerminateJobObject.assert_called_once_with(77, 1)
      job.close()
      job.close()
      kernel.CloseHandle.assert_called_once_with(77)

  def test_job_assignment_failure_uses_fallback(self):
    fake = mock.Mock()
    fake.NoSuchProcess = ProcessLookupError
    fake.AccessDenied = PermissionError
    fake.Process.return_value.create_time.return_value = 100
    with mock.patch.object(procs, 'WindowsJob', side_effect=OSError('refused')), \
         mock.patch.object(procs, 'psutil', fake), \
         mock.patch.dict(procs._WINDOWS, {}, clear=True):
      procs.start_windows(mock.Mock(pid=1))
      self.assertIsNone(procs._WINDOWS[1]['job'])
      self.assertEqual(procs._WINDOWS[1]['identities'], {1: 100})
      procs.close_windows(1)

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
