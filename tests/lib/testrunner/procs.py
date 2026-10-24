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
  stat column, and the command name is the leaf name of the path ps
  prints.  Empty when ps fails.
  '''
  try:
    out = subprocess.run(
        ['ps', '-axo', 'pid=,ppid=,pgid=,rss=,stat=,comm=']
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
    table[pid] = (ppid, parts[2], rss, state, os.path.basename(parts[5].strip()))
  return table

def _session_key(table, sid):
  '''
  The value of the session field of ``table`` for the session whose leader
  is ``sid``: the id itself on Linux, where the field is the pid of the
  leader; on macOS the process group of the leader (its own pid for a
  leader made with start_new_session), or None when the leader is gone
  (the parent links from the roots then find the members).
  '''
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
  return sorted(TOOLS.intersection(comms))

def session_rss(sid):
  '''The resident set of one session, in bytes.'''
  return scan_sessions([sid])[sid][0]

def kill_session(sid, sig=signal.SIGKILL, rounds=20, pause=0.05, roots=()):
  '''
  Sends ``sig`` to every process of the session ``sid`` and to the process
  group of its leader, in rounds, until a scan finds no process of the
  session or ``rounds`` is reached.  A process that forks between the scan
  and the kill is caught by the next round.  ``roots`` are the pids of the
  session seen before (see scan_sessions); every pid a round finds joins
  them.  Returns the pids that were signalled.
  '''
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
