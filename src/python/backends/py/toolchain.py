'''
The build step of the Python backend: ICurry-JSON to a Python module, with
its bytecode cache.

A generated file carries a format stamp (compiler.FORMAT_VERSION).  Json2Py,
the step that writes the file, refuses a cached file of another stamp, or of
none; the plan then writes the file again from the JSON file.  See is_stale.
'''
from ...toolchain import plans
from ... import exceptions
from ..generic.toolchain import Json2TargetSource
from . import compiler
import importlib.util, itertools, logging, os, py_compile, re, struct

logger = logging.getLogger(__name__)

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Py(interp)
  skeleton.append((plans.UNCONDITIONAL, ['.py'], None))

def bytecode_file(pyfile):
  '''The bytecode cache of a generated Python file, as importlib names it.'''
  return importlib.util.cache_from_source(pyfile)

def compile_bytecode(pyfile):
  '''
  Writes the bytecode cache of ``pyfile`` beside it, under ``__pycache__``.
  The loader reads the cache instead of the source while the source keeps its
  size and time stamp.  The cache is written whether or not the process runs
  with ``-B``: it is a product of the toolchain, like the file itself, not a
  by-product of an import.  A cache that cannot be written is logged and
  skipped; the file loads from source then.
  '''
  try:
    py_compile.compile(pyfile, doraise=True)
  except py_compile.PyCompileError as exc:
    raise exceptions.CompileError(str(exc))
  except OSError as exc:
    logger.warning('cannot write the bytecode cache of %r: %s', pyfile, exc)

def bytecode_is_current(pyfile):
  '''
  True when the bytecode cache of ``pyfile`` exists and importlib would load
  it: its header names the size and the time stamp of the file as it is now,
  or, for a hash-based cache, the hash of its contents.
  '''
  try:
    with open(bytecode_file(pyfile), 'rb') as stream:
      header = stream.read(16)
    stat = os.stat(pyfile)
  except OSError:
    return False
  if len(header) < 16 or header[:4] != importlib.util.MAGIC_NUMBER:
    return False
  flags, = struct.unpack('<I', header[4:8])
  if flags & 1:
    with open(pyfile, 'rb') as stream:
      return header[8:16] == importlib.util.source_hash(stream.read())
  mtime, size = struct.unpack('<II', header[8:16])
  return mtime == int(stat.st_mtime) & 0xFFFFFFFF \
     and size == stat.st_size & 0xFFFFFFFF

def ensure_bytecode(pyfile):
  '''Writes the bytecode cache of ``pyfile`` unless a current one exists.'''
  if os.path.isfile(pyfile) and not bytecode_is_current(pyfile):
    compile_bytecode(pyfile)

# The format stamp of a generated Python file.  The stamp heads the file.
FORMAT_PAT = re.compile(r'# FORMAT: (\d+)')

def format_version(file_in):
  '''The format stamp of a generated file.  A file without one is format 1.'''
  with open(file_in, 'r') as stream:
    for line in itertools.islice(stream, 16):
      m = FORMAT_PAT.match(line)
      if m:
        return int(m.group(1))
  return 1

def source_is_stale(file_in):
  '''
  Tells whether a generated Python file is out of date: its format stamp is
  not the emitter's (compiler.FORMAT_VERSION).  The emitter writes other
  code now, so the plan writes the file again from the JSON file.
  '''
  return format_version(file_in) != compiler.FORMAT_VERSION

class Json2Py(Json2TargetSource):
  NAME = 'json2py'
  SUFFIX = '.py'

  def is_stale(self, filename, currypath=None):
    '''
    Tells whether a cached file of this step is out of date (source_is_stale).
    The plan then starts again from the JSON file (Plan.prune_stale).  The
    plan asks about the JSON input of this step as well, which is never
    refused.
    '''
    return filename.endswith('.py') and source_is_stale(filename)

  def __call__(self, file_in, currypath, **ignored):
    file_out = super().__call__(file_in, currypath, **ignored)
    compile_bytecode(file_out)
    return file_out
