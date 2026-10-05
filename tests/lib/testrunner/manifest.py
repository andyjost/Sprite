'''
The manifest: what each test file cost on each backend the last time it was
measured.  The file is tests/manifest.json; --update-manifest writes it.

The manifest maps a file name to a backend to an entry:

    duration_s          The wall seconds of the last measured run.
    peak_rss_mb         The largest resident set of the file's session seen
                        in any measured run, in MiB.  null when unknown.
    tests, failures     The counts of the last measured run.
    measured_on_cores   The cores and the memory, in GiB, of the machine of
    measured_on_mem_gb  the measurement.  The size of the machine, not its
                        name: durations and peaks depend on it.

The runner reads two things from an entry: the duration orders the files
(longest first) and selects the fast tier, and the peak sets the cap of the
file: CAP_FACTOR times the peak, at least MIN_CAP.  A file without a peak
gets DEFAULT_CAP.  A file without a duration is assumed to take as long as
the median of the measured files (assumed_duration).  The committed seed may
be sparse.
'''

import json, os, statistics
from . import CAP_FACTOR, DEFAULT_CAP, MIB, MIN_CAP, MANIFEST_FILE

__all__ = ['FORMAT', 'Manifest', 'machine_size']

FORMAT = 1
FIELDS = (
    'duration_s', 'peak_rss_mb', 'tests', 'failures', 'measured_on_cores'
  , 'measured_on_mem_gb'
  )

def machine_size():
  '''The size of this machine: its cores and its memory in GiB, rounded.'''
  from . import procs
  total = procs.mem_total()
  return {
      'measured_on_cores': procs.cpu_count()
    , 'measured_on_mem_gb': None if total is None else round(total / 1024 ** 3)
    }

class Manifest:
  '''The entries of the manifest, with the derived caps and the order.'''

  def __init__(self, files=None, path=None):
    self.files = {} if files is None else files
    self.path = path

  @classmethod
  def load(cls, path=MANIFEST_FILE, missing_ok=True):
    '''Reads the manifest.  A missing file gives an empty manifest.'''
    try:
      with open(path, encoding='utf-8') as stream:
        data = json.load(stream)
    except FileNotFoundError:
      if not missing_ok:
        raise
      return cls(path=path)
    if not isinstance(data, dict) or 'files' not in data:
      raise ValueError('%s: not a manifest' % path)
    if data.get('format') != FORMAT:
      raise ValueError(
          '%s: manifest format %r, this runner reads format %r'
        % (path, data.get('format'), FORMAT)
        )
    return cls(files=data['files'], path=path)

  def save(self, path=None):
    '''Writes the manifest with sorted keys, so a diff stays small.'''
    path = self.path if path is None else path
    data = {'format': FORMAT, 'files': self.files}
    text = json.dumps(data, indent=2, sort_keys=True) + '\n'
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as stream:
      stream.write(text)
    os.replace(tmp, path)

  def entry(self, filename, backend):
    '''The entry of a file on a backend, or None.'''
    return self.files.get(filename, {}).get(backend)

  def duration(self, filename, backend):
    '''The manifest duration in seconds, or None.'''
    entry = self.entry(filename, backend)
    return None if entry is None else entry.get('duration_s')

  def peak(self, filename, backend):
    '''The manifest peak in bytes, or None.'''
    entry = self.entry(filename, backend)
    if entry is None or entry.get('peak_rss_mb') is None:
      return None
    return int(entry['peak_rss_mb'] * MIB)

  def cap(self, filename, backend):
    '''The cap of a file in bytes (see the module docstring).'''
    peak = self.peak(filename, backend)
    if peak is None:
      return DEFAULT_CAP
    return max(MIN_CAP, CAP_FACTOR * peak)

  def assumed_duration(self, backend=None):
    '''
    The duration assumed for a file without an entry: the median of the
    measured durations of ``backend``, or of every backend when that one
    has none; None when nothing is measured.
    '''
    durations = [
        entry['duration_s']
        for entries in self.files.values()
        for name, entry in entries.items()
        if (backend is None or name == backend)
       and entry.get('duration_s') is not None
      ]
    if not durations:
      return None if backend is None else self.assumed_duration()
    return statistics.median(durations)

  def order_key(self, filename, backend):
    '''
    Sorts the longest file first.  A file without a duration is assumed to
    take the median of the measured durations, so the measured heavy files
    start before it, and it starts before the light ones; among equals,
    the file without an entry goes first.  An early start of a long file
    shortens the tail of the run.
    '''
    duration = self.duration(filename, backend)
    if duration is None:
      return (-(self.assumed_duration(backend) or 0), 0)
    return (-duration, 1)

  def update(self, filename, backend, result, size=None):
    '''
    Records a result of one run.  ``result`` has ``duration`` (seconds),
    ``peak`` (bytes), ``tests``, ``failures``, and ``completed``.  The peak
    only grows.  The duration, the counts, and the machine size are written
    only for a run that ended by itself with a unittest verdict (``tests``
    is not None): a killed run, or one that died before its tests ran,
    measured nothing whole.
    '''
    size = machine_size() if size is None else size
    entry = self.files.setdefault(filename, {}).setdefault(
        backend, {name: None for name in FIELDS}
      )
    peak_mb = None if result.peak is None else round(result.peak / MIB)
    if peak_mb is not None:
      old = entry.get('peak_rss_mb')
      entry['peak_rss_mb'] = peak_mb if old is None else max(old, peak_mb)
    if result.completed and result.tests is not None:
      entry['duration_s'] = round(result.duration, 1)
      entry['tests'] = result.tests
      entry['failures'] = result.failures
      entry.update(size)
    return entry
