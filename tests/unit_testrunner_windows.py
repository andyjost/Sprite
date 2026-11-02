"""Exercise Windows runner branches on every test platform."""
import cytest
from testrunner import cli, prepare, procs, scheduler, selection
from testrunner.manifest import Manifest
import importlib.util
import io
import os
import subprocess
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
    self.assertIn('cleanup terminates the Job Object, or only the leader without a job.', out.getvalue())

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

  def test_windows_traceback_deadline(self):
    with mock.patch.object(sys, 'platform', 'win32'):
      job = cli.test_job('unit_x.py', 'cxx', 'stage', Manifest({}), 600, 'logs', {})
      self.assertIn('windows_unittest(600)', job.argv[3])
      self.assertEqual(job.argv[-4:],
          ['discover', '-v', cli.TESTDIR, 'unit_x.py'])
      job = cli.test_job('unit_primitives_io.py', 'cxx', 'stage', Manifest({}),
                         600, 'logs', {})
      self.assertNotIn('-f', job.argv)
      job = cli.test_job('unit_x.py', 'cxx', 'stage', Manifest({}), None, 'logs', {})
      self.assertIn('windows_unittest(None)', job.argv[3])

  def test_windows_reports_both_tracebacks_before_summary(self):
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'unit_probe.py').write_text(
          'import unittest\n'
          'class TestProbe(unittest.TestCase):\n'
          '  def test_a(self): self.fail("first failure")\n'
          '  def test_b(self): raise ValueError("second error")\n')
      with mock.patch.object(sys, 'platform', 'win32'), \
           mock.patch.object(cli, 'TESTDIR', directory):
        job = cli.test_job('unit_probe.py', 'cxx', 'stage', Manifest({}),
                           None, 'logs', {})
      child = subprocess.run(job.argv, capture_output=True, text=True, timeout=10)
      self.assertEqual(child.returncode, 1, child.stderr)
      before_summary = child.stderr.split('Ran 2 tests')[0]
      self.assertIn('AssertionError: first failure', before_summary)
      self.assertIn('ValueError: second error', before_summary)
      self.assertLess(before_summary.index('AssertionError: first failure'),
                      before_summary.index('test_b ('))
      self.assertEqual(before_summary.count('Traceback (most recent call last):'), 4)
      self.assertIn('FAILED (failures=1, errors=1)', child.stderr)

  def test_traceback_launcher_runs_discovery(self):
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'unit_probe.py').write_text(
          'import time, unittest\n'
          'class TestProbe(unittest.TestCase):\n'
          '  def test_wait(self): time.sleep(1.5)\n')
      with mock.patch.object(sys, 'platform', 'win32'), \
           mock.patch.object(cli, 'TESTDIR', directory):
        job = cli.test_job('unit_probe.py', 'cxx', 'stage', Manifest({}),
                           31, 'logs', {})
      child = subprocess.run(job.argv, capture_output=True, text=True, timeout=10)
      self.assertEqual(child.returncode, 0, child.stderr)
      self.assertIn('Timeout (0:00:01)', child.stderr)
      self.assertIn('test_wait', child.stderr)
      self.assertIn('Ran 1 test', child.stderr)

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
      self.assertEqual(options['creationflags'], 0x204)
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
         mock.patch.dict(procs._WINDOWS, {123: {'job': None, 'leader': job.proc}}, clear=True), \
         mock.patch.object(procs.subprocess, 'run') as run:
      self.assertEqual(procs.meminfo(), {})
      self.assertFalse(procs.is_alive(123))
      scheduler.Watchdog(sched).tick(now=2)
    self.assertIsNone(job.peak)
    self.assertEqual(job.kill_reason, 'timeout')
    run.assert_not_called()
    job.proc.kill.assert_called_once_with()

  def test_no_job_reads_and_kills_only_leader(self):
    leader = mock.Mock(pid=1)
    leader.poll.return_value = None
    fake = mock.Mock()
    fake.NoSuchProcess = ProcessLookupError
    fake.AccessDenied = PermissionError
    fake.Process.return_value.memory_info.return_value.rss = 10
    fake.Process.return_value.name.return_value = 'python.exe'
    state = {'job': None, 'leader': leader}
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.dict(procs._WINDOWS, {1: state}, clear=True), \
         mock.patch.object(procs, 'psutil', fake):
      # Stale iterator entries and recycled parent IDs cannot admit children.
      fake.process_iter.side_effect = AssertionError('process discovery')
      self.assertEqual(procs.scan_sessions([1], roots={1: [2, 3]})[1],
                       (10, [1], {1: 'python'}))
      fake.Process.assert_called_once_with(1)
      fake.Process.side_effect = PermissionError
      self.assertEqual(procs.scan_sessions([1])[1], (None, [1], {1: 'unknown'}))
      self.assertEqual(procs.kill_session(1), [1])
      leader.kill.assert_called_once_with()
      fake.Process.return_value.kill.assert_not_called()
      leader.poll.return_value = 0
      self.assertEqual(procs.scan_sessions([1])[1], (0, [], {}))
      self.assertEqual(procs.kill_session(1), [])

  def test_job_members_and_termination(self):
    job = mock.Mock()
    job.members.return_value = [2]
    fake = mock.Mock()
    fake.NoSuchProcess = ProcessLookupError
    fake.AccessDenied = PermissionError
    fake.Process.return_value.memory_info.return_value.rss = 42
    fake.Process.return_value.name.return_value = 'child.exe'
    state = {'job': job}
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.dict(procs._WINDOWS, {1: state}, clear=True), \
         mock.patch.object(procs, 'psutil', fake):
      self.assertEqual(procs.scan_sessions([1])[1], (42, [2], {2: 'child'}))
      self.assertEqual(procs.kill_session(1, reason='timeout'), [2])
      job.terminate.assert_called_once_with()
      procs.close_windows(1)
      job.close.assert_called_once_with()

  def kernel_stub(self, failure=None):
    import ctypes as c
    from ctypes import wintypes as w
    kernel = mock.Mock()
    handle = 2**40 + 77
    signatures = {
        'CreateJobObjectW': ([w.LPVOID, w.LPCWSTR], w.HANDLE),
        'SetInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, c.c_uint32], c.c_int32),
        'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], c.c_int32),
        'QueryInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, c.c_uint32, w.LPVOID], c.c_int32),
        'TerminateJobObject': ([w.HANDLE, c.c_uint32], c.c_int32),
        'CloseHandle': ([w.HANDLE], c.c_int32)}
    def call(name, args):
      fn = getattr(kernel, name)
      self.assertEqual(fn.argtypes, signatures[name][0])
      self.assertIs(fn.restype, signatures[name][1])
      if name == 'CreateJobObjectW':
        self.assertEqual(c.sizeof(fn.restype), 8)
        return 0 if failure == name else fn.restype(handle).value
      self.assertEqual(args[0], handle)
      if name == 'SetInformationJobObject':
        limits = args[2]._obj
        # Windows SDK winnt.h: JOBOBJECT_BASIC_LIMIT_INFORMATION,
        # IO_COUNTERS and JOBOBJECT_EXTENDED_LIMIT_INFORMATION (x64).
        self.assertEqual(c.sizeof(limits), 144)
        self.assertEqual(c.sizeof(limits.basic), 64)
        self.assertEqual(c.sizeof(limits.io), 48)
        self.assertEqual([getattr(type(limits.io), f).offset for f in
                          ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')],
                         [0, 8, 16, 24, 32, 40])
        for field, offset in [('basic', 0), ('io', 64), ('process_memory', 112),
                              ('job_memory', 120), ('peak_process', 128), ('peak_job', 136)]:
          self.assertEqual(getattr(type(limits), field).offset, offset)
        for field, offset in [('process_time', 0), ('job_time', 8), ('flags', 16),
                              ('minimum', 24), ('maximum', 32), ('active', 40),
                              ('affinity', 48), ('priority', 56), ('scheduling', 60)]:
          self.assertEqual(getattr(type(limits.basic), field).offset, offset)
        self.assertEqual(limits.basic.flags, 0x2000)
        self.assertEqual(args[1], 9)
        self.assertEqual(args[3], 144)
      if name == 'AssignProcessToJobObject':
        self.assertEqual(args[1], 2**40 + 99)
      return name != failure
    for name in signatures:
      getattr(kernel, name).side_effect = lambda *args, name=name: call(name, args)
    return kernel, handle

  def test_kernel_job_calls(self):
    import ctypes as c
    kernel, handle = self.kernel_stub()
    sizes = []
    def query(*args):
      # Check declarations as well as exercising ERROR_MORE_DATA.
      kernel.QueryInformationJobObject.side_effect = None
      self.assertEqual(kernel.QueryInformationJobObject.argtypes,
          [c.c_void_p, c.c_int, c.c_void_p, c.c_uint32, c.c_void_p])
      self.assertIs(kernel.QueryInformationJobObject.restype, c.c_int32)
      kernel.QueryInformationJobObject.side_effect = query
      h, kind, buffer, size, returned = args
      self.assertEqual((h, kind, returned), (handle, 3, None))
      sizes.append(size)
      if len(sizes) == 1:
        return False
      # Windows SDK winnt.h: JOBOBJECT_BASIC_PROCESS_ID_LIST on x64
      # has size 16, DWORD counts at 0 and 4, ULONG_PTR list at 8.
      class IdList(c.Structure):
        _fields_ = [('assigned', c.c_uint32), ('count', c.c_uint32),
                    ('ids', c.c_size_t * 1)]
      self.assertEqual(c.sizeof(IdList), 16)
      self.assertEqual([getattr(IdList, f).offset for f in ('assigned', 'count', 'ids')], [0, 4, 8])
      c.c_uint32.from_buffer(buffer, 0).value = 40
      c.c_uint32.from_buffer(buffer, 4).value = 40
      (c.c_size_t * 40).from_buffer(buffer, 8)[:] = list(range(100, 140))
      return True
    kernel.QueryInformationJobObject.side_effect = query
    with mock.patch.object(c, 'WinDLL', return_value=kernel, create=True), \
         mock.patch.object(c, 'get_last_error', return_value=234, create=True):
      job = procs.WindowsJob(types.SimpleNamespace(_handle=2**40 + 99))
      self.assertEqual(job.members(), list(range(100, 140)))
      self.assertEqual(sizes, [256, 512])
      job.terminate()
      job.close()
      job.close()
      kernel.CloseHandle.assert_called_once_with(handle)

  def test_constructor_failures_close_once(self):
    import ctypes as c
    for failure in ('CreateJobObjectW', 'SetInformationJobObject', 'AssignProcessToJobObject'):
      with self.subTest(failure=failure):
        kernel, handle = self.kernel_stub(failure)
        with mock.patch.object(c, 'WinDLL', return_value=kernel, create=True), \
             mock.patch.object(c, 'get_last_error', return_value=5, create=True), \
             mock.patch.object(c, 'WinError', side_effect=lambda code: OSError(code, 'refused'), create=True):
          with self.assertRaises(OSError):
            procs.WindowsJob(types.SimpleNamespace(_handle=2**40 + 99))
        if failure == 'CreateJobObjectW':
          kernel.CloseHandle.assert_not_called()
        else:
          kernel.CloseHandle.assert_called_once_with(handle)
        if failure != 'AssignProcessToJobObject':
          kernel.AssignProcessToJobObject.assert_not_called()

  def test_suspended_assign_resume_and_refusal(self):
    import ctypes as c
    for refused in (False, True):
      for with_psutil in (False, True):
        with self.subTest(refused=refused, psutil=with_psutil):
          kernel, handle = self.kernel_stub('AssignProcessToJobObject' if refused else None)
          events = []
          assign = kernel.AssignProcessToJobObject.side_effect
          def assignment(*args):
            events.append('assign')
            return assign(*args)
          kernel.AssignProcessToJobObject.side_effect = assignment
          child = mock.Mock(pid=1, _handle=2**40 + 99)
          child.poll.return_value = None
          fake = mock.Mock()
          fake.Process.return_value.resume.side_effect = lambda: events.append('resume')
          ntdll = mock.Mock()
          ntdll.NtResumeProcess.side_effect = lambda h: events.append('resume') or 0
          def launch(*args, **kwargs):
            self.assertTrue(kwargs['creationflags'] & 0x4)
            events.append('suspend')
            return child
          def dll(name, **kwargs):
            return kernel if name == 'kernel32' else ntdll
          with mock.patch.object(sys, 'platform', 'win32'), \
               mock.patch.object(c, 'WinDLL', side_effect=dll, create=True), \
               mock.patch.object(c, 'get_last_error', return_value=5, create=True), \
               mock.patch.object(c, 'WinError', side_effect=lambda code: OSError(code, 'refused'), create=True), \
               mock.patch.object(procs, 'psutil', fake if with_psutil else None), \
               mock.patch.object(scheduler.subprocess, 'Popen', side_effect=launch), \
               mock.patch.dict(procs._WINDOWS, {}, clear=True), \
               mock.patch.object(sys, 'stdout', io.StringIO()) as output:
            job = scheduler.Job('x', 'cxx', ['python'], 1024, 10, None)
            scheduler.Scheduler([], 2048, 1).start(job)
            self.assertEqual(events, ['suspend', 'assign', 'resume'])
            if not with_psutil:
              from ctypes import wintypes as w
              self.assertEqual(ntdll.NtResumeProcess.argtypes, [w.HANDLE])
              self.assertIs(ntdll.NtResumeProcess.restype, c.c_int32)
              ntdll.NtResumeProcess.assert_called_once_with(2**40 + 99)
            if refused:
              self.assertEqual(output.getvalue().count('descendants are not tracked'), 1)
              self.assertEqual(procs.kill_session(1), [1])
              child.kill.assert_called_once_with()
              fake.Process.return_value.kill.assert_not_called()
            procs.close_windows(1)
            kernel.CloseHandle.assert_called_once_with(handle)

  def test_failed_resume_reaps_suspended_leader(self):
    if procs.psutil is not None:
      AccessDenied = procs.psutil.AccessDenied
    else:
      class AccessDenied(Exception):
        pass
    for refused in (False, True):
      with self.subTest(refused=refused):
        child = mock.Mock(pid=1)
        fake = mock.Mock()
        error = AccessDenied()
        fake.Process.return_value.resume.side_effect = error
        job = mock.Mock()
        with mock.patch.object(procs, 'WindowsJob',
                               side_effect=OSError('refused') if refused else None,
                               return_value=job), \
             mock.patch.object(procs, 'psutil', fake), \
             mock.patch.object(sys, 'stdout', io.StringIO()), \
             mock.patch.dict(procs._WINDOWS, {}, clear=True):
          with self.assertRaises(OSError) as raised:
            procs.start_windows(child)
          self.assertIs(raised.exception.__cause__, error)
          child.kill.assert_called_once_with()
          child.wait.assert_called_once_with(timeout=10)
          fake.Process.return_value.kill.assert_not_called()
          if not refused:
            job.close.assert_called_once_with()
          self.assertNotIn(1, procs._WINDOWS)

  def test_failed_resume_and_cleanup_errors_are_bounded_and_reported(self):
    for has_job, job_errors in ((False, False), (True, False), (True, True)):
      with self.subTest(has_job=has_job, job_errors=job_errors):
        child = mock.Mock(pid=1)
        job = mock.Mock()
        calls = mock.Mock()
        calls.attach_mock(job, 'job')
        calls.attach_mock(child, 'child')
        child.kill.side_effect = OSError('kill refused')
        child.wait.side_effect = subprocess.TimeoutExpired('leader', 10)
        if job_errors:
          job.terminate.side_effect = OSError('terminate refused')
          job.close.side_effect = OSError('close refused')
        fake = mock.Mock()
        resume_error = RuntimeError('resume refused')
        fake.Process.return_value.resume.side_effect = resume_error
        with mock.patch.object(procs, 'WindowsJob', return_value=job,
                               side_effect=None if has_job else OSError('no job')), \
             mock.patch.object(procs, 'psutil', fake), \
             mock.patch.object(sys, 'stdout', io.StringIO()), \
             mock.patch.dict(procs._WINDOWS, {}, clear=True):
          with self.assertRaises(OSError) as raised:
            procs.start_windows(child)
          self.assertIs(raised.exception.__cause__, resume_error)
          expected = [mock.call.child.kill(), mock.call.child.wait(timeout=10)]
          if has_job:
            expected = [mock.call.job.terminate(), mock.call.job.close()] + expected
          if job_errors:
            self.assertIn('terminate refused', str(raised.exception))
            self.assertIn('close refused', str(raised.exception))
          self.assertEqual(calls.mock_calls, expected)
          self.assertIn('kill refused', str(raised.exception))
          self.assertIn('TimeoutExpired', str(raised.exception))
          self.assertNotIn(1, procs._WINDOWS)

  def test_failed_warning_write_still_resumes_leader(self):
    child = mock.Mock(pid=1)
    fake = mock.Mock()
    output = mock.Mock()
    output.write.side_effect = BrokenPipeError('closed')
    with mock.patch.object(procs, 'WindowsJob', side_effect=OSError('refused')), \
         mock.patch.object(procs, 'psutil', fake), \
         mock.patch.object(sys, 'stdout', output), \
         mock.patch.dict(procs._WINDOWS, {}, clear=True):
      procs.start_windows(child)
      output.write.assert_called()
      fake.Process.return_value.resume.assert_called_once_with()
      self.assertIs(procs._WINDOWS[1]['leader'], child)
      child.kill.assert_not_called()
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
