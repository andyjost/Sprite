'''Python bindings for libcurryrt, the C++ runtime library.'''
import os as _os, sys as _sys
if _sys.platform == 'win32':
  # An extension finds its DLLs in the directories the process declares, not
  # on PATH (Python 3.8); the runtime library is lib/ of the installation.
  from .... import config as _config
  _os.add_dll_directory(_config.installed_path('lib'))
from ._curryrtbindings import *
from .... import config as _config
set_install_prefix(_config.prefix())

_register_primitive = register_primitive

def _primitive_value(value, typeexpr, result=False, interp=None):
  from ....toolchain.flat2icurry import flatcurry as fc
  if not isinstance(typeexpr, fc.TCons):
    raise TypeError('primitive requires a concrete declared type')
  name = typeexpr.name
  args = typeexpr.args
  if name == fc.prelude('IO'):
    return _primitive_value(value, args[0], result, interp)
  if name == fc.prelude('String') or (name == fc.prelude('[]') and args[0] == fc.TCons(fc.prelude('Char'), [])):
    if not result and value == []: return ''
    valid = isinstance(value, str)
  elif name == fc.prelude('[]'):
    if not isinstance(value, list):
      raise TypeError('primitive value does not match declared list type')
    return [_primitive_value(x, args[0], result, interp) for x in value]
  elif name == fc.prelude('(,)'):
    if not isinstance(value, tuple) or len(value) != 2:
      raise TypeError('primitive value does not match declared pair type')
    return tuple(_primitive_value(x, t, result, interp) for x, t in zip(value, args))
  elif name == fc.prelude('()'): valid = value is None
  elif name == fc.prelude('Int'): valid = type(value) is int
  elif name == fc.prelude('Float'): valid = type(value) is float
  elif name == fc.prelude('Bool'): valid = type(value) is bool
  elif name == fc.prelude('Char'): valid = isinstance(value, str) and len(value) == 1
  else: raise TypeError('unsupported primitive declared type: ' + '.'.join(name))
  if not valid:
    raise TypeError('primitive value does not match declared type ' + name[1])
  if name == fc.prelude('Char') and result:
    from ....objects.terms import Char, term
    return term(interp, Char(value))._node
  return value

def register_primitive(name, arity, callable, monadic=False):
  if not _builtins.callable(callable):
    raise TypeError('expected a callable')
  def typed(interp, *values):
    from ....toolchain.flat2icurry import flatcurry as fc
    scheme = interp.sigtable.lookup(name, required=True)
    typeexpr = scheme.typeexpr
    arguments = []
    for value in values:
      if not isinstance(typeexpr, fc.FuncType):
        raise TypeError('primitive arity does not match declared type')
      arguments.append(_primitive_value(value, typeexpr.domain, interp=interp))
      typeexpr = typeexpr.range
    return _primitive_value(callable(*arguments), typeexpr, result=True, interp=interp)
  _register_primitive(name, arity, typed, monadic)

import builtins as _builtins

def _register_environment_primitives():
  import socket
  import curry
  register_primitive('System.Environment.getArgs', 0, lambda: curry.program_arguments, True)
  register_primitive('System.Environment.getProgName', 0,
      lambda: curry.program_name, True)
  register_primitive('System.Environment.getHostname', 0, socket.gethostname, True)

_register_environment_primitives()
from ...generic.eval import control
from ....interpreter import flags as _flags
from . import fingerprint
from ... import InfoTable as _backends_InfoTable
from ... import Node as _backends_Node
import logging, sys

logger = logging.getLogger(__name__)
_backends_Node.register(Node)
_backends_InfoTable.register(InfoTable)

def make_node(info, *args, **kwds):
  info = getattr(info, 'info', info)
  partial_info = kwds.pop('partial_info', None)
  target = kwds.pop('target', None)
  target = getattr(target, 'target', target)
  from ....common import F_INT_TYPE
  if info.flags & 0xf == F_INT_TYPE and args and isinstance(args[0], int):
    if not -2 ** 63 <= args[0] < 2 ** 63:
      from ....utility.strings import int_text
      node = make_integer(int_text(args[0]))
      if target is not None:
        target.forward_to(node)
        return target
      return node
  args = [Arg(arg) for arg in args]
  return Node.create(info, args, target, bool(partial_info))

class StepCounter(object):
  '''
  The step counter of the generic evaluator over a C++ runtime state.

  Evaluator.set_global_step_limit reads ``rts.stepcounter``.
  This view uses the native ``steps_total`` and ``step_limit`` fields.
  The count and limit are relative to the last reset (``_step_base``),
  while the state totals keep every step.  A limit at or below the count
  raises E_TERMINATE at once; otherwise generate_values raises it after
  the scheduler completes the step that reaches the limit.

  A view: ``rts.stepcounter`` makes one per access, and the state holds no
  counter.  A counter kept by the state made a reference cycle, which
  delayed the destruction of the state of evaluator.single_step until the
  cyclic collector ran; a live state is a root of the collector, so the
  history of a search stayed reachable (test_repl_eval_under_stress of
  unit_goals.py grew with the square of its length).
  '''
  def __init__(self, rts):
    self._rts = rts

  @property
  def global_count(self):
    '''The steps taken since the last reset.'''
    return self._rts.steps_total - self._rts._step_base

  @property
  def global_limit(self):
    limit = self._rts.step_limit
    return float('inf') if limit == NOLIMIT else limit - self._rts._step_base

  @global_limit.setter
  def global_limit(self, limit):
    if limit is None:
      self._rts.step_limit = NOLIMIT
      return
    limit = int(limit)
    if self.global_count >= limit:
      raise control.E_TERMINATE()
    self._rts.step_limit = self._rts._step_base + limit

  def reset_global(self):
    self._rts._step_base = self._rts.steps_total


# A directly constructed base state has no owning Python interpreter.
RuntimeStateBase.interp = property(
    lambda self: getattr(self, '_interp', None),
    lambda self, interp: setattr(self, '_interp', interp))


class RuntimeState(RuntimeStateBase):
  def __init__(self, interp, goal=None):
    self.interp = interp
    istate = interp.backend.get_interpreter_state(interp)
    self.tracing = interp.flags['trace']
    limit = interp.flags['stack_limit']
    self.stack_limit = NOLIMIT if limit is None else int(limit)
    # The rotation cadence (see curryrt/ticker.hpp): zero steps select time
    # mode with the quantum in nanoseconds.
    mode, value = _flags.parse_rotation(interp.flags['rotation'])
    self.rotation_steps = value if mode == 'steps' else 0
    self.rotation_quantum_ns = value if mode == 'time' else 0
    # The checker of the run-time invariants of the Fair Scheme (the flag
    # ``checker``; curryrt/checker.hpp).
    self.checker = bool(interp.flags['checker'])
    RuntimeStateBase.__init__(
        self, istate, goal, self.tracing, self.stack_limit
      , self.rotation_steps, self.rotation_quantum_ns, self.checker
      , 0 if interp.flags['worker_stack'] is None else int(interp.flags['worker_stack'])
      )
    # The count of the stepper starts here (StepCounter.reset_global).
    self._step_base = 0
    self._counts = [0, 0, None]

  @property
  def stepcounter(self):
    '''The step counter of the generic evaluator: a view of this state.'''
    return StepCounter(self)

  def single_step(self, node):
    '''
    One rewrite step at the root of ``node`` (see evaluator.single_step).
    A step that reports an error raises it as the evaluation would.
    '''
    RuntimeStateBase.single_step(self, node)

  def generate_events(self):
    '''Yield (is_output, node), keeping the continuation between pulls.'''
    counts, next_event = self._counts, self._next_event_counted
    try:
      while True:
        _flush_stdout()
        result = next_event(counts)
        if result is None:
          return
        yield result
    except StepLimitReached:
      raise control.E_TERMINATE()

  def generate_values(self):
    '''
    Generates the values of the goal.

    Curry character IO uses the current Python standard streams through
    the host hook below. Flushing before the scheduler also orders buffered
    Python output before native child-process output.

    The step limit of the stepper (``stepcounter``) ends the evaluation with
    E_TERMINATE, the flow-control exception of the generic evaluator.
    '''
    from ....interpreter.eval import _print_yield
    for output, result in self.generate_events():
      if output:
        _print_yield(self.interp, result)
      else:
        yield result

def _flush_stdout():
  # A closed or missing stdout is legal: some IO tests close it to provoke an
  # error from the program.
  try:
    sys.stdout.flush()
  except (AttributeError, OSError, ValueError):
    pass


# One character of lookahead per hosted stream. Replacing a standard
# stream drops its old lookahead. File handles use native binary UTF-8 streams.
from collections import defaultdict as _defaultdict
_stream_lookahead = _defaultdict(lambda: None)
_stream_recovered = _defaultdict(lambda: None)
_command_streams = {}
_command_processes = set()
_command_owners = {}
import threading as _threading
_command_lock = _threading.RLock()
_command_pending = set()
_command_origin = _os.getpid()


def _command_call(process, operation, *args, **kwargs):
  owner = vars(process).get('_command_creator_pid', _command_origin)
  builtin_only = sys.platform != 'win32' and '_command_creator_pid' in vars(process)
  if builtin_only:
    # Only these bounded syscalls run with signals masked, never Python IO.
    if operation is _os.killpg:
      _curryrtbindings._command_posix_call(owner, 0, *args)
      return
    if operation is _os.waitpid:
      pid, flags = args
      assert flags == _os.WNOHANG
      return _curryrtbindings._command_posix_call(owner, 1, pid, 0)
    if operation is getattr(_os, 'waitid', None):
      kind, pid, flags = args
      assert kind == _os.P_PID and flags == _os.WEXITED | _os.WNOWAIT | _os.WNOHANG
      _, exited = _curryrtbindings._command_posix_call(owner, 2, pid, 0)
      return True if exited else None
  return _curryrtbindings._command_call(owner, builtin_only, operation, *args, **kwargs)


def _wait_command(process, timeout=0):
  # Windows cannot fork. Non-command process adapters retain their wait API.
  if sys.platform == 'win32' or '_command_creator_pid' not in vars(process):
    return _command_call(process, process.wait, timeout=timeout)
  import subprocess
  import time
  deadline = time.monotonic() + timeout
  while True:
    # Share Popen's waiter serialization without blocking past the deadline,
    # acquiring it after the fork check and before masking signals.
    _curryrtbindings._fork_check()
    if process._waitpid_lock.acquire(False):
      try:
        if process.returncode is not None:
          return process.returncode
        try:
          pid, status = _command_call(process, _os.waitpid, process.pid, _os.WNOHANG)
        except ChildProcessError:
          process.returncode = 0
          return 0
        if pid:
          process.returncode = _os.waitstatus_to_exitcode(status)
          return process.returncode
      finally:
        process._waitpid_lock.release()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
      raise subprocess.TimeoutExpired(process.args, timeout)
    time.sleep(min(.01, remaining))


def _close_command_stream(process, stream, discard=False):
  if process is None: process = stream
  if isinstance(stream, _CommandStream):
    try:
      _close_command_stream(process, stream.writer, discard)
    finally:
      _close_command_stream(process, stream.reader, discard)
    return
  if discard:
    # Close FileIO first: discard buffered input without waiting for a command
    # that has stopped consuming it, even if group termination failed.
    raw = getattr(getattr(stream, 'buffer', None), 'raw', None)
    if raw is not None:
      _command_call(process, raw.close)
  try:
    _command_call(process, stream.close)
  except (OSError, ValueError):
    if not discard: raise


def _reset_commands_after_fork():
  global _command_lock, _command_streams, _command_pending
  global _command_processes, _command_owners, _stream_lookahead, _stream_recovered
  # Do not flush, close or destroy inherited streams or process owners.
  _curryrtbindings._fork_abandon((_command_lock, _command_streams,
      _command_pending, _command_processes, _command_owners,
      _stream_lookahead, _stream_recovered))
  _command_lock = _threading.RLock()
  _command_streams, _command_owners = {}, {}
  _command_pending, _command_processes = set(), set()
  _stream_lookahead = _defaultdict(lambda: None)
  _stream_recovered = _defaultdict(lambda: None)


if hasattr(_os, 'register_at_fork'):
  _os.register_at_fork(after_in_child=_reset_commands_after_fork)


def _command_exited(process, timeout=0):
  """Observe exit without releasing the leader's process/group id."""
  import errno
  import time
  if process.returncode is not None:
    return True
  if sys.platform != 'win32' and all(hasattr(_os, name) for name in
                                    ('waitid', 'WNOWAIT', 'WEXITED', 'WNOHANG', 'P_PID')):
    deadline = time.monotonic() + timeout
    while True:
      try:
        result = _command_call(process, _os.waitid, _os.P_PID, process.pid,
                               _os.WEXITED | _os.WNOWAIT | _os.WNOHANG)
      except ChildProcessError:
        # Another waiter already reaped it: record that before any signal.
        process._command_reaped = True
        # Give its status publication at least one second, even for a poll.
        import subprocess
        try:
          _wait_command(process, timeout=max(1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
          return False
        return process.returncode is not None
      except OSError as error:
        if error.errno not in (errno.EINVAL, errno.ENOSYS, errno.ENOTSUP):
          raise
        break
      if result is not None:
        return True
      remaining = deadline - time.monotonic()
      if remaining <= 0:
        return False
      time.sleep(min(.01, remaining))
  # Some systems (including older macOS) lack waitid/WNOWAIT support.
  # Signals must precede this reaping wait; skip the final group kill after it.
  if not timeout:
    if sys.platform == 'win32' or '_command_creator_pid' not in vars(process):
      return _command_call(process, process.poll) is not None
    import subprocess
    try:
      _wait_command(process)
      return True
    except subprocess.TimeoutExpired:
      return False
  import subprocess
  try:
    _wait_command(process, timeout=timeout)
    return True
  except subprocess.TimeoutExpired:
    return False


from ....utility.procfork import work as _fork_work


@_fork_work
def _reap_commands():
  # No worker: a child exiting while idle is reaped at the next launch,
  # handle close or shutdown. Poll never waits for a running child.
  with _command_lock:
    for process in list(_command_pending):
      _curryrtbindings._fork_check()
      try:
        if _command_exited(process):
          _signal_command(process, kill=True)
          _wait_command(process, timeout=1)
          if sys.platform == 'win32':
            process._command_job.close()
            process._handle.Close()
          _command_pending.discard(process)
          _command_processes.discard(process)
      except Exception:
        _curryrtbindings._fork_check()
        # Keep this child pending without preventing cleanup of the others.
        logger.exception('Command %s retirement failed; will retry', process.pid)


def _retire_command(token):
  with _command_lock:
    process = _command_owners.pop(token, None)
    if process in _command_processes and process not in _command_owners.values():
      _command_pending.add(process)
  _reap_commands()

_next_command_stream = 3

def _read_standard_char(stream, index):
  from collections import deque
  recovered = _stream_recovered[index]
  if recovered is not None and recovered[0] is stream and (recovered[1] or recovered[2]):
    char = recovered[1].popleft() if recovered[1] else ''
  else:
    _stream_recovered[index] = None
    try:
      char = stream.read(1)
    except UnicodeDecodeError as error:
      # A strict TextIOWrapper has consumed this byte chunk but produced no
      # characters. Retain its replacement-decoded content without changing
      # the caller's stream encoding or error policy.
      chars = deque(error.object.decode(error.encoding, 'replace'))
      char = chars.popleft() if chars else ''
      # An incomplete sequence is diagnosed only when the decoder sees
      # EOF. Do not ask it to finalize that same pending prefix again.
      eof = error.reason in ('unexpected end of data', 'truncated data',
                             'incomplete multibyte sequence')
      _stream_recovered[index] = (stream, chars, eof)
  # Curry characters are Unicode scalar values. Python's surrogateescape
  # represents malformed input bytes with surrogates, which become U+FFFD.
  return '\ufffd' if char and 0xd800 <= ord(char) <= 0xdfff else char

def _windows_nonblocking_pipe(descriptor):
  # Python 3.11 lacks the Windows os.get_blocking/set_blocking interface.
  import ctypes
  import msvcrt
  kernel = ctypes.windll.kernel32
  handle = ctypes.c_void_p(msvcrt.get_osfhandle(descriptor))
  mode = ctypes.c_ulong()
  if not kernel.GetNamedPipeHandleStateW(handle, ctypes.byref(mode),
                                        None, None, None, None, 0):
    return None
  nonblocking = ctypes.c_ulong(mode.value | 1)  # PIPE_NOWAIT
  if not kernel.SetNamedPipeHandleState(handle, ctypes.byref(nonblocking), None, None):
    raise ctypes.WinError(kernel.GetLastError())
  def restore():
    if not kernel.SetNamedPipeHandleState(handle, ctypes.byref(mode), None, None):
      raise ctypes.WinError(kernel.GetLastError())
  return restore


def _peek_standard_char(stream, index, nonblocking=False):
  pending = _stream_lookahead[index]
  if pending is not None and pending[0] is stream:
    return pending
  try:
    position = stream.tell()
  except (OSError, ValueError, AttributeError):
    position = None
  restore = None
  descriptor = None
  raw = None
  readinto = None
  if nonblocking:
    try:
      descriptor = stream.fileno()
      blocking = _os.get_blocking(descriptor)
      _os.set_blocking(descriptor, False)
      restore = lambda: _os.set_blocking(descriptor, blocking)
    except AttributeError:
      if descriptor is None or sys.platform != 'win32': return None
      restore = _windows_nonblocking_pipe(descriptor)
      if restore is None: return None
    except (OSError, ValueError):
      return None
  original_readinto = None
  patched = False
  try:
    if nonblocking:
      # BufferedReader.read1 maps a raw None (would block) to b'', which a
      # TextIOWrapper's incremental decoder treats as final EOF. Preserve the
      # distinction at the byte boundary, leaving partial bytes in that decoder
      # until another read supplies the rest. Already decoded text stays visible.
      raw = getattr(getattr(stream, 'buffer', None), 'raw', None)
      if raw is not None:
        readinto = raw.readinto
        original_readinto = vars(raw).get('readinto')
        def read_available(buffer):
          count = readinto(buffer)
          if count is None:
            raise BlockingIOError('no input available')
          return count
        raw.readinto = read_available
        patched = True
    char = _read_standard_char(stream, index)
    # An empty nonblocking read need not mean EOF. The descriptor probe
    # below distinguishes no input from EOF without caching this result.
    if nonblocking and not char:
      return None
    pending = (stream, char, position)
    _stream_lookahead[index] = pending
    return pending
  except (BlockingIOError, TypeError):
    if not nonblocking:
      raise
    return None
  except OSError as error:
    # Older Windows raw readers report an empty nonblocking pipe this way.
    if nonblocking and getattr(error, 'winerror', None) == 232:
      return None
    raise
  finally:
    if patched:
      if original_readinto is None:
        del raw.readinto
      else:
        raw.readinto = original_readinto
    if restore is not None:
      restore()


class _CommandStream:
  """A command's output reader and input writer exposed as one handle."""
  def __init__(self, reader, writer, owner):
    self.reader, self.writer = reader, writer
    self._command_creator_pid = owner

  def __getattr__(self, name):
    return getattr(self.reader, name)

  def writable(self):
    return self.writer.writable()

  def write(self, text):
    return _command_call(self, self.writer.write, text)

  def flush(self):
    _command_call(self, self.writer.flush)

  def close(self):
    _close_command_stream(self, self)


@_fork_work
def _standard_stream(index, operation, text, value):
  import io
  import select
  import time
  global _next_command_stream
  if operation in ('exec', 'connect'):
    import subprocess
    _reap_commands()
    if sys.platform == 'win32':
      from ....utility.windowsjob import WindowsJob
    process = None
    owner = _os.getpid()
    try:
      process = subprocess.Popen(text, shell=True, stdin=subprocess.PIPE,
          stdout=subprocess.PIPE, stderr=subprocess.PIPE if operation == 'exec' else None, text=True,
          encoding='utf-8', errors='replace', bufsize=1,
          start_new_session=sys.platform != 'win32',
          creationflags=0x4 if sys.platform == 'win32' else 0)
      process._command_creator_pid = owner
      if sys.platform == 'win32':
        process._command_job = WindowsJob(process)
        # Popen closes the suspended primary thread's handle.
        import ctypes
        from ctypes import wintypes
        resume = ctypes.WinDLL('ntdll').NtResumeProcess
        resume.argtypes, resume.restype = [wintypes.HANDLE], ctypes.c_int32
        if resume(int(process._handle)) < 0:
          raise OSError('cannot resume command')
      with _command_lock:
        _command_processes.add(process)
    except BaseException:
      if process is None: raise
      # Each cleanup must run even if another cleanup fails or is interrupted.
      job = getattr(process, '_command_job', None)
      cleanups = ([job.close] if job is not None else [])
      cleanups += [process.kill if sys.platform == 'win32' else
                   lambda: _signal_command(process, kill=True),
                   lambda: _wait_command(process, timeout=1)]
      cleanups += [lambda stream=stream: _close_command_stream(process, stream) for stream in
                   (process.stdin, process.stdout, process.stderr) if stream is not None]
      if sys.platform == 'win32':
        cleanups.append(process._handle.Close)
      for cleanup in cleanups:
        try: cleanup()
        except BaseException:
          _curryrtbindings._fork_check()
      with _command_lock:
        _command_processes.discard(process)
      raise
    ids = []
    streams = ((process.stdin, process.stdout, process.stderr) if operation == 'exec'
               else (_CommandStream(process.stdout, process.stdin, owner),))
    for stream in streams:
      stream._command_creator_pid = owner
      token = _next_command_stream
      _next_command_stream += 1
      _command_streams[token] = stream
      _command_owners[token] = process
      ids.append(str(token))
    return ' '.join(ids)
  streams = {0: sys.stdin, 1: sys.stdout, 2: sys.stderr, **_command_streams}
  process = _command_owners.get(index)
  if operation in ('release', 'prim_hClose') and index >= 3:
    stream = _command_streams.pop(index, None)
    try:
      if stream is not None: _close_command_stream(process, stream)
    finally:
      _stream_lookahead.pop(index, None)
      _stream_recovered.pop(index, None)
      _retire_command(index)
    return ''
  stream = streams[index]
  if operation == 'waits':
    indices = list(map(int, text.split(','))) if text else []
    selected = [streams[i] for i in indices]
    if not selected:
      if value > 0: time.sleep(value / 1000)
      return '-1'
    for i, item in enumerate(selected):
      pending = _stream_lookahead[indices[i]]
      recovered = _stream_recovered[indices[i]]
      if item.closed: raise ValueError('stream does not exist (closed handle)')
      if not item.readable(): raise ValueError('stream is not readable')
      if pending is not None and pending[0] is item: return str(i)
      if recovered is not None and recovered[0] is item and recovered[1]: return str(i)
      if isinstance(item, io.StringIO): return str(i)
      # A text wrapper may already hold decoded input although its descriptor
      # is empty. Probe the same reader without blocking, retaining the char.
      if _peek_standard_char(item, indices[i], nonblocking=True) is not None:
        return str(i)
      import stat
      if stat.S_ISREG(_os.fstat(item.fileno()).st_mode): return str(i)
    if sys.platform == 'win32':
      # select on Windows supports sockets only; console and pipes use msvcrt
      # and PeekNamedPipe, through Python's platform libraries.
      import ctypes
      import msvcrt
      deadline = None if value < 0 else time.monotonic() + value / 1000
      while True:
        for i, item in enumerate(selected):
          if item.isatty():
            if msvcrt.kbhit(): return str(i)
          else:
            available = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.PeekNamedPipe(
                ctypes.c_void_p(msvcrt.get_osfhandle(item.fileno())),
                None, 0, None, ctypes.byref(available), None)
            if ok and available.value: return str(i)
            if not ok:
              error = ctypes.windll.kernel32.GetLastError()
              if error == 109: return str(i)
              raise ctypes.WinError(error)
        if deadline is not None and time.monotonic() >= deadline: return '-1'
        time.sleep(.001)
    ready, _, _ = select.select(selected, [], [], None if value < 0 else value / 1000)
    return str(next((i for i, item in enumerate(selected) if item in ready), -1))
  if operation == 'prim_hClose':
    _reap_commands()
    if not stream.closed: stream.close()
    _stream_lookahead[index] = None
    _stream_recovered[index] = None
    return ''
  if stream.closed: raise ValueError('stream does not exist (closed handle)')
  pending = _stream_lookahead[index]
  if pending is not None and pending[0] is not stream:
    _stream_lookahead[index] = pending = None
  if operation in ('prim_hPutChar', 'prim_hFlush') and index >= 3:
    writer = stream.writer if isinstance(stream, _CommandStream) else stream
    if process is None: process = stream
    if operation == 'prim_hPutChar': _command_call(process, writer.write, text)
    else: _command_call(process, writer.flush)
  elif operation == 'prim_hPutChar': stream.write(text)
  elif operation == 'prim_hFlush': stream.flush()
  elif operation == 'prim_hIsReadable': return '1' if stream.readable() else '0'
  elif operation == 'prim_hIsWritable': return '1' if stream.writable() else '0'
  elif operation == 'prim_hIsTerminalDevice': return '1' if stream.isatty() else '0'
  elif operation == 'prim_hWaitForInput':
    return '1' if _standard_stream(index, 'waits', str(index), value) == '0' else '0'
  elif operation == 'prim_hIsEOF':
    if pending is None:
      pending = _peek_standard_char(stream, index)
    return '1' if pending[1] == '' else '0'
  elif operation == 'prim_hGetChar':
    if pending is not None:
      _stream_lookahead[index] = None
      return pending[1]
    return _read_standard_char(stream, index)
  elif operation == 'prim_hSeek':
    def seek(*args):
      if index < 3: return stream.seek(*args)
      reader = stream.reader if isinstance(stream, _CommandStream) else stream
      return _command_call(process if process is not None else stream, reader.seek, *args)
    if int(text) == 1 and pending is not None and pending[2] is not None:
      # Text positions are opaque cookies, not byte or character counts.
      seek(pending[2])
    seek(value, int(text))
    _stream_lookahead[index] = None
    _stream_recovered[index] = None
  else: raise ValueError('unknown standard stream operation: ' + operation)
  return ''

set_stream_hook(_standard_stream)
import atexit as _atexit
def _signal_command(process, kill=False):
  if sys.platform == 'win32':
    process._command_job.terminate()
  else:
    # Sprite owns this group only until its leader is reaped. Descendants
    # leaving the group/session themselves are outside command containment.
    if process.returncode is not None or vars(process).get('_command_reaped', False):
      return
    import signal
    try:
      _command_call(process, _os.killpg, process.pid, signal.SIGKILL if kill else signal.SIGTERM)
    except ProcessLookupError:
      pass
    except PermissionError:
      # XNU reports EPERM for a group containing only zombies. Confirm the
      # leader's exit without reaping it before allowing retirement. A live
      # descendant with different credentials can also cause EPERM, so keep
      # that uncertainty visible even though the dead leader can be reaped.
      if not _command_exited(process):
        raise
      logger.warning('Cannot signal command group %s: leader exited; '
                     'live descendants may remain', process.pid, exc_info=True)


def _shutdown_native():
  if _curryrtbindings._fork_poisoned():
    return
  try:
    _shutdown_commands()
  except Exception:
    if not _curryrtbindings._fork_poisoned(): raise


@_fork_work
def _shutdown_commands():
  # The hot tier registers later, so it quiesces before this drain. The heap
  # and its root registries remain alive for late Python finalizers.
  with _command_lock:
    processes = list(_command_processes)
  # Never hold the registry lock while waiting, and never start a thread.
  for process in processes:
    _curryrtbindings._fork_check()
    try:
      try: _signal_command(process)
      except Exception:
        _curryrtbindings._fork_check()
        logger.exception('Command %s termination failed', process.pid)
      try: _command_exited(process, timeout=1)
      except Exception:
        _curryrtbindings._fork_check()
        logger.exception('Command %s exit observation failed', process.pid)
      # WNOWAIT keeps the exited leader's id reserved through this signal.
      try: _signal_command(process, kill=True)
      except Exception:
        _curryrtbindings._fork_check()
        logger.exception('Command %s final group kill failed', process.pid)
      if process.returncode is None:
        _wait_command(process, timeout=1)
      _curryrtbindings._fork_check()
      if sys.platform == 'win32':
        process._command_job.close()
        process._handle.Close()
      with _command_lock:
        _command_processes.discard(process)
        _command_pending.discard(process)
    except Exception:
      _curryrtbindings._fork_check()
      # A failed child must not prevent bounded cleanup of later children.
      logger.exception('Command %s shutdown failed', process.pid)
  for token, stream in list(_command_streams.items()):
    try: _close_command_stream(_command_owners[token], stream, discard=True)
    except Exception:
      _curryrtbindings._fork_check()
  _curryrtbindings._fork_check()
  _curryrtbindings._heap_drain()
  _curryrtbindings._fork_check()
  shutdown_handles()
  _curryrtbindings._fork_check()
  for token in list(_command_streams):
    try: _standard_stream(token, 'release', '', 0)
    except Exception:
      _curryrtbindings._fork_check()

_atexit.register(_shutdown_native)

def _exit_with(code):
  shutdown_handles()
  raise SystemExit(code)

register_primitive('System.Process.getPID', 0, _os.getpid, True)
register_primitive('System.Process.prim_exitWith', 1, _exit_with, True)
