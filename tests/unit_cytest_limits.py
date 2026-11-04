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
    with tempfile.TemporaryDirectory() as directory:
      path = os.path.join(directory, 'escaped.pid')
      code = ('import os, sys, time\n'
              'if os.fork() == 0:\n'
              '    os.setsid()\n'
              '    with open(%r, "w") as stream: stream.write(str(os.getpid()))\n'
              '    print("ready", flush=True)\n'
              '    print("error", file=sys.stderr, flush=True)\n'
              '    time.sleep(1.3)\n'
              '    print("draining", flush=True)\n'
              '    time.sleep(60)\n'
              'else: time.sleep(60)\n') % path
      def cleanup():
        try:
          with open(path) as stream:
            os.kill(int(stream.read()), signal.SIGKILL)
        except (FileNotFoundError, ProcessLookupError):
          pass
      # Bound this regression even with the old, unbounded drain.
      guard = threading.Timer(6, cleanup)
      guard.start()
      start = time.monotonic()
      try:
        with self.hidden('timeout', 'gtimeout'):
          proc = cytest.run_in_subprocess(code, 1)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1 + cytest.TIMEOUT_DRAIN_SECONDS + 1)
        self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
        self.assertEqual(proc.stdout, 'ready\ndraining\n')
        self.assertEqual(proc.stderr, 'error\n')
      finally:
        guard.cancel()
        guard.join()
        cleanup()

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

  @unittest.skipUnless(sys.platform != 'win32' and
      (shutil.which('timeout') or shutil.which('gtimeout')), 'GNU timeout')
  def test_external_timeout(self):
    proc = cytest.run_in_subprocess('import time; time.sleep(4)', 1)
    self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
    self.assertTrue(any(tool in proc.args for tool in ('timeout', 'gtimeout')))
