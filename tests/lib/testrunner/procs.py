'''
Processes: the sessions of the children, their resident sets, the kills, and
the memory and the cores of the machine.

Every file runs in a session of its own (``start_new_session=True``), so the
session id of every process it starts, directly or through a compiler, is
the pid of the child.  The functions here walk /proc and match that id in
/proc/<pid>/stat.  Nothing depends on cgroups or on a service manager.

The ``timeout`` command that the tests wrap their own children in puts its
child into a new process group.  So a kill of the process group of the child
misses those processes.  ``kill_session`` kills every process of the
session instead.  A child that starts a session of its own (``setsid``, or
``start_new_session=True``, as the benchmark harness and func_complete.py
do) leaves the session; the scan also walks the parent links down from the
leader, so such a child and its processes stay with the file.  The members
of one scan are the roots of the next, so a process whose parent ended
stays with its file as well.
'''

import os, signal, time

__all__ = [
    'cpu_count', 'kill_session', 'mem_available', 'mem_total', 'meminfo'
  , 'scan_sessions', 'session_rss'
  ]

PAGE_SIZE = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096

def meminfo(path='/proc/meminfo'):
  '''The fields of /proc/meminfo, in bytes.'''
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

def cpu_count():
  '''The cores this process may use.'''
  count = None
  if hasattr(os, 'process_cpu_count'):
    count = os.process_cpu_count()
  return count or os.cpu_count() or 1

def _stat_fields(pid):
  '''
  The fields of /proc/<pid>/stat after the command name, or None when the
  process is gone.  The name may hold spaces and parentheses, so the split
  starts after the last closing parenthesis.
  '''
  try:
    with open('/proc/%d/stat' % pid, 'rb') as stream:
      data = stream.read()
  except OSError:
    return None
  tail = data[data.rfind(b')') + 2:]
  return tail.split()

# Indexes into the fields after the command name.  The man page numbers the
# fields from 1 with pid first and comm second, so state is field 3.
STATE, PPID, PGRP, SESSION, RSS = 0, 1, 2, 3, 21

def _pids():
  try:
    names = os.listdir('/proc')
  except OSError:
    return []
  return [int(name) for name in names if name.isdigit()]

def _table():
  '''
  One walk of /proc: a dict from each pid to its parent, its session id,
  its resident set in bytes, and its state.
  '''
  table = {}
  for pid in _pids():
    fields = _stat_fields(pid)
    if fields is None or len(fields) <= RSS:
      continue
    try:
      ppid, sid, pages = int(fields[PPID]), int(fields[SESSION]), int(fields[RSS])
    except ValueError:
      continue
    table[pid] = (ppid, sid, pages * PAGE_SIZE, fields[STATE])
  return table

def scan_sessions(sids, roots=None):
  '''
  One walk of /proc.  Returns a dict from each session id in ``sids`` to a
  pair: the sum of the resident sets of its processes, in bytes, and the
  sorted list of their pids.

  The processes of a session are the ones whose session id is ``sid`` and
  the descendants of its leader through the parent links.  The second set
  finds a child that started a session of its own.  ``roots`` maps a
  session id to further pids to walk down from: the members of the last
  scan, so a process whose parent ended stays with its session.  A zombie
  counts with a resident set of zero.
  '''
  table = _table()
  children = {}
  for pid, (ppid, _, _, _) in table.items():
    children.setdefault(ppid, []).append(pid)
  result = {}
  for sid in sids:
    members = set(pid for pid, entry in table.items() if entry[1] == sid)
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
    result[sid] = (rss, sorted(members))
  return result

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
    _, pids = scan_sessions([sid], roots={sid: roots})[sid]
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
  fields = _stat_fields(pid)
  return None if fields is None else fields[STATE]

def is_alive(pid):
  '''True when ``pid`` exists and is not a zombie.'''
  return _state(pid) not in (None, b'Z')
