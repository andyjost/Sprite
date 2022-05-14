# Adapted from https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/
from contextlib import contextmanager
import ctypes, io, os, sys, tempfile

libc = ctypes.CDLL(None)
c_stdin = ctypes.c_void_p.in_dll(libc, 'stdin')
c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')

@contextmanager
def redirect_stdin(stream):
  original_stdin_fd = sys.stdin.fileno()

  def _redirect_stdin(from_fd):
    libc.fflush(c_stdin)
    sys.stdin.close()
    os.dup2(from_fd, original_stdin_fd)
    sys.stdin = io.TextIOWrapper(os.fdopen(original_stdin_fd, 'rb'))

  saved_stdin_fd = os.dup(original_stdin_fd)
  try:
    tfile = tempfile.TemporaryFile(mode='r+b')
    tfile.write(stream.read())
    tfile.seek(0)
    _redirect_stdin(tfile.fileno())
    yield
    _redirect_stdin(saved_stdin_fd)
    tfile.flush()
  finally:
    tfile.close()
    os.close(saved_stdin_fd)

@contextmanager
def redirect_stdout(stream):
  original_stdout_fd = sys.stdout.fileno()

  def _redirect_stdout(to_fd):
    libc.fflush(c_stdout)
    sys.stdout.close()
    os.dup2(to_fd, original_stdout_fd)
    sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, 'wb'))

  saved_stdout_fd = os.dup(original_stdout_fd)
  try:
    tfile = tempfile.TemporaryFile(mode='w+b')
    _redirect_stdout(tfile.fileno())
    yield
    _redirect_stdout(saved_stdout_fd)
    tfile.flush()
    tfile.seek(0, io.SEEK_SET)
    stream.write(tfile.read())
  finally:
    tfile.close()
    os.close(saved_stdout_fd)

