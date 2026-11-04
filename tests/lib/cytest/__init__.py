# The rotation of the C++ backend in step mode for every test file, however
# it is run (the runner and the CI script set the same default): the exact
# counters and the order of the values of a search then reproduce.  A value
# in the environment wins, so SPRITE_ROTATION=time:10ms runs a file in time
# mode; an empty value counts as unset, as it does for the interpreter.  The
# variable must be set before the first import of curry.
import os
if not os.environ.get('SPRITE_ROTATION'):
  os.environ['SPRITE_ROTATION'] = 'steps:65536'
# The warnings of the Curry front end (overlapping rules) off for every test
# file, as the runner and the benchmark harness set it, so the output of a
# suite does not change with the state of the products; a test of the
# warnings sets the variable itself (curry.toolchain._frontend).
if not os.environ.get('SPRITE_FRONTEND_WARNINGS'):
  os.environ['SPRITE_FRONTEND_WARNINGS'] = '0'
# The product cache of the C++ backend under tests/.cache, as the runner
# sets it, so a file run by hand writes nothing under the cache directory of
# the user.  A value in the environment wins; the empty string turns the
# cache off.
os.environ.setdefault(
    'SPRITE_PRODUCT_CACHE'
  , os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
      , '.cache', 'products'
      )
  )

from . import raw
from .checkers import check_expressions, check_indexing, check_predicate
import builtins
import contextlib
import functools
import gc
import os
import shutil
import signal
import subprocess
import sys
import unittest
import warnings

@contextlib.contextmanager
def trap():
  '''
  (Built-in) Traps test failures for debugging.

      with trap():
        self.assertTrue(...)
  '''
  try:
    yield None
  except Exception as e:
    breakpoint(msg=repr(str(e)), depth=2)
    raise

builtins.trap = trap

# Enable a break when certain exceptions occur.  For instance, this can be used
# to break whenever a RuntimeError or AssertionError occurs (n.b., that's an
# assertion failure, NOT a unittest.assert* failure).
def breakOn(exc_name):
  exception = getattr(builtins, exc_name)
  def __new__(cls, *args, **kwds):
    # breakpoint(depth=1)
    pdbtrace()
    return exception(*args, **kwds)
  replacement = type(exc_name, (exception,), {'__new__': __new__})
  setattr(builtins, exc_name, replacement)

  if exc_name:
    breakOn(exc_name)

# ================================================================================
# It is now OK to load the curry module.

from .testcase import TestCase, FunctionalTestCase
from io import StringIO
import importlib



def setio(stdin=None, stdout=None, stderr=None):
  '''
  Builds a decorator that configures the I/O of the global interpreter found in
  ``curry`` module.

  Note that TestCase resets the curry module after each test, so the I/O
  configuration is only affected for the test decorated.

  Parameters:
  -----------
    ``stdin``
        The configuration for stdin.  This can be a stream-like object (such as
        an open file) or a string.  If a string is provided, then it will be
        the input to the program.
    ``stdout``
        The configuration for stdout.  A stream-like object or string.  If a string
        is provided, then the output will be a StringIO object initialized with the
        given value.
    ``stderr``
        The configuration for stderr.  Similar to stdout.
  '''
  def setio(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
      import curry
      interp = raw.interp()
      if stdin is not None:
        if isinstance(stdin, str):
          io = StringIO()
          io.write(stdin)
          io.seek(0)
          interp.stdin = io
        else:
          interp.stdin = stdin
      if stdout is not None:
        if isinstance(stdout, str):
          io = StringIO()
          io.write(stdout)
          interp.stdout = io
        else:
          interp.stdout = stdout
      if stderr is not None:
        if isinstance(stderr, str):
          io = StringIO()
          io.write(stderr)
          interp.stderr = io
        else:
          interp.stderr = stderr
      return f(*args, **kwds)
    return wrapper
  return setio


def with_flags(**flags):
  '''Test decorator that set the specified flags.  Implies hardreset.'''
  def decorator(f):
    @functools.wraps(f)
    @hardreset
    def replacement(*args, **kwds):
      import curry
      curry.reset(**flags)
      return f(*args, **kwds)
    return replacement
  return decorator

def hardreset(f):
  '''Test decorator that hard-resets the curry module after the test runs.'''
  @functools.wraps(f)
  def decorator(*args, **kwds):
    try:
      return f(*args, **kwds)
    finally:
      import curry
      importlib.reload(curry)
      gc.collect() # The old interpreter is garbage.  Unload its modules now.
  return decorator

def readfile(filename, mode='r', fopen=open):
  with fopen(filename, mode) as istream:
    return istream.read()

class TimeoutError(AssertionError):
  '''
  Raised by ``timeout`` when a test exceeds its time limit.  An
  AssertionError, so the test fails rather than errors.
  '''

class timeout(contextlib.ContextDecorator):
  '''
  Fails a test that runs longer than ``seconds``.  Use it as a decorator or as
  a context manager::

      @cytest.timeout(10)
      def test_something(self):
        ...

      with cytest.timeout(10):
        ...

  The limit is enforced with SIGALRM, so it applies to Python code in the main
  thread.  On Windows it is a no-op; the runner bounds the test file.
  Code that spins inside C++ is not interrupted; run such a test in a
  subprocess instead.  After the limit, the timer repeats every second in case
  the first exception is swallowed.

  Apply the decorator innermost, directly on the test function and below
  ``with_flags`` or ``hardreset``.  Their cleanup reloads ``curry``, and the
  repeating alarm must not fire inside it.
  '''
  def __init__(self, seconds):
    self.seconds = seconds

  def _expire(self, signum, frame):
    raise TimeoutError('timeout after %s seconds' % self.seconds)

  def __enter__(self):
    if sys.platform == 'win32':
      return self
    if not hasattr(signal, 'SIGALRM'):
      raise unittest.SkipTest('timeout requires POSIX SIGALRM')
    self.prev_handler = signal.signal(signal.SIGALRM, self._expire)
    signal.setitimer(signal.ITIMER_REAL, self.seconds, 1)
    return self

  def __exit__(self, *exc_info):
    if sys.platform == 'win32':
      return False
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, self.prev_handler)
    return False

# The exit status of the ``timeout`` command when the time limit expires.
TIMEOUT_STATUS = 124

# True when the collector of the C++ backend runs at every safepoint
# (SPRITE_GC_STRESS=1; see src/curryrt/graph/gc/wdgc.cpp and section 4 of
# README).  A test whose child grows a large live heap, recurses deeply, or
# must run out of memory does not end in reasonable time in that mode.
GC_STRESS = os.environ.get('SPRITE_GC_STRESS') == '1'

def skipIfGcStress(reason):
  '''Skips a test when the collector runs in stress mode.'''
  return unittest.skipIf(GC_STRESS, 'collector stress mode: ' + reason)

def expectedFailureIf(condition, reason):
  '''
  Marks a test as a known failure when ``condition`` holds, and leaves it
  alone otherwise.  ``reason`` names the defect for the reader; unittest
  reports an expected failure without one.  The condition names the setting
  with the known defect; a fix shows as an unexpected success.
  '''
  if condition:
    return unittest.expectedFailure
  return lambda f: f

def interpret_mode():
  '''
  The value of the interpreter flag ``interpret`` of this session.
  '''
  import curry
  return curry.flags['interpret']

def skipIfInterpreted(reason):
  '''
  Skips a test under the interpreter flag ``interpret`` set to 'new' or 'all'
  on the C++ backend when the test requires generated code. 'new' permits
  modules without objects and 'all' ignores objects. The prepare pass can
  supply corpus objects under 'new' (section 4 of README).
  '''
  mode = interpret_mode()
  return unittest.skipIf(
      mode in ('new', 'all'), 'interpret:%s: %s' % (mode, reason)
    )

def skipUnlessObjectsLoad(reason):
  '''
  Skips a test under the interpreter flag ``interpret`` set to 'all' on the
  C++ backend, where the loader refuses to open a compiled object
  (backends.cxx.loader): a test of curry.load, or of a saved program, which
  loads its object.  curry.save itself works under every mode.
  '''
  mode = interpret_mode()
  return unittest.skipIf(mode == 'all', 'interpret:%s: %s' % (mode, reason))

def gc_backend():
  '''
  The collector of the installed C++ runtime: 'wdgc' or 'mps' (make GC=mps).
  See config.cxx_gc.
  '''
  from curry import config
  return config.cxx_gc()

def skipUnlessGcBackend(name, reason):
  '''
  Skips a test unless the installed C++ runtime uses the collector ``name``.
  The tests of the block heap and of its collector hold for 'wdgc' alone.
  '''
  return unittest.skipUnless(
      gc_backend() == name, 'collector %s only: %s' % (name, reason)
    )

def json_module(name, value):
  '''
  A synthetic ICurry description of a module ``name`` with one public
  function, ``goal``,
  that returns the integer ``value``. Tests convert this in-memory fixture
  description to ICurry text and an image with ``write_module_image``; no
  Curry front end runs.  ``name`` may be dotted; the module then lives in a package.
  '''
  return (
      '{"__class__":"IProg","name":"%(name)s","imports":["Prelude"],"types":[]'
      ',"functions":[{"__class__":"IFunction","name":"%(name)s.goal","arity":0'
      ',"vis":{"__class__":"Public"},"needed":[],"body":{"__class__":'
      '"IFuncBody","block":{"__class__":"IBlock","vardecls":[],"assigns":[]'
      ',"stmt":'
      '{"__class__":"IReturn","expr":{"__class__":"ILit","lit":{"__class__":'
      '"IInt","value":%(value)d}}}}}}],"aliases":[]}'
    ) % {'name': name, 'value': value}

def posix_only(reason):
  """Skip tests of POSIX facilities on Windows."""
  return unittest.skipIf(sys.platform == 'win32', reason)

def windows_only(reason):
  """Skip tests of Windows facilities on other platforms."""
  return unittest.skipUnless(sys.platform == 'win32', reason)

def linux_only(reason):
  '''
  Skips a test on a platform other than Linux: one that reads /proc or an
  ELF object, or relies on a limit another kernel does not enforce.
  '''
  return unittest.skipUnless(sys.platform.startswith('linux'), reason)

def tool_command(command):
  """Invoke staged Python tools with the active Python on Windows."""
  command = list(command)
  if sys.platform == 'win32':
    name = os.path.basename(command[0])
    modules = {'sprite-exec': 'curry',
               'sprite-make': 'curry.tools.make'}
    if name in modules:
      return [sys.executable, '-m', modules[name]] + command[1:]
    if name == 'python':
      return [sys.executable] + command[1:]
  return command


def limit_prefix(address_space=None, timeout=None, kill_after=None):
  '''
  The command prefix that caps a child on this platform: ``prlimit --as=N``
  for an address space of N bytes where prlimit exists (Linux; macOS has no
  prlimit and does not enforce the limit), then the timeout command of GNU
  coreutils (``timeout``, or ``gtimeout`` from Homebrew on macOS) with
  ``-k kill_after`` when given.  A part whose tool is missing is left out.
  A caller appends its own command.
  '''
  # Windows timeout.exe waits for a key; it is not GNU timeout.
  if sys.platform == 'win32':
    return []
  prefix = []
  if address_space is not None and shutil.which('prlimit'):
    prefix += ['prlimit', '--as=%d' % address_space]
  if timeout is not None:
    for name in 'timeout', 'gtimeout':
      if shutil.which(name):
        prefix.append(name)
        if kill_after is not None:
          prefix += ['-k', str(kill_after)]
        prefix.append(str(timeout))
        break
  return prefix

_address_space_warning = False

def run_in_subprocess(code, timeout, address_space=None, input=None, text=True):
  '''
  Runs Python ``code`` in a fresh interpreter and returns the
  ``subprocess.CompletedProcess`` with the text of both output streams, or
  their bytes when ``text`` is false.  ``input`` feeds the standard input of
  the child; by default the child inherits it.

  The child runs under the ``timeout`` command, which kills it after
  ``timeout`` seconds (exit status TIMEOUT_STATUS).  ``address_space`` caps
  its virtual memory in bytes through ``prlimit`` or Linux RLIMIT_AS.
  Without a timeout tool, a timed communicate kills the process tree.
  The child inherits the environment and the working directory, so SPRITE_INTERPRETER_FLAGS selects
  the backend and CURRYPATH finds the test modules.  PYTHONIOENCODING is set
  to UTF-8, so the standard streams of a Python-backend child hold UTF-8 under
  any locale, as those of a C++-backend child do.

  Use this for a test that could spin or crash inside C++ on a regression.
  SIGALRM does not interrupt the C++ scheduler, so the ``timeout`` context
  manager cannot stop such a test, and a crash would end the test runner.
  '''
  global _address_space_warning
  prefix = limit_prefix(address_space, timeout)
  external_timeout = any(name in prefix for name in ('timeout', 'gtimeout'))
  if address_space is not None and 'prlimit' not in prefix:
    if sys.platform.startswith('linux'):
      # Execute in the child, avoiding preexec_fn in a threaded parent.
      code = ('import resource; resource.setrlimit(resource.RLIMIT_AS, '
              '(%d, %d))\n' % (address_space, address_space)) + code
    elif not _address_space_warning:
      _address_space_warning = True
      warnings.warn('test child address-space cap is unavailable on this platform',
                    RuntimeWarning, stacklevel=2)
  cmd = prefix + [sys.executable, '-B', '-c', code]
  env = dict(os.environ, PYTHONIOENCODING='utf-8')
  if external_timeout:
    kwds = {} if input is None else {'input': input}
    return subprocess.run(cmd, capture_output=True, text=text, env=env, **kwds)
  from testrunner import procs
  windows = sys.platform == 'win32'
  options = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | 0x4}
             if windows else {'start_new_session': True})
  with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE if input is not None else None,
                        text=text, env=env, **options) as proc:
    try:
      if windows:
        procs.start_windows(proc)
      try:
        stdout, stderr = proc.communicate(input=input, timeout=timeout)
        status = proc.returncode
      except subprocess.TimeoutExpired:
        if windows:
          procs.kill_session(proc.pid, leader=proc, reason='timeout')
        else:
          try:
            os.killpg(proc.pid, signal.SIGKILL)
          except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        status = TIMEOUT_STATUS
      return subprocess.CompletedProcess(cmd, status, stdout, stderr)
    finally:
      if windows:
        procs.close_windows(proc.pid)




def write_module_image(path, description, translate=True):
  """Write a synthetic translation and its image without a front end."""
  import json
  from curry.backends.cxx import image
  from curry.toolchain import _loadcurry
  def render(value):
    if isinstance(value, list):
      return '[' + ','.join(map(render, value)) + ']'
    if not isinstance(value, dict):
      return json.dumps(value)
    value = dict(value)
    cls = value.pop('__class__')
    if cls == 'IType':
      cls = 'IDataType'
    if cls == 'IDataType':
      module, _, name = value['name'].rpartition('.')
      qname = '(' + json.dumps(module) + ',' + json.dumps(name) + ',0)'
      ctors = []
      for ctor in value['constructors']:
        cm, _, cn = ctor['name'].rpartition('.')
        ctors.append('((' + json.dumps(cm) + ',' + json.dumps(cn) + ',0),'
            + str(ctor['arity']) + ')')
      return '(IDataType ' + qname + ' [' + ','.join(ctors) + '])'
    if cls == 'IProg':
      value.pop('aliases', None)
    if cls == 'IFunction' and value.get('needed') is None:
      value['needed'] = []
    if cls in ('IFunction', 'IFCall', 'ICCall', 'IFPCall', 'ICPCall', 'IConsBranch', 'ICall'):
      module, _, name = value['name'].rpartition('.')
      value['name'] = (module, name)
    args = []
    for v in value.values():
      if isinstance(v, tuple):
        args.append('(' + json.dumps(v[0]) + ',' + json.dumps(v[1]) + ',0)')
      else:
        args.append(render(v))
    return '(' + cls + (' ' + ' '.join(args) if args else '') + ')'
  try:
    text = render(json.loads(description))
  except ValueError:
    text = description
    translate = False
  icyfile = path[:-4] + '.icy'
  with open(icyfile, 'w') as stream:
    stream.write(text + '\n')
  if translate:
    search = [os.path.dirname(os.path.dirname(os.path.dirname(path)))] + raw.interp().path
    image.ensure(raw.interp(), icyfile, search)
