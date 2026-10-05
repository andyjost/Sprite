'''
Implements Interpreter.stats, the statistics of a run.
'''

from .. import toolchain
import os, resource, sys, time

__all__ = [
    'KEYS', 'SCHEDULER_KEYS', 'Stats', 'format_stats', 'histogram_median'
  , 'peak_rss', 'scheduler_fields', 'stats'
  ]

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

KEYS = (
    'wall', 'cpu', 'steps', 'forks', 'collections', 'peak_rss', 'compile'
  , 'gc_seconds', 'swapped', 'failed_compiles'
  )

# The keys a C++ runtime built with the scheduler counters (make COUNTERS=1)
# adds after KEYS.  See scheduler_fields.
SCHEDULER_KEYS = (
    'serial_steps', 'nested_steps', 'shared_steps', 'queue_max'
  , 'configurations', 'failures', 'failed_steps'
  , 'lifetime_median', 'lifetime_mean', 'lifetime_max'
  , 'nested_configurations', 'nested_lifetime_median', 'nested_lifetime_mean'
  , 'nested_lifetime_max'
  )

class Stats(dict):
  '''
  The statistics of a run, keyed by :data:`KEYS` in that order, followed by
  :data:`SCHEDULER_KEYS` when the runtime has the scheduler counters.
  ``str`` gives one line of key=value pairs, the line ``sprite-exec --stats``
  prints.
  '''
  def __str__(self):
    return format_stats(self)

def format_stats(stats):
  '''
  Formats statistics as one line of key=value pairs, in the order of the
  keys.  Seconds and means have six decimals; counts and bytes are integers.
  '''
  return ' '.join('%s=%s' % (key, _format(value)) for key, value in stats.items())

def _format(value):
  return '%.6f' % value if isinstance(value, float) else str(value)

def histogram_median(histogram):
  '''
  The median of a step histogram of the scheduler counters: exact counts in
  ``exact`` for the values below ``len(exact)``, and in ``coarse[k]`` the
  count of the values in [2**k, 2**(k+1)).  A median that falls in a coarse
  bucket is reported as the lower bound of the bucket.  Zero when the
  histogram is empty.  Of an even number of values, the lower middle one
  counts.
  '''
  count = histogram['count']
  if not count:
    return 0
  target = (count + 1) // 2
  seen = 0
  for value, n in enumerate(histogram['exact']):
    seen += n
    if seen >= target:
      return value
  for k, n in enumerate(histogram['coarse']):
    seen += n
    if seen >= target:
      return 2 ** k
  raise ValueError('the histogram counts fewer values than its count')

def _lifetime_fields(prefix, queue):
  '''The fields of the lifetimes of one kind of queue.'''
  histogram = queue['lifetimes']
  ended = queue['values'] + queue['failures'] + queue['forked']
  count = histogram['count']
  mean = histogram['sum'] / count if count else 0.0
  return [
      (prefix + 'configurations', ended + queue['left'])
    , (prefix + 'lifetime_median', histogram_median(histogram))
    , (prefix + 'lifetime_mean', mean)
    , (prefix + 'lifetime_max', histogram['max'])
    ]

def scheduler_fields(counters):
  '''
  The fields derived from the scheduler counters of the C++ runtime, as a
  list of (key, value) in the order of :data:`SCHEDULER_KEYS`.  ``counters``
  is the dict the runtime reports (summed over the evaluations), or None,
  which gives every field as zero.

  ``serial_steps``
      Steps taken while the outermost queue held one configuration.  The
      serial fraction is this over ``steps``.
  ``nested_steps``
      Steps taken inside a set function, in a nested queue.
  ``shared_steps``
      Steps whose redex another configuration created.  The shared-work
      ratio is this over ``steps``.
  ``queue_max``
      The largest number of configurations in the outermost queue.
  ``configurations``
      The configurations of the outermost queue: the ones that ended by a
      value, a failure, or a fork, and the ones still in the queue.
  ``failures``, ``failed_steps``
      The configurations of the outermost queue that failed, and the steps
      they took.
  ``lifetime_median``, ``lifetime_mean``, ``lifetime_max``
      The steps from the creation of a configuration of the outermost queue
      to its end by a value, a failure, or a fork.  The median is exact below
      1024 steps; above, it is the lower bound of a power-of-two bucket.
  ``nested_configurations``, ``nested_lifetime_median``,
  ``nested_lifetime_mean``, ``nested_lifetime_max``
      The same for the configurations of the queues of set functions, which
      end by a value, a failure, or a fork.
  '''
  if counters is None:
    return [(key, 0.0 if key.endswith('_mean') else 0)
            for key in SCHEDULER_KEYS]
  outer, nested = counters['outer'], counters['nested']
  configurations, *lifetimes = _lifetime_fields('', outer)
  fields = [
      ('serial_steps', counters['serial_steps'])
    , ('nested_steps', counters['nested_steps'])
    , ('shared_steps', counters['shared_steps'])
    , ('queue_max', counters['queue_max'])
    , configurations
    , ('failures', outer['failures'])
    , ('failed_steps', outer['failure_steps'])
    ] + lifetimes + _lifetime_fields('nested_', nested)
  assert tuple(key for key, _ in fields) == SCHEDULER_KEYS
  return fields

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
    ``gc_seconds``
        Seconds the node collector of the C++ backend spent in its
        collections.  The Python backend reports zero.
    ``swapped``
        The functions that tiered execution of the C++ backend swapped from
        the interpreter to compiled code in this process (the interpreter
        flag ``interpret`` set to 'tiered').  The Python backend reports
        zero.
    ``failed_compiles``
        The background compiles of tiered execution that failed in this
        process; the modules stay interpreted.  The Python backend reports
        zero.

    A C++ runtime built with the scheduler counters (make COUNTERS=1) adds
    the keys of :data:`SCHEDULER_KEYS`; see :func:`scheduler_fields`.
  '''
  usage = resource.getrusage(resource.RUSAGE_SELF)
  totals = interp._evaluation_totals
  fields = [
      ('wall', time.monotonic() - _START)
    , ('cpu', usage.ru_utime + usage.ru_stime)
    , ('steps', totals.steps)
    , ('forks', totals.forks)
    , ('collections', interp.backend.num_collections())
    , ('peak_rss', usage.ru_maxrss * _RSS_UNIT)
    , ('compile', toolchain.compile_seconds())
    , ('gc_seconds', interp.backend.gc_seconds())
    ]
  swapped, failed = interp.backend.tiered_counts()
  fields += [('swapped', swapped), ('failed_compiles', failed)]
  if interp.backend.scheduler_counters_enabled():
    fields += scheduler_fields(totals.scheduler)
  return Stats(fields)
