'''
Implements Interpreter.stats, the statistics of a run.
'''

from .. import toolchain
import os, resource, sys, time

__all__ = ['KEYS', 'Stats', 'format_stats', 'peak_rss', 'stats']

def _process_start():
  '''
  The monotonic clock at the start of this process.  Linux tells when a
  process started, in clock ticks after boot, and how long ago the system
  booted.  Elsewhere, the moment this module was imported stands in.
  '''
  try:
    with open('/proc/self/stat') as stream:
      # The command name, in parentheses, may hold spaces; the fields after
      # it start at field 3.  The start time is field 22.
      fields = stream.read().rpartition(')')[2].split()
    start = int(fields[19]) / os.sysconf('SC_CLK_TCK')
    with open('/proc/uptime') as stream:
      uptime = float(stream.read().split()[0])
  except (OSError, ValueError, IndexError):
    return time.monotonic()
  return time.monotonic() - (uptime - start)

# This module is imported with the package and is not run again by a reload
# of the package, so the start is read once per process.
_START = _process_start()

# ru_maxrss is in kibibytes on Linux and in bytes on macOS.
_RSS_UNIT = 1 if sys.platform == 'darwin' else 1024

KEYS = ('wall', 'cpu', 'steps', 'forks', 'collections', 'peak_rss', 'compile')

class Stats(dict):
  '''
  The statistics of a run, keyed by :data:`KEYS` in that order.  ``str``
  gives one line of key=value pairs, the line ``sprite-exec --stats`` prints.
  '''
  def __str__(self):
    return format_stats(self)

def format_stats(stats):
  '''
  Formats statistics as one line of key=value pairs.  Seconds have six
  decimals; counts and bytes are integers.
  '''
  return ' '.join('%s=%s' % (key, _format(stats[key])) for key in KEYS)

def _format(value):
  return '%.6f' % value if isinstance(value, float) else str(value)

def peak_rss():
  '''The peak resident set size of this process, in bytes.'''
  return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * _RSS_UNIT

def stats(interp):
  '''
  Reports the statistics of the run.

  Returns:
    A :class:`Stats` object, a dict with these keys, in this order:

    ``wall``
        Seconds since this process started (on Linux; elsewhere, since the
        Curry system was imported).  The start time of a process has a
        resolution of one clock tick, 10 ms on most systems.
    ``cpu``
        User plus system CPU seconds of this process.  Child processes, such
        as the Curry front end and the C++ compiler, are not included.
    ``steps``
        The rewrite steps taken by the evaluations of this interpreter, a
        running evaluation included.  A soft reset keeps the count.
    ``forks``
        The number of times a configuration forked at a choice in those
        evaluations.
    ``collections``
        The collections run in this process by the node collector of the
        C++ backend.  The Python backend reports zero.
    ``peak_rss``
        The peak resident set size of this process, in bytes.
    ``compile``
        Seconds this process spent in the steps of the toolchain: the Curry
        front end, the ICurry-JSON conversion, the code generator, and the
        C++ compiler.  Zero when every file was current.
  '''
  usage = resource.getrusage(resource.RUSAGE_SELF)
  totals = interp._evaluation_totals
  return Stats([
      ('wall', time.monotonic() - _START)
    , ('cpu', usage.ru_utime + usage.ru_stime)
    , ('steps', totals.steps)
    , ('forks', totals.forks)
    , ('collections', interp.backend.num_collections())
    , ('peak_rss', usage.ru_maxrss * _RSS_UNIT)
    , ('compile', toolchain.compile_seconds())
    ])
