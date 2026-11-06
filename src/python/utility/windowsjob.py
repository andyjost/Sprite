"""Windows command containment shared by runtime and test runner."""

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
