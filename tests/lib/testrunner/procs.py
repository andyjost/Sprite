'''
Processes: the sessions of the children, their resident sets, the kills, and
the memory and the cores of the machine.

Every file runs in a session of its own (``start_new_session=True``), so the
session id of every process it starts, directly or through a compiler, is
the pid of the child.  The functions here walk /proc and match that id in
/proc/<pid>/stat.  Nothing depends on cgroups or on a service manager.  On
macOS, which has no /proc, one run of ps(1) gives the same table, with the
process group of the leader as the key of a session (see _table_darwin:
ps prints no session id there, and its session pointer is hidden from a
user, the same for every process), and sysctl and vm_stat give the memory
of the machine (see _meminfo_darwin).

The ``timeout`` command that the tests wrap their own children in puts its
child into a new process group.  So a kill of the process group of the child
misses those processes.  ``kill_session`` kills every process of the
session instead.  A child that starts a session of its own (``setsid``, or
``start_new_session=True``, as the benchmark harness and func_complete.py
do) leaves the session; the scan also walks the parent links down from the
leader, so such a child and its processes stay with the file.  The members
of one scan are the roots of the next, so a process whose parent ended
stays with its file as well.

A scan also reads the name of each process (the comm field).  The names in
TOOLS belong to the Curry toolchain: the front end, icurry and PAKCS, which
run on swipl, and the C++ compiler and linker.  The watchdog allows a
session more memory while one of them runs (see scheduler.Watchdog).
'''

import os, re, signal, subprocess, sys, time
from curry.utility import cpu_count
try:
  import psutil
except ImportError:
  psutil = None

__all__ = [
    'TOOLS', 'cpu_count', 'kill_session', 'mem_available', 'mem_total'
  , 'meminfo', 'scan_sessions', 'session_rss', 'toolchain_in'
  ]

# The process names of the Curry toolchain, as /proc/<pid>/stat reports
# them: the Curry front end (a wrapper script and the binary), icurry and
# PAKCS (both run on swipl), and the C++ compiler proper, its driver, and
# the linker.  Whether one of them runs depends on the state of the tree
# (the ICurry cache, the products of the modules), not on the test.
TOOLS = frozenset([
    'curry-frontend', 'pakcs-frontend', 'kics2-frontend', 'icurry', 'pakcs'
  , 'swipl', 'cc1plus', 'cc1', 'g++', 'gcc', 'c++', 'clang', 'clang++'
  , 'collect2', 'ld', 'lto1', 'lto-wrapper'
  ])

PAGE_SIZE = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096

# macOS: no /proc; ps, sysctl and vm_stat stand in (issue #162).
DARWIN = sys.platform == 'darwin'

def _meminfo_darwin():
  '''
  The two fields the runner reads, on macOS: MemTotal from sysctl
  hw.memsize, and MemAvailable as the free, inactive and speculative pages
  of vm_stat, in bytes.  Empty when a command fails.
  '''
  fields = {}
  try:
    total = subprocess.run(
        ['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, check=True
      ).stdout
    fields['MemTotal'] = int(total.strip())
    stat = subprocess.run(['vm_stat'], capture_output=True, text=True, check=True).stdout
  except (OSError, subprocess.CalledProcessError, ValueError):
    return fields
  match = re.search(r'page size of (\d+) bytes', stat)
  page = int(match.group(1)) if match else PAGE_SIZE
  pages = 0
  for name in 'Pages free', 'Pages inactive', 'Pages speculative':
    match = re.search(r'^%s:\s+(\d+)' % re.escape(name), stat, re.M)
    if match:
      pages += int(match.group(1))
  fields['MemAvailable'] = pages * page
  return fields

def meminfo(path='/proc/meminfo'):
  '''The fields of /proc/meminfo, in bytes (on macOS, see _meminfo_darwin).'''
  if sys.platform == 'win32':
    if psutil is None:
      return {}
    memory = psutil.virtual_memory()
    return {'MemTotal': memory.total, 'MemAvailable': memory.available}
  if DARWIN and path == '/proc/meminfo':
    return _meminfo_darwin()
  fields = {}
  try:
    with open(path) as stream:
      for line in stream:
        name, _, rest = line.partition(':')
        parts = rest.split()
        if not parts:
          continue
        value = int(parts[0])
        if len(parts) > 1 and parts[1] == 'kB':
          value *= 1024
        fields[name.strip()] = value
  except (OSError, ValueError):
    pass
  return fields

def mem_available(path='/proc/meminfo'):
  '''MemAvailable in bytes, or None when it cannot be read.'''
  return meminfo(path).get('MemAvailable')

def mem_total(path='/proc/meminfo'):
  '''MemTotal in bytes, or None when it cannot be read.'''
  return meminfo(path).get('MemTotal')

def _stat(pid):
  '''
  The command name of a process and the fields of /proc/<pid>/stat after it,
  or None when the process is gone.  The name may hold spaces and
  parentheses, so the split starts after the last closing parenthesis.
  '''
  try:
    with open('/proc/%d/stat' % pid, 'rb') as stream:
      data = stream.read()
  except OSError:
    return None
  close = data.rfind(b')')
  comm = data[data.find(b'(') + 1:close].decode('utf-8', 'replace')
  return comm, data[close + 2:].split()

def _stat_fields(pid):
  '''The fields of /proc/<pid>/stat after the command name, or None.'''
  stat = _stat(pid)
  return None if stat is None else stat[1]

# Indexes into the fields after the command name.  The man page numbers the
# fields from 1 with pid first and comm second, so state is field 3.
STATE, PPID, PGRP, SESSION, RSS = 0, 1, 2, 3, 21

def _pids():
  try:
    names = os.listdir('/proc')
  except OSError:
    return []
  return [int(name) for name in names if name.isdigit()]

def _table_darwin():
  '''
  The table of _table from one run of ps(1) on macOS: the session field is
  the process group, since ps prints no session id there and its session
  pointer is hidden from a user (the same value for every process, which
  would make every process a member of every session); the leader of a
  session made with start_new_session is the leader of its process group,
  and the processes that the timeout command moves into groups of their
  own are found through the parent links (see scan_sessions).  The
  resident set is reported in KiB, the state is the first letter of the
  stat column, and the command name comes from the command line (see
  _darwin_name).  Empty when ps fails.
  '''
  try:
    out = subprocess.run(
        ['ps', '-axo', 'pid=,ppid=,pgid=,rss=,stat=,command=']
      , capture_output=True, text=True, check=True
      ).stdout
  except (OSError, subprocess.CalledProcessError):
    return {}
  table = {}
  for line in out.splitlines():
    parts = line.split(None, 5)
    if len(parts) < 6:
      continue
    try:
      pid, ppid, rss = int(parts[0]), int(parts[1]), int(parts[3]) * 1024
    except ValueError:
      continue
    state = parts[4][:1].encode('ascii', 'replace')
    table[pid] = (ppid, parts[2], rss, state, _darwin_name(parts[5]))
  return table

# The shells, whose script is the name of a process (see _darwin_name).
SHELLS = frozenset(['sh', 'bash', 'zsh', 'dash', 'ksh'])

def _darwin_name(command):
  '''
  The command name of a process from the command line ps prints on macOS:
  the leaf name of its program, or of its script when the program is a
  shell, as /proc/<pid>/comm names a script on Linux.  The wrapper scripts
  of the toolchain (tools/cxx, curry-frontend) are found by their names so.
  '''
  words = command.split()
  if not words:
    return ''
  name = os.path.basename(words[0])
  if name in SHELLS and len(words) > 1 and not words[1].startswith('-'):
    name = os.path.basename(words[1])
  return name

def _session_key(table, sid):
  '''
  The value of the session field of ``table`` for the session whose leader
  is ``sid``: the id itself on Linux, where the field is the pid of the
  leader; on macOS the process group of the leader (its own pid for a
  leader made with start_new_session), or None when the leader is gone
  (the parent links from the roots then find the members).
  '''
  if sys.platform == 'win32':
    return None
  if not DARWIN:
    return sid
  entry = table.get(sid)
  return None if entry is None else entry[1]

def _table():
  '''
  One walk of /proc: a dict from each pid to its parent, its session id,
  its resident set in bytes, its state, and its command name.  On macOS,
  one run of ps (see _table_darwin).
  '''
  if sys.platform == 'win32':
    return {}
  if DARWIN:
    return _table_darwin()
  table = {}
  for pid in _pids():
    stat = _stat(pid)
    if stat is None or len(stat[1]) <= RSS:
      continue
    comm, fields = stat
    try:
      ppid, sid, pages = int(fields[PPID]), int(fields[SESSION]), int(fields[RSS])
    except ValueError:
      continue
    table[pid] = (ppid, sid, pages * PAGE_SIZE, fields[STATE], comm)
  return table

def scan_sessions(sids, roots=None):
  '''
  One walk of /proc.  Returns a dict from each session id in ``sids`` to a
  triple: the sum of the resident sets of its processes, in bytes, the
  sorted list of their pids, and a dict from each pid to its command name.

  The processes of a session are the ones whose session id is ``sid`` and
  the descendants of its leader through the parent links.  The second set
  finds a child that started a session of its own.  ``roots`` maps a
  session id to further pids to walk down from: the members of the last
  scan, so a process whose parent ended stays with its session.  A zombie
  counts with a resident set of zero.
  '''
  if sys.platform == 'win32':
    return {sid: _scan_windows(sid) for sid in sids}
  table = _table()
  children = {}
  for pid, entry in table.items():
    children.setdefault(entry[0], []).append(pid)
  result = {}
  for sid in sids:
    key = _session_key(table, sid)
    members = set(
        pid for pid, entry in table.items() if key is not None and entry[1] == key
      )
    stack = [sid] + [pid for pid in (roots or {}).get(sid, ()) if pid in table]
    seen = set()
    while stack:
      pid = stack.pop()
      if pid in seen:
        continue
      seen.add(pid)
      if pid in table:
        members.add(pid)
      stack.extend(children.get(pid, ()))
    rss = sum(table[pid][2] for pid in members)
    comms = {pid: table[pid][4] for pid in members}
    result[sid] = (rss, sorted(members), comms)
  return result

def toolchain_in(comms):
  '''
  The names of the processes of the Curry toolchain among the command names
  ``comms`` (an iterable of names), sorted; empty when none runs.
  '''
  tools = TOOLS | {'clang-cl', 'cl', 'link', 'lld-link'} if sys.platform == 'win32' else TOOLS
  return sorted(tools.intersection(comms))

def session_rss(sid):
  '''The resident set of one session, in bytes.'''
  return scan_sessions([sid])[sid][0]

def kill_session(sid, sig=getattr(signal, 'SIGKILL', None), rounds=20, pause=0.05, roots=(), leader=None, reason="cleanup"):
  '''
  Sends ``sig`` to every process of the session ``sid`` and to the process
  group of its leader, in rounds, until a scan finds no process of the
  session or ``rounds`` is reached.  A process that forks between the scan
  and the kill is caught by the next round.  ``roots`` are the pids of the
  session seen before (see scan_sessions); every pid a round finds joins
  them.  On Windows, a kernel job owns the processes; without a job, only
  the retained leader handle is killed. Returns the pids that were signalled.
  '''
  if sys.platform == 'win32':
    return _kill_windows(sid, reason, leader)
  signalled = set()
  roots = set(roots)
  for _ in range(rounds):
    _, pids, _ = scan_sessions([sid], roots={sid: roots})[sid]
    roots.update(pids)
    live = [pid for pid in pids if _state(pid) not in (None, b'Z')]
    if not live:
      break
    try:
      os.killpg(sid, sig)
    except (ProcessLookupError, PermissionError):
      pass
    for pid in live:
      try:
        os.kill(pid, sig)
        signalled.add(pid)
      except (ProcessLookupError, PermissionError):
        pass
    time.sleep(pause)
  return sorted(signalled)

def _state(pid):
  if sys.platform == 'win32':
    return b'R' if psutil is not None and psutil.pid_exists(pid) else None
  if DARWIN:
    try:
      out = subprocess.run(
          ['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True
        ).stdout.strip()
    except OSError:
      return None
    return out[:1].encode('ascii', 'replace') if out else None
  fields = _stat_fields(pid)
  return None if fields is None else fields[STATE]

def is_alive(pid):
  '''True when ``pid`` exists and is not a zombie.'''
  return _state(pid) not in (None, b'Z')


# Keep job and leader handles until the scheduler finishes the file.
_WINDOWS = {}

class WindowsJob:
  """Kernel job ownership; loaded lazily so POSIX can import this module."""
  def __init__(self, process):
    import ctypes as c
    from ctypes import wintypes as w
    self.c = c
    self.kernel = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([w.LPVOID, w.LPCWSTR], w.HANDLE),
        'SetInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, c.c_uint32], c.c_int32),
        'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], c.c_int32),
        'QueryInformationJobObject': ([w.HANDLE, c.c_int, w.LPVOID, c.c_uint32, w.LPVOID], c.c_int32),
        'TerminateJobObject': ([w.HANDLE, c.c_uint32], c.c_int32),
        'CloseHandle': ([w.HANDLE], c.c_int32)}
    for name, (args, result) in signatures.items():
      fn = getattr(self.kernel, name)
      fn.argtypes, fn.restype = args, result
    class Limits(c.Structure):
      _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64),
                  ('flags', c.c_uint32), ('minimum', c.c_size_t),
                  ('maximum', c.c_size_t), ('active', c.c_uint32),
                  ('affinity', c.c_size_t), ('priority', c.c_uint32),
                  ('scheduling', c.c_uint32)]
    class IOCounts(c.Structure):
      _fields_ = [(name, c.c_uint64) for name in (
          'reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]
    class ExtendedLimits(c.Structure):
      _fields_ = [('basic', Limits), ('io', IOCounts),
                  ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                  ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
    self.handle = self.kernel.CreateJobObjectW(None, None)
    if not self.handle:
      raise c.WinError(c.get_last_error())
    limits = ExtendedLimits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not self.kernel.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)) or not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
      error = c.get_last_error()
      self.close()
      raise c.WinError(error)

  def members(self):
    c = self.c
    size = 256
    while True:
      buffer = c.create_string_buffer(size)
      if self.kernel.QueryInformationJobObject(self.handle, 3, buffer, size, None):
        count = c.c_uint32.from_buffer(buffer, 4).value
        return list((c.c_size_t * count).from_buffer(buffer, 8))
      if c.get_last_error() != 234:  # ERROR_MORE_DATA
        raise c.WinError(c.get_last_error())
      size *= 2

  def terminate(self):
    if not self.kernel.TerminateJobObject(self.handle, 1):
      raise self.c.WinError(self.c.get_last_error())

  def close(self):
    if self.handle:
      self.kernel.CloseHandle(self.handle)
      self.handle = None


def start_windows(process):
  state = {'job': None, 'leader': process}
  _WINDOWS[process.pid] = state
  try:
    state['job'] = WindowsJob(process)
  except OSError:
    print('Windows: pid=%d has no job; its descendants are not tracked.'
          % process.pid, flush=True)
  finally:
    try:
      # Popen closes the primary thread handle, so resume the whole process.
      if psutil is not None:
        psutil.Process(process.pid).resume()
      else:
        import ctypes as c
        from ctypes import wintypes as w
        resume = c.WinDLL('ntdll').NtResumeProcess
        resume.argtypes, resume.restype = [w.HANDLE], c.c_int32
        status = resume(int(process._handle))
        if status < 0:
          raise OSError('NtResumeProcess failed: %d' % status)
    except OSError:
      # A failed resume must not leave a suspended leader behind.
      process.kill()
      process.wait()
      close_windows(process.pid)
      raise


def close_windows(sid):
  state = _WINDOWS.pop(sid, None)
  if state and state['job']:
    state['job'].close()


def _scan_windows(sid):
  state = _WINDOWS.get(sid)
  if not state:
    return None, [], {}
  job = state['job']
  leader = state['leader'] if job is None else None
  pids = job.members() if job else ([sid] if leader.poll() is None else [])
  table = {pid: (None, 'unknown') for pid in pids}
  if psutil is not None:
    for pid in pids:
      try:
        proc = psutil.Process(pid)
        table[pid] = (proc.memory_info().rss, proc.name().removesuffix('.exe'))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
  rss = None if any(rss is None for rss, _ in table.values()) else sum(
      rss for rss, _ in table.values())
  return rss, sorted(table), {pid: name for pid, (_, name) in table.items()}


def _kill_windows(sid, reason, leader=None):
  state = _WINDOWS.get(sid)
  if not state:
    return []
  if state['job'] is None:
    leader = state['leader']
    if leader.poll() is None:
      print('kill pid=%d name=leader reason=%s' % (sid, reason), flush=True)
      leader.kill()
      return [sid]
    return []
  _, pids, names = _scan_windows(sid)
  for pid in pids:
    print('kill pid=%d name=%s reason=%s' % (pid, names[pid], reason), flush=True)
  state['job'].terminate()
  return pids
