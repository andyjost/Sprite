from .. import cache, exceptions, config, getInterpreter, interpreter, toolchain, utility
from ..interpreter import flags as _flags
from ..toolchain import plans, _filenames, _findcurry, _loadcurry
from ..toolchain._makecurry import Maker, ToolchainContext
from io import StringIO
from .utility import handle_program_errors, unrst
import argparse, os, pydoc, shutil, subprocess, sys, tempfile, time

PROGRAM_NAME = 'sprite-make'
__all__ = ['main']

__doc__ = '''\
Executes the toolchain to compile Curry code.

This program uses timestamps and prerequisites to lazily update targets.  Each
positional argument can be a Curry module name, a Curry source file, or an
ICurry file (extension: ``.icy``).  Modules are located by searching the
CURRYPATH environment variable.  An ICurry file can only be converted to JSON;
the JSON file is written beside it.

Three target formats are supported.  Curry-formatted ICurry (extension:
``.icy``) is generated with the ``-i,--icy`` option.  These files can be read
into Curry programs using the standard module ICurry.Files.readICurry.

JSON-formatted ICurry (extension: ``.json``) is generated with the
``-j,--json`` option.  This format is more suitable when a Curry interpreter is
not available.  Sprite only reads the JSON format.  Note that an ICY file is
the prerequisite of JSON, meaning that ``--json`` implies ``--icy``.

Python (extension: ``.py``) is generated with the ``-p,--py,--python`` option.
This implies both ``--json`` and ``--icy``.  The generated file can be imported
as a regular Python module, loaded via the Python API with
:func:`{python_package_name}.load` or executed from the command line.  By default,
running the file imports the module but does nothing else.  Supply ``-g`` to name a
goal.  The bytecode cache of the generated file is written beside it, under
``__pycache__``, so that the first load does not compile the source.

C++ (extension: ``.cpp``) is generated with the ``--cxx`` option, which implies
``--json`` and ``--icy``.  The shared object of the C++ backend (extension:
``.so``) is generated with the ``--so`` option, which implies ``--cxx`` and
needs the C++ compiler that Sprite was configured with.  The installation
procedure uses ``--py`` and ``--so`` to build the Curry library for both
backends.

Following the conventions of other Curry systems, output files are by default
written to ``<dir>/.curry/{intermediate_subdir}``, where ``<dir>`` is the
directory containing the source code.  For example, a curry file
``/path/to/A.curry`` gives rise to
``/path/to/.curry/{intermediate_subdir}/A.icy`` and
``/path/to/.curry/{intermediate_subdir}/A.json``.  The ``-o,--output`` option
can be used to specify the output file.

The ``-c,--compact`` option causes JSON output to be compacted by removing
insignificant whitespace.  Compacted JSON is less human-readable but smaller.

The ``-t,--tidy`` option removes intermediate files generated in the
compilation process.

The ``-z,--zip`` option causes JSON output to be compressed, in which case a
``.z`` extension is appended to the JSON file.  JSON that is both compacted and
zipped is often smaller than JSON that is only zipped.

The ``--curry2icurry`` option names the route from Curry to ICurry.
``frontend`` runs the Curry front end and then the built-in translation from
FlatCurry; ``icurry`` runs the ``icurry`` program.  The default is the
value of SPRITE_CURRY2ICURRY, else the choice made by ``configure``, else
whichever tool is installed.

The ``--jobs N`` option makes up to ``N`` modules at once.  Each module is
made by a child process that runs this program on that module alone;
``auto`` is one child per processor.  The imports of a module are made
before the module, so no two children write the files that this program
makes for one module (the ICurry, JSON, Python, C++ and shared-object
files).  A module whose files are current gets no child.  The order does
not cover the interface files of the Curry front end (``.fint``, ``.fcy``):
the front end writes those of an import on its own when they are missing,
so two children whose modules import one module without them write them at
once.  Run the front-end step of such a tree (products copied without
their interface files) with ``--jobs 1``.  Before the children start, this
process builds the precompiled header of the C++ backend when it is
missing, so the children find it.  The option covers the modules named on
the command line and the modules they import.  The installation procedure
passes the job count of ``make``.

Environment Variables
---------------------

    CURRYPATH
        a colon-separated list of paths to search for Curry modules.

    SPRITE_CURRY2ICURRY
        names the route from Curry to ICurry: ``frontend`` or ``icurry``.

    SPRITE_LOG_LEVEL
        adjusts logging output.  Values are CRITICAL, ERROR,
        WARNING (default), INFO, and DEBUG.

Examples
--------

The following converts ``A.curry`` to the ICurry file ``A.icy``.  Module A is
found by searching CURRYPATH.  The output is placed at
``<dir>/.curry/{intermediate_subdir}/A.icy``, where ``<dir>`` is the directory
containing ``A.curry``::

    % curry-make --icurry A.curry

The following creates a compacted, zipped JSON file::

    % curry-make --json -czt /path/to/A.curry

The output is written to ``/path/to/.curry/{intermediate_subdir}/A.json.z``.
The intermediate file ``/path/to/.curry/{intermediate_subdir}/A.icy`` will be
removed unless it was up-to-date prior to the command running.

The following compiles the Curry code in ``A.curry`` to a Python script named
``A.py`` that evaluates ``'A.main'``::

    % curry-make --py A.curry -g main -o A.py

'''.format(
    intermediate_subdir=config.intermediate_subdir()
  , python_package_name=config.python_package_name()
  )

def main(program_name, argv):
  '''
  Main function for sprite-make.
  '''
  parser = argparse.ArgumentParser(
      prog=program_name
    , description='Make ICurry files.'
    )
  # E.g., sprite-make --icurry Prelude --json Nat
  parser.add_argument('-c', '--compact', action='store_true', help='compact JSON output')
  parser.add_argument(      '--curry2icurry', choices=config.CURRY2ICURRY_TOOLS, default=None, metavar='TOOL'
    , help='the route from Curry to ICurry: frontend (the Curry front end and '
           'the built-in translation) or icurry (the icurry program)')
  parser.add_argument(      '--cxx'    , action='store_true', help='make C++ files')
  parser.add_argument(      '--so'     , action='store_true'
    , help='make shared objects for the C++ backend (implies --cxx)')
  parser.add_argument('-g', '--goal'   , default=None, help='specifies the goal in --python mode')
  parser.add_argument('-i', '--icy'    , action='store_true', help='make ICY files')
  parser.add_argument('-j', '--json'   , action='store_true', help='make JSON files')
  parser.add_argument(      '--jobs'   , default='1', metavar='N'
    , help='make up to N modules at once, each in a child process (auto: one '
           'per processor); the imports of a module are made first')
  parser.add_argument('-k', '--keep-going', action='store_true', help='keep working after an error')
  parser.add_argument('-M', '--man'    , action='store_true', help='show detailed usage')
  parser.add_argument('-o', '--output' , action='store', type=str, help='specify the output file')
  parser.add_argument('-p', '--py', '--python', action='store_true', help='make Python files')
  parser.add_argument('-q', '--quiet'  , action='store_true', help='work quietly')
  parser.add_argument('-S', '--subdir' , action='store_true'
    , help='print the subdirectory to which output files are written then exit')
  parser.add_argument('-t', '--tidy'   , action='store_true'
    , help='remove intermediate files generated by this program')
  parser.add_argument('-z', '--zip'    , action='store_true'
    , help='zip JSON output with zlib (adds .z extension)')
  parser.add_argument('names', nargs='*', help='Curry modules or source files to process')
  parser.add_argument('--no-header'  , action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--with-rst'   , action='store_true', help=argparse.SUPPRESS)
  args = parser.parse_args(argv)

  if args.man:
    mantext = StringIO()
    if not args.no_header:
      parser.print_usage(file=mantext)
      mantext.write('\n')
    mantext.write(__doc__ if args.with_rst else unrst(__doc__))
    pydoc.getpager()(mantext.getvalue())
    return
  else:
    del args.man

  if args.subdir:
    sys.stdout.write(os.path.join('.curry', config.intermediate_subdir()))
    return
  else:
    del args.subdir

  jobs = parse_jobs(args.jobs)
  if jobs is None:
    sys.stderr.write(
        program_name + ': --jobs should be a count or auto, not %r.\n' % args.jobs
      )
    sys.exit(1)
  del args.jobs

  if len(args.names) > 1 and args.output:
    sys.stderr.write(program_name + ': -o,--output cannot be used with multiple input files.\n')
    sys.exit(1)
  if not any([args.icy, args.json, args.py, args.cxx, args.so]):
    sys.stderr.write(
        program_name + ': at least one of (-i,--icy) or (-j,--json) or --cxx or '
                       '--so or (-p,--py,--python) must be supplied.\n'
      )
    sys.exit(1)
  if args.so:
    args.cxx = True
  if args.py or args.cxx:
    args.json = True
  if args.json:
    args.icy = True

  CODEGEN_OPTIONS = 'py', 'cxx'
  num_codegens = sum(getattr(args, opt) for opt in CODEGEN_OPTIONS)
  if args.goal is not None and num_codegens == 0:
    sys.stderr.write(
        program_name + ': (-g,--goal) is only allowed when at least one of '
                       '(-p,--py,--python) or --cxx is supplied.\n'
      )
    sys.exit(1)
  elif num_codegens > 1:
    sys.stderr.write(
        program_name + ': at most one of (-p,--py,--python) or --cxx can be '
                       'supplied.\n'
      )
    sys.exit(1)
  args.backend_name = 'py' if args.py else 'cxx' if args.cxx else None
  kwds = dict(args._get_kwargs())
  error_handler = handle_program_errors(
      program_name
    , exit_status=None if args.keep_going else 1
    )
  # An explicit compile compiles: under the interpreter flag interpret set to
  # 'new' or 'tiered' the plan of an import ends at the JSON, and this
  # program must still write the object (the background compile of tiered
  # execution runs this program).
  interp = getInterpreter() if args.backend_name is None else \
           interpreter.Interpreter(
               flags=_flags.getflags(
                   {'backend': args.backend_name, 'interpret': 'off'}
                 )
             )
  with error_handler:
    plan = _buildplan(interp, **kwds)
  if error_handler.nerrors:
    # With -k the handler reports the error and goes on; without a plan
    # nothing can be made.
    sys.exit(1)
  if jobs > 1:
    _make_parallel(program_name, plan, args, kwds, error_handler, jobs)
  else:
    for name in args.names:
      with error_handler:
        _make_one(program_name, plan, name, args, kwds)
  if error_handler.nerrors:
    sys.exit(1)

def _make_one(program_name, plan, name, args, kwds):
  '''Makes one named module, source file, or ICurry file in this process.'''
  if name.endswith('.icy'):
    # A committed ICurry file.  The JSON is written beside it, so the Curry
    # library can be rebuilt without icurry.
    _convert_icy(program_name, name, args)
    return
  kwds = dict(kwds, is_sourcefile=name.endswith('.curry'))
  file_out = toolchain.makecurry(plan, name, config.currypath(), **kwds)
  _ensure_bytecode(args, file_out)

def _ensure_bytecode(args, file_out):
  '''
  Writes the bytecode cache of a Python file that was current already and
  lacks it (an installation from before the cache was written).
  '''
  if args.py and file_out.endswith('.py'):
    from ..backends.py.toolchain import ensure_bytecode
    ensure_bytecode(file_out)

def _convert_icy(program_name, name, args):
  '''
  Converts an ICurry file to JSON.  The JSON file is written beside the ICurry
  file and copied to the output file, if one was given.
  '''
  if not args.json or args.py or args.cxx:
    raise exceptions.CompileError(
        '%s: an .icy file can only be converted to JSON (-j,--json).'
            % program_name
      )
  jsonfile = toolchain.icurry2json(
      name, config.currypath(), compact=args.compact, zip=args.zip
    )
  if args.output:
    if not (os.path.exists(args.output) and
            os.path.samefile(args.output, jsonfile)):
      shutil.copy(jsonfile, args.output)

KEYWORDS = {
    'cxx' : plans.MAKE_TARGET_SOURCE
  , 'icy' : plans.MAKE_ICURRY
  , 'json': plans.MAKE_JSON
  , 'py'  : plans.MAKE_TARGET_SOURCE
  , 'so'  : plans.MAKE_TARGET_OBJECT
  , 'zip' : plans.ZIP_JSON
  }

def _buildplan(interp, **kwds):
  plan_flags = 0
  for kw in KEYWORDS:
    if kwds.get(kw, False):
      plan_flags |= KEYWORDS[kw]
  return plans.makeplan(interp, plan_flags)

def parse_jobs(text):
  '''
  The job count that ``--jobs`` names: a positive count, or ``auto`` for one
  job per processor.  None for any other text.
  '''
  if text == 'auto':
    return os.process_cpu_count() or 1
  try:
    count = int(text)
  except ValueError:
    return None
  return count if count > 0 else None

# The parallel run
# ================
# Under --jobs N the modules are made by child processes, each running this
# program on one module.  The order follows the imports: the interpreter
# imports the imports of a module before the module, and an import whose
# files are stale is made on the spot (see curry.interpreter.import_).  So
# two children that import one stale module would both write its files.
# This process resolves the named modules and the closure of their imports
# first, finds the modules whose files need work, and starts a child for one
# of them only when the children of its stale imports have ended.

class Job(object):
  '''
  A module of a parallel run: the argument that names it, its current file,
  the jobs of the stale modules it imports (directly, or through imports
  whose files are current), and the child that makes it.
  '''
  def __init__(self, arg, currentfile):
    self.arg = arg
    self.currentfile = currentfile
    self.imports = []
    self.proc = None
    self.stdout = None
    self.stderr = None

  def __repr__(self):
    return 'Job(%r)' % self.arg

def imports_of(curryfile):
  '''
  The names of the modules that the module of ``curryfile`` imports, the
  Prelude among them.  The names come from the source when it exists (a scan
  of the import declarations; see curry.cache.SourceInfo), else from the
  JSON file beside the products.  Nothing when neither exists.
  '''
  if os.path.isfile(curryfile):
    with open(curryfile, 'rb') as stream:
      names = cache.SourceInfo(curryfile, stream.read()).imports
  else:
    jsonfiles = [f for f in _filenames.jsonfilenames(curryfile) if os.path.isfile(f)]
    if not jsonfiles:
      return []
    try:
      names = list(_loadcurry.loadjson(jsonfiles[0]).imports)
    except Exception:
      # The child that makes the module reports the unreadable file.
      return []
  if 'Prelude' not in names and os.path.basename(curryfile) != 'Prelude.curry':
    names.insert(0, 'Prelude')
  return names

def is_done(plan, currentfile):
  '''Tells whether ``currentfile`` ends ``plan``, so that nothing is to be made.'''
  return Maker(plan, ToolchainContext(currentfile=currentfile), None, None, {}).done

class JobGraph(object):
  '''
  The jobs of a parallel run, in the order they were found: a module after
  the modules it imports.
  '''
  def __init__(self, plan, currypath):
    self.plan = plan
    self.currypath = currypath
    self.jobs = []
    # By the Curry file of a visited module: its own job (None when its files
    # are current, or while it is under visit), and the jobs an importer of
    # the module waits for: its own job when its files are stale, else the
    # jobs of its stale imports.  A module under visit has no job yet, so a
    # cycle (an import declaration inside a comment, say) adds no edge.
    self._own = {}
    self._deps = {}

  def add(self, arg, is_sourcefile=False):
    '''
    Adds the job of a named module and the jobs of its stale imports.
    Returns the job, or None when the files of the module are current or
    the name is a package, with the current file of the module.  Raises
    what the lookup of the module raises.
    '''
    currentfile = _findcurry.currentfile(
        self.plan, arg, self.currypath, is_sourcefile=is_sourcefile
      )
    return self._visit(arg, currentfile), currentfile

  def _visit(self, arg, currentfile):
    if os.path.isdir(currentfile):
      return None
    curryfile = _filenames.curryfilename(currentfile)
    if curryfile in self._own:
      return self._own[curryfile]
    self._own[curryfile] = None
    self._deps[curryfile] = []
    waits = []
    for name in imports_of(curryfile):
      try:
        imported = _findcurry.currentfile(self.plan, name, self.currypath)
      except (exceptions.ModuleLookupError, exceptions.PrerequisiteError):
        continue
      if os.path.isdir(imported):
        continue
      self._visit(name, imported)
      waits.extend(self._deps[_filenames.curryfilename(imported)])
    waits = list(dict.fromkeys(waits))
    if is_done(self.plan, currentfile):
      self._deps[curryfile] = waits
      return None
    job = Job(arg, currentfile)
    job.imports = waits
    self.jobs.append(job)
    self._own[curryfile] = job
    self._deps[curryfile] = [job]
    return job

def child_command(args, job):
  '''The command that makes the module of ``job`` in a child process.'''
  cmd = [sys.executable, '-m', config.python_package_name() + '.tools.make']
  for flag in [ 'compact', 'cxx', 'so', 'icy', 'json', 'keep_going', 'py'
              , 'quiet', 'tidy', 'zip' ]:
    if getattr(args, flag):
      cmd.append('--' + flag.replace('_', '-'))
  if args.curry2icurry:
    cmd += ['--curry2icurry', args.curry2icurry]
  if args.goal is not None:
    cmd += ['--goal', args.goal]
  cmd.append(job.arg)
  return cmd

def child_environment():
  '''The environment of a child: this package in front of PYTHONPATH.'''
  env = dict(os.environ)
  root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  path = env.get('PYTHONPATH', '')
  env['PYTHONPATH'] = root + (os.pathsep + path if path else '')
  return env

def _make_parallel(program_name, plan, args, kwds, error_handler, jobs):
  '''
  Makes the named modules with up to ``jobs`` child processes.  An ICurry
  file is converted in this process.  With -o, the one named module is made
  in this process after its imports, as a serial run makes it.
  '''
  graph = JobGraph(plan, config.currypath())
  deferred = []
  for name in args.names:
    with error_handler:
      if name.endswith('.icy'):
        _make_one(program_name, plan, name, args, kwds)
        continue
      job, currentfile = graph.add(name, is_sourcefile=name.endswith('.curry'))
      if args.output:
        deferred.append(name)
        if job is not None:
          graph.jobs.remove(job)
      elif job is None:
        _ensure_bytecode(args, currentfile)
  if graph.jobs:
    _prepare_shared(plan)
  run_jobs(program_name, graph.jobs, jobs, args, error_handler)
  if error_handler.nerrors and not args.keep_going:
    return
  for name in deferred:
    with error_handler:
      _make_one(program_name, plan, name, args, kwds)

def _prepare_shared(plan):
  '''
  Builds, once in this process, what every child would otherwise build on
  its own: the precompiled header of the C++ backend, when the plan compiles
  objects and the header is missing or stale.  A child finds it current.
  Without this, N children over a tree without the header compile it N
  times (os.replace keeps the tree correct, so the cost is time alone).
  '''
  for stage in plan.stages:
    prepare = getattr(stage.step, 'prepare_header', None)
    if prepare is not None:
      prepare()

def run_jobs(program_name, jobs, width, args, error_handler, poll_interval=0.05):
  '''
  Runs the children of ``jobs``, at most ``width`` at once.  A job starts
  when the jobs of its imports have ended well.  A job whose import failed
  is not started, and counts as an error.  After an error no further job
  starts unless -k was given; the running children end by themselves.  The
  output of a child is written when it ends, so the lines of one module stay
  together.
  '''
  pending = list(jobs)
  running = []
  finished = set()
  failed = set()
  stop = False
  env = child_environment()
  try:
    while pending or running:
      for job in list(pending):
        if stop or len(running) >= width:
          break
        if any(dep in failed for dep in job.imports):
          pending.remove(job)
          failed.add(job)
          error_handler.nerrors += 1
          sys.stderr.write(
              '%s: %s was not made because an import failed.\n'
                  % (program_name, job.arg)
            )
        elif all(dep in finished for dep in job.imports):
          pending.remove(job)
          job.stdout = tempfile.TemporaryFile()
          job.stderr = tempfile.TemporaryFile()
          job.proc = subprocess.Popen(
              child_command(args, job), stdin=subprocess.DEVNULL
            , stdout=job.stdout, stderr=job.stderr, env=env
            )
          running.append(job)
      if not running:
        break
      job = _wait_any(running, poll_interval)
      running.remove(job)
      _relay(job)
      if job.proc.returncode == 0:
        finished.add(job)
      else:
        failed.add(job)
        error_handler.nerrors += 1
        stop = not args.keep_going
  except BaseException:
    for job in running:
      job.proc.terminate()
    for job in running:
      job.proc.wait()
      _relay(job)
    raise

def _wait_any(running, poll_interval):
  '''Waits for the first of the running children to end and returns its job.'''
  while True:
    for job in running:
      if job.proc.poll() is not None:
        return job
    time.sleep(poll_interval)

def _relay(job):
  '''Writes the output of an ended child to the streams of this process.'''
  for stream, out in [(job.stdout, sys.stdout), (job.stderr, sys.stderr)]:
    stream.seek(0)
    data = stream.read()
    stream.close()
    if data:
      out.write(data.decode('utf-8', errors='replace'))
      out.flush()

if __name__ == '__main__':
  main(PROGRAM_NAME, sys.argv[1:])
