import cytest
import os
import shutil
import signal
import sys
import subprocess
import time
import unittest
from unittest import mock


class TestChildLimits(unittest.TestCase):
  def hidden(self, *names):
    which = shutil.which
    return mock.patch.object(cytest.shutil, 'which',
        side_effect=lambda name: None if name in names else which(name))

  def test_timeout_without_tool(self):
    # Finite loops bound regression runs against the old helper too.
    code = ('import time; print("ready", flush=True); end = time.monotonic() + 4\n'
            'while time.monotonic() < end: pass')
    for text in (True, False):
      start = time.monotonic()
      with self.hidden('timeout', 'gtimeout'):
        proc = cytest.run_in_subprocess(code, 1, text=text)
      self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
      self.assertLess(time.monotonic() - start, 3)
      self.assertEqual(proc.stdout, 'ready\n' if text else b'ready\n')

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

  @unittest.skipUnless(sys.platform != 'win32' and
      (shutil.which('timeout') or shutil.which('gtimeout')), 'GNU timeout')
  def test_external_timeout(self):
    proc = cytest.run_in_subprocess('import time; time.sleep(4)', 1)
    self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS)
    self.assertTrue(any(tool in proc.args for tool in ('timeout', 'gtimeout')))
