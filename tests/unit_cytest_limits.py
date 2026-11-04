import cytest
import os
import shutil
import signal
import sys
import subprocess
import time
import tempfile
import threading
import unittest
from unittest import mock


class TestChildLimits(unittest.TestCase):
  def hidden(self, *names):
    which = shutil.which
    return mock.patch.object(cytest.shutil, 'which',
        side_effect=lambda name: None if name in names else which(name))

  def test_timeout_without_tool(self):
    # Finite loops bound regression runs against the old helper too.
    code = ('import sys, time; sys.stdout.buffer.write(b"ready\\n"); sys.stdout.flush(); end = time.monotonic() + 4\n'
            'while time.monotonic() < end: pass')
    for text in (True, False):
      start = time.monotonic()
      with self.hidden('timeout', 'gtimeout'):
        proc = cytest.run_in_subprocess(code, 1, text=text)
      self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
      self.assertLess(time.monotonic() - start, 3)
      self.assertEqual(proc.stdout, 'ready\n' if text else b'ready\n')

  @unittest.skipUnless(hasattr(os, 'setsid') and hasattr(os, 'fork'), 'needs POSIX sessions')
  def test_timeout_with_escaped_session(self):
    for text in (True, False):
      with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, 'escaped.pid')
        release = os.path.join(directory, 'release')
        written = os.path.join(directory, 'written')
        code = ('import os, time\n'
                'r, w = os.pipe()\n'
                'if os.fork() == 0:\n'
                '    with open(%r, "w") as stream: stream.write(str(os.getpid()))\n'
                '    os.setsid()\n'
                '    os.write(w, b"r")\n'
                '    while not os.path.exists(%r): time.sleep(0.01)\n'
                '    os.write(1, b"after\\r\\n")\n'
                '    with open(%r, "w"): pass\n'
                '    time.sleep(60)\n'
                'else:\n'
                '    os.read(r, 1)\n'
                '    os.write(1, b"ready\\r\\n")\n'
                '    os.write(2, b"error\\r")\n'
                '    time.sleep(60)\n') % (path, release, written)
        def cleanup():
          try:
            with open(path) as stream:
              os.kill(int(stream.read()), signal.SIGKILL)
          except (FileNotFoundError, ProcessLookupError):
            pass
        killpg = os.killpg
        def kill_and_release(pid, sig):
          killpg(pid, sig)
          # Order the escaped writer after the kill and before the leader reap.
          with open(release, 'w'):
            pass
          deadline = time.monotonic() + 1
          while not os.path.exists(written) and time.monotonic() < deadline:
            time.sleep(0.01)
          self.assertTrue(os.path.exists(written), 'escaped writer did not respond')
        guard = threading.Timer(4, cleanup)
        guard.start()
        start = time.monotonic()
        try:
          with self.hidden('timeout', 'gtimeout'), \
               mock.patch.object(cytest.os, 'killpg', side_effect=kill_and_release):
            proc = cytest.run_in_subprocess(code, 1, text=text)
          self.assertLess(time.monotonic() - start, 3)
          self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
          self.assertEqual(proc.stdout, 'ready\nafter\n' if text else b'ready\r\nafter\r\n')
          self.assertEqual(proc.stderr, 'error\n' if text else b'error\r')
        finally:
          guard.cancel()
          guard.join()
          cleanup()

  def test_timeout_with_inherited_stdout(self):
    with tempfile.TemporaryDirectory() as directory:
      path = os.path.join(directory, 'grandchild.pid')
      grandchild = ('import os, time\n'
                    'with open(%r, "w") as stream: stream.write(str(os.getpid()))\n'
                    'time.sleep(4)\n') % path
      code = ('import os, subprocess, sys, time\n'
              'child = subprocess.Popen([sys.executable, "-c", %r])\n'
              'deadline = time.monotonic() + 0.5\n'
              'while not os.path.exists(%r) and time.monotonic() < deadline: time.sleep(0.01)\n'
              'assert os.path.exists(%r)\n'
              'os.write(1, b"ready\\n")\n'
              'time.sleep(4)\n') % (grandchild, path, path)
      start = time.monotonic()
      try:
        with self.hidden('timeout', 'gtimeout'):
          proc = cytest.run_in_subprocess(code, 1)
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
        self.assertEqual(proc.stdout, 'ready\n')
        self.assertEqual(proc.stderr, '')
      finally:
        try:
          with open(path) as stream:
            pid = int(stream.read())
          if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True, timeout=2)
          else:
            os.kill(pid, signal.SIGKILL)
        except (FileNotFoundError, ProcessLookupError):
          pass

  @unittest.skipUnless(hasattr(os, 'fork'), 'needs fork')
  def test_timeout_kills_grandchild(self):
    code = ('import os, time\npid = os.fork()\n'
            'if pid == 0: time.sleep(4); os._exit(0)\n'
            'print(pid, flush=True)\ntime.sleep(4)\n')
    with self.hidden('timeout', 'gtimeout'):
      proc = cytest.run_in_subprocess(code, 1)
    pid = int(proc.stdout.strip())
    try:
      status = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                              capture_output=True, text=True).stdout.strip()
      dead = not status or status.startswith('Z')
      self.assertTrue(dead, 'grandchild survived timeout')
      self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
    finally:
      try:
        os.kill(pid, signal.SIGKILL)
      except ProcessLookupError:
        pass

  @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux RLIMIT_AS')
  def test_memory_without_prlimit(self):
    with self.hidden('prlimit'):
      small = cytest.run_in_subprocess('x = bytearray(1 << 20); print(len(x))', 2,
                                       address_space=128 << 20)
      large = cytest.run_in_subprocess('x = bytearray(256 << 20)', 2,
                                       address_space=128 << 20)
    self.assertEqual(small.returncode, 0, small.stderr)
    self.assertNotEqual(large.returncode, 0)
    self.assertIn('MemoryError', large.stderr)

  @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux RLIMIT_AS')
  def test_memory_bootstrap_preserves_code(self):
    code = ('from __future__ import annotations\n'
            'import sys; assert sys.argv == ["-c"]; raise RuntimeError("line two")')
    with self.hidden('prlimit'):
      proc = cytest.run_in_subprocess(code, 2, address_space=128 << 20)
      success = cytest.run_in_subprocess(
          'from __future__ import annotations\n'
          'def f(x: Undefined): pass\n'
          'assert f.__annotations__ == {"x": "Undefined"}\n'
          'assert __name__ == "__main__"\n'
          'assert "resource" not in globals()\n'
          'assert "SPRITE_TEST_CHILD_CODE" not in __import__("os").environ\n'
          'assert "SPRITE_TEST_CHILD_LIMIT" not in __import__("os").environ\n'
          'assert __import__("__main__").f is f', 2, address_space=128 << 20)
    self.assertEqual(success.returncode, 0, success.stderr)
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn('File "<string>", line 2, in <module>', proc.stderr)
    self.assertIn('RuntimeError: line two', proc.stderr)

  def test_file_capture_matches_tool(self):
    code = ('import sys; data = sys.stdin.buffer.read(); '
            'sys.stdout.buffer.write(data); sys.stderr.buffer.write(data)')
    for text in (True, False):
      data = 'caf\u00e9\r\nline\rend\n' if text else b'\xff\r\nline\rend\n'
      expected = subprocess.run([sys.executable, '-c', code], input=data,
                                capture_output=True, text=text)
      with self.hidden('timeout', 'gtimeout'):
        actual = cytest.run_in_subprocess(code, 2, input=data, text=text)
      self.assertEqual(actual.returncode, expected.returncode)
      self.assertEqual(actual.stdout, expected.stdout)
      self.assertEqual(actual.stderr, expected.stderr)

  @unittest.skipUnless(sys.platform != 'win32' and
      (shutil.which('timeout') or shutil.which('gtimeout')), 'GNU timeout')
  def test_external_timeout(self):
    proc = cytest.run_in_subprocess('import time; time.sleep(4)', 1)
    self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
    self.assertTrue(any(tool in proc.args for tool in ('timeout', 'gtimeout')))
