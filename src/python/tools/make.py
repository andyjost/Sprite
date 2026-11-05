from .. import cache, exceptions, config, interpreter, toolchain, utility
from ..interpreter import flags as _flags
from ..toolchain import (
    plans, _curry2icurry, _filenames, _findcurry, _loadcurry, _productcache
  )
from ..toolchain._makecurry import Maker, ToolchainContext
from io import StringIO
from .utility import handle_program_errors, unrst
import argparse, os, pydoc, re, shutil, subprocess, sys, tempfile, time

PROGRAM_NAME = 'sprite-make'
__all__ = ['main']

__doc__ = '''\
Executes the toolchain to compile Curry code.

This program uses timestamps and prerequisites to lazily update targets.  Each
positional argument can be a Curry module name, a Curry source file, or an
ICurry file (extension: ``.icy``).  Modules are located by searching the
CURRYPATH environment variable; the imports of a program given as a source
file are searched in the directory of the file first, as PAKCS searches, so
a program and the modules beside it need no CURRYPATH.  An ICurry file can
be translated to a module image beside it.

The targets are ``--icy`` (the translation record), ``--image`` (the
runtime module image), ``--cxx`` (generated C++) and ``--so`` (a shared
object, with extension ``.dll`` on Windows). Each target implies its prerequisites. With no target option,
the default is ``--image``. Output lives under
``<dir>/.curry/{intermediate_subdir}``; ``--output`` copies the final
product to the requested path. ``--tidy`` removes newly generated
intermediates, retaining the ICurry text required by inspection and save.

The ``--curry2icurry`` option names the route from Curry to ICurry.
``frontend`` runs the Curry front end and then the built-in translation from
FlatCurry; ``icurry`` runs the ``icurry`` program.  The default is the
value of SPRITE_CURRY2ICURRY, else the choice made by CMake (``CURRY2ICURRY_TOOL``), else
whichever tool is installed.

The ``--rewrite-flat`` option runs the step from Curry to ICurry of every
named module again, whether or not its files are current, without the
ICurry cache: the front end (which leaves a current FlatCurry file as it
is), the rewrite step, which rewrites the FlatCurry file in place when the
binding optimization replaces an equality or the set0 lift lifts a call
(``curry.toolchain.flat2icurry.rewrite_file``), and the translation.  The
option implies ``--icy``, so it stands alone;
the later steps of another target follow as usual from the new ICurry
file.  Use it on a module whose products were made before the FlatCurry
file was rewritten, so that the file on disk and the products agree; the
module must have its source.  The option runs the modules in this process
(``--jobs 1``).

The ``--jobs N`` option makes up to ``N`` modules at once.  Each module is
made by a child process that runs this program on that module alone;
``auto`` is one child per processor.  The imports of a module are made
before the module, so no two children write the files that this program
makes for one module (the ICurry, image, C++ and shared-object
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

The product cache.  The C++ backend keeps a copy of each shared object it
compiles, with the generated C++ and the ABI stamp, in a cache directory
outside the tree when ``SPRITE_PRODUCT_CACHE`` names a directory.  An entry
is found by content: the digest of the
ABI stamp, the text of the module and of the modules it imports, and the
facts that shape the generated code.  A module whose entry is in the
cache is neither generated nor compiled; its files are placed beside the
source with a stamp for this installation.  A module in the temporary
directory of the system is not cached.  At the end of a run that restored
or stored a product this program prints one line with the two counts,
``sprite-make: product cache: N restored, M stored``, unless ``-q`` was
given; under ``--jobs`` the counts of the children are summed.  See the
page on environment variables.

Products made before the rewrite.  An ICurry file translated before the
rewrite step existed is stale: the FlatCurry file beside the source holds
a Boolean equality that the binding optimization replaces, or a ``set0``
call that the set0 lift lifts, and the ICurry file lacks the result (a
pair from an older tree or from the overlay archive of the tests).  The
step from Curry to ICurry runs again for such a module, as for a changed
source.  At the end of a run that made such a module again this program
prints ``sprite-make: pre-rewrite pairs: N translated again``, unless
``-q`` was given; under ``--jobs`` the counts of the children are summed.
When the ICurry cache held the entry of the module (the test drivers keep
one), the cache writes the ICurry file and the rewrite step runs over the
FlatCurry file; the line then ends in ``, M from the ICurry cache``.  The
modules of the Curry library are not judged; their ICurry is committed.  A
FlatCurry file larger than 256 KB, or one that cannot be written again, is
not judged either, with a warning.

Environment Variables
---------------------

    CURRYPATH
        a colon-separated list of paths to search for Curry modules.  The
        directory of a program given as a source file is searched first.

    SPRITE_PRODUCT_CACHE
        the directory of the product cache; the empty string turns the
        cache off.

    SPRITE_CURRY2ICURRY
        names the route from Curry to ICurry: ``frontend`` or ``icurry``.

    SPRITE_LOG_LEVEL
        adjusts logging output.  Values are CRITICAL, ERROR,
        WARNING (default), INFO, and DEBUG.

    SPRITE_FRONTEND_WARNINGS
        set to 0 silences the warnings of the Curry front end (overlapping
        rules), which a run otherwise reports once per module through the
        log at the WARNING level.  ``-q`` silences them too.

Examples
--------

The following converts ``Peano.curry`` to the ICurry file ``Peano.icy``.  Module Peano is
found by searching CURRYPATH.  The output is placed at
``<dir>/.curry/{intermediate_subdir}/Peano.icy``, where ``<dir>`` is the directory
containing ``Peano.curry``::

    sprite-make --icy Peano.curry

The following creates a runtime module image::

    sprite-make --image Peano.curry

'''.format(
    intermediate_subdir=config.intermediate_subdir()
  , python_package_name=config.python_package_name()
  )

def main(program_name, argv):
  import json
  records = json.loads(os.environ.pop('_SPRITE_LOADER_INPUTS', '{}'))
  with _findcurry.loader_inputs(records):
    return _main(program_name, argv)


def _main(program_name, argv):
  '''
  Main function for sprite-make.
  '''
  parser = argparse.ArgumentParser(
      prog=program_name
    , description='Compile Curry modules to ICurry, images, C++ or shared objects.'
    )
  parser.add_argument(      '--curry2icurry', choices=config.CURRY2ICURRY_TOOLS, default=None, metavar='TOOL'
    , help='the route from Curry to ICurry: frontend (the Curry front end and '
           'the built-in translation) or icurry (the icurry program)')
  parser.add_argument(      '--cxx'    , action='store_true', help='make C++ files')
  parser.add_argument(      '--so'     , action='store_true'
    , help='make shared objects for the C++ backend (implies --cxx)')
  parser.add_argument('-g', '--goal'   , default=None, help='specifies the goal of a generated program')
  parser.add_argument('-i', '--icy'    , action='store_true', help='make ICY files')
  parser.add_argument(      '--jobs'   , default='1', metavar='N'
    , help='make up to N modules at once, each in a child process (auto: one '
           'per processor); the imports of a module are made first')
  parser.add_argument('-k', '--keep-going', action='store_true', help='keep working after an error')
  parser.add_argument('-M', '--man'    , action='store_true', help='show detailed usage')
  parser.add_argument('-o', '--output' , action='store', type=str, help='specify the output file')
  parser.add_argument('-q', '--quiet'  , action='store_true', help='work quietly')
  parser.add_argument(      '--rewrite-flat', action='store_true'
    , help='run the step from Curry to ICurry again, current or not: the '
           'front end, the rewrite of the FlatCurry file by the binding '
           'optimization and the set0 lift, and the translation (implies '
           '--icy; needs the source; --jobs 1)')
  parser.add_argument('-S', '--subdir' , action='store_true'
    , help='print the subdirectory to which output files are written then exit')
  parser.add_argument('-t', '--tidy'   , action='store_true'
    , help='remove intermediate files generated by this program')
  parser.add_argument('--image', action='store_true', help='make runtime module images')
  parser.add_argument('names', nargs='*', help='Curry modules or source files to process')
  parser.add_argument('--no-header'  , action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--with-rst'   , action='store_true', help=argparse.SUPPRESS)
  # A child of --jobs: it prints the counts of the product cache for the
  # parent, which sums them, whatever -q says (see cache_line).
  parser.add_argument('--child'      , action='store_true', help=argparse.SUPPRESS)
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
  if args.rewrite_flat and jobs > 1:
    sys.stderr.write(program_name + ': --rewrite-flat runs the modules in this process; use --jobs 1.\n')
    sys.exit(1)
  if args.rewrite_flat:
    # The option is the step from Curry to ICurry; it needs no other target.
    args.icy = True
  if not any([args.icy, args.image, args.cxx, args.so]):
    args.image = True
  if args.so:
    args.cxx = True
  if args.cxx:
    args.image = True
  if args.image:
    args.icy = True

  if args.goal is not None and not args.cxx:
    sys.stderr.write(
        program_name + ': (-g,--goal) is only allowed when --cxx is supplied.\n'
      )
    sys.exit(1)
  args.backend_name = 'cxx' if args.cxx else None
  kwds = dict(args._get_kwargs())
  error_handler = handle_program_errors(
      program_name
    , exit_status=None if args.keep_going else 1
    )
  # An explicit compile compiles: under the interpreter flag interpret set to
  # 'new' or 'all' the plan of an import ends at the image, and this
  # program must still write the object (the hot tier of the C++ compiler backend runs this
  # program for its background compile).
  from .. import _interpreter_
  batch = len(args.names) > 1 and (args.image or args.cxx) \
      and not args.output and not args.rewrite_flat \
      and not any(name.endswith('.icy') for name in args.names)
  interp = _interpreter_ if args.backend_name is None and not batch else \
           interpreter.Interpreter(
               flags=_flags.getflags(
                   dict(_interpreter_.flags) if args.backend_name is None else
                   {'backend': args.backend_name, 'interpret': 'off'}
                 )
             )
  with error_handler:
    plan = _buildplan(interp, **kwds)
  if error_handler.nerrors:
    # With -k the handler reports the error and goes on; without a plan
    # nothing can be made.
    sys.exit(1)
  _productcache.reset_counts()
  _curry2icurry.reset_counts()
  counts = {'restored': 0, 'stored': 0, 'refreshed': 0, 'served': 0}
  if jobs > 1:
    _make_parallel(program_name, plan, args, kwds, error_handler, jobs, counts)
  elif batch:
    graph = JobGraph(plan, config.currypath())
    for name in args.names:
      with error_handler:
        graph.add(name, is_sourcefile=name.endswith('.curry'))
    published = {}
    for job in graph.jobs:
      source = _filenames.curryfilename(job.currentfile)
      with error_handler:
        _reset_changed_imports(interp, source, published)
        before = _target_products(plan, source)
        toolchain.makecurry(plan, source,
            job.currypath, **dict(kwds, is_sourcefile=True, resolved_path=True))
        after = _target_products(plan, source)
        changed = {path for path, digest in after.items() if digest != before[path]}
        if changed:
          published.setdefault(_filenames.module_name(source), set()).update(changed)
  else:
    for index, name in enumerate(args.names):
      if index and args.cxx:
        _reset_changed_imports(interp, name)
      with error_handler:
        _make_one(program_name, plan, name, args, kwds)
  report_cache(program_name, args, counts)
  report_rewrites(program_name, args, counts)
  if error_handler.nerrors:
    sys.exit(1)

# The line about the product cache at the end of a run (see the manual).  A
# child of --jobs prints it for its parent, which sums the counts of its
# children and its own.
CACHE_LINE = re.compile(
    r'^(?P<program>\S+): product cache: (?P<restored>\d+) restored, '
    r'(?P<stored>\d+) stored$'
  )

def cache_line(program_name, counts):
  '''The line that reports ``counts`` of the product cache.'''
  return '%s: product cache: %d restored, %d stored' % (
      program_name, counts['restored'], counts['stored']
    )

def report_cache(program_name, args, counts):
  '''
  Prints the line about the product cache when this run restored or stored
  a product: the counts of this process (``_productcache.counts``) plus
  ``counts``, those of the children.  Quiet under -q, unless this process
  is a child of --jobs, whose parent reads the line.
  '''
  total = {
      key: _productcache.counts[key] + counts[key] for key in ('restored', 'stored')
    }
  if not any(total.values()):
    return
  if args.quiet and not args.child:
    return
  sys.stdout.write(cache_line(program_name, total) + '\n')
  sys.stdout.flush()

# The line about the pairs made before the binding rewrite that a run made
# again (see the manual): the pairs translated again, and the pairs the
# ICurry cache served (the clause appears when there was one).  A child of
# --jobs prints it for its parent, as it prints the line about the product
# cache.
REWRITE_LINE = re.compile(
    r'^(?P<program>\S+): pre-rewrite pairs: (?P<refreshed>\d+) translated again'
    r'(?:, (?P<served>\d+) from the ICurry cache)?$'
  )

def rewrite_line(program_name, refreshed, served=0):
  '''
  The line that reports ``refreshed`` pre-rewrite pairs translated again
  and ``served`` pairs the ICurry cache served.
  '''
  line = '%s: pre-rewrite pairs: %d translated again' % (program_name, refreshed)
  if served:
    line += ', %d from the ICurry cache' % served
  return line

def report_rewrites(program_name, args, counts):
  '''
  Prints the line about the pre-rewrite pairs when this run made one again:
  the counts of this process (``_curry2icurry.pairs_refreshed`` and
  ``pairs_served``) plus ``counts['refreshed']`` and ``counts['served']``,
  those of the children.  Quiet under -q, unless this process is a child
  of --jobs, whose parent reads the line.
  '''
  refreshed = _curry2icurry.pairs_refreshed() + counts.get('refreshed', 0)
  served = _curry2icurry.pairs_served() + counts.get('served', 0)
  if not (refreshed or served):
    return
  if args.quiet and not args.child:
    return
  sys.stdout.write(rewrite_line(program_name, refreshed, served) + '\n')
  sys.stdout.flush()

def _target_products(plan, source):
  """Observe publications of this target, including its interface records."""
  from ..backends.cxx import image
  icy = _filenames.icurryfilename(source)
  files = plan.filelist(source) + [
      icy[:-4] + suffix for suffix in ('.fint', '.icurry', '.icy.imports', '.icy.source')]
  return {os.path.realpath(path): image.digest(path) for path in files}


def _reset_changed_imports(interp, target, published=None):
  """Reset only when this target would read a replaced loaded product."""
  from ..backends.cxx import image
  if target.endswith('.curry'):
    names = imports_of(target, interp)
    generation = _findcurry.generation_for_source(target, interp)
    if generation is not None:
      names.append(generation.name)
  else:
    generation = _findcurry.loaded_generation(target, interp)
    if generation is not None:
      names = [target]
    else:
      plan = plans.makeplan(interp, plans.MAKE_ALL)
      source = next(_findcurry._modulefiles(plan, target, config.currypath()), None)
      names = imports_of(_filenames.curryfilename(source), interp) \
          if source is not None and not os.path.isdir(source) else []
  pending = [_findcurry.loaded_generation(name, interp) for name in names]
  seen = set()
  while pending:
    generation = pending.pop()
    if generation is None or id(generation) in seen:
      continue
    seen.add(id(generation))
    replaced_copy = any(path not in generation.digests
        for path in (published or {}).get(generation.name, ()))
    if replaced_copy or any(
        image.digest(path) != digest for path, digest in generation.digests.items()):
      interp.reset()
      return
    pending.extend(dep for _, dep in generation.imports if dep is not None)


def _make_one(program_name, plan, name, args, kwds):
  '''Makes one named module, source file, or ICurry file in this process.'''
  if name.endswith('.icy'):
    # Standalone ICurry need not have a Curry source or interfaces.
    _convert_icy(program_name, name, args)
    return
  # A child inherits the parent's already resolved scope.
  kwds = dict(kwds, is_sourcefile=name.endswith('.curry'))
  if getattr(args, 'child', False):
    kwds['resolved_path'] = True
  if args.rewrite_flat:
    name = _rewrite_flat(plan, name, kwds)
    if not kwds['is_sourcefile']:
      kwds['resolved_path'] = True
    kwds['is_sourcefile'] = True
  toolchain.makecurry(plan, name, config.currypath(), **kwds)

@_findcurry.with_resolution
def _rewrite_flat(plan, name, kwds):
  '''
  Runs the step from Curry to ICurry of a module again, from its source and
  without the ICurry cache (see --rewrite-flat).  The ICurry file written
  here is then the newest file of the module, and makecurry goes on from
  it.  A module without a source, or a package, is an error.
  '''
  currypath = config.currypath()
  currentfile = _findcurry.currentfile(plan, name, currypath, **kwds)
  curryfile = None if os.path.isdir(currentfile) else _filenames.curryfilename(currentfile)
  if curryfile is None or not os.path.isfile(curryfile):
    raise exceptions.CompileError(
        '--rewrite-flat needs the Curry source of %s.' % name
      )
  scope = _findcurry.program_path(name, currypath, **kwds)
  effective = _findcurry.import_path(plan.interp,
      _findcurry.imports_path(scope, **kwds))
  if effective is None:
    effective = plan.interp.path
  icyfile = toolchain.curry2icurry(
      curryfile, effective, **dict(kwds, use_cache=False))
  return _filenames.curryfilename(icyfile)

def _convert_icy(program_name, name, args):
  '''
  Converts an ICurry file to an image.  The image file is written beside the ICurry
  file and copied to the output file, if one was given.
  '''
  from .. import _interpreter_
  from ..backends.cxx import image
  from ..toolchain import _destination
  name = _destination.canonical(name)
  if args.icy and not (args.image or args.cxx):
    product = name
  else:
    product, _ = image.ensure(_interpreter_, name, config.currypath())
  if args.cxx:
    from ..backends.cxx.toolchain import ICurry2Cpp, Cpp2So
    product = ICurry2Cpp(_interpreter_)(
        _filenames.ImageProduct(product,
            _filenames.icurryfilename(product)
            if os.path.isfile(_filenames.icurryfilename(product)) else name),
        config.currypath())
    if args.so:
      product = Cpp2So(_interpreter_)(product, config.currypath())
  if args.output and os.path.abspath(args.output) != os.path.abspath(product):
    _findcurry.verify_loaded_product(product, _interpreter_)
    with ToolchainContext(product, output=args.output):
      pass

KEYWORDS = {
    'cxx' : plans.MAKE_TARGET_SOURCE
  , 'icy' : plans.MAKE_ICURRY
  , 'image': plans.MAKE_IMAGE
  , 'so'  : plans.MAKE_TARGET_OBJECT
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
    return utility.cpu_count()
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
  def __init__(self, arg, currentfile, currypath=None):
    self.arg = arg
    self.currentfile = currentfile
    self.currypath = currypath
    self.loader_inputs = dict(_findcurry._loader_inputs.get() or {})
    self.imports = []
    self.proc = None
    self.stdout = None
    self.stderr = None

  def __repr__(self):
    return 'Job(%r)' % self.arg

def imports_of(curryfile, interp=None):
  '''
  The names of the modules that the module of ``curryfile`` imports, the
  Prelude among them.  The names come from the source when it exists (a scan
  of the import declarations; see curry.cache.SourceInfo), else from the
  image file beside the products.  Nothing when neither exists.
  '''
  generation = _findcurry.generation_for_source(curryfile, interp)
  if generation is not None:
    names = [name for name, _ in generation.imports]
  elif os.path.isfile(curryfile):
    with open(curryfile, 'rb') as stream:
      names = cache.SourceInfo(curryfile, stream.read()).imports
  else:
    try:
      from ..backends.cxx import image
      names = list(image.read(_filenames.replacesuffix(curryfile, '.img'))['imports'])
    except (OSError, ValueError):
      try:
        names = list(_loadcurry.loadicurry(curryfile).imports)
      except (OSError, ValueError):
        return []
  if 'Prelude' not in names and os.path.basename(curryfile) != 'Prelude.curry':
    names.insert(0, 'Prelude')
  return names

def is_done(plan, currentfile, currypath=None):
  '''Tells whether ``currentfile`` ends ``plan``, so that nothing is to be made.'''
  if _findcurry.generation_for_source(currentfile, plan.interp) is None \
      and plan.flags & plans.MAKE_IMAGE and not os.path.isdir(currentfile) \
      and _filenames.logging_module_name(currentfile) not in config.unsupported_syslibs():
    from ..backends.cxx import image
    if image.writable(_filenames.curryfilename(currentfile)):
      try:
        source = _filenames.curryfilename(currentfile)
        header = image._check(plan.interp, source, image.filename(currentfile))
        search = _findcurry.program_path(source,
            config.currypath() if currypath is None else currypath, is_sourcefile=True)
        imports = {}
        for name in header['imports']:
          generation = _findcurry.loaded_generation(name, plan.interp)
          imports[name] = image.generation_digest(generation) if generation is not None else \
              image.digest(image.filename(_findcurry.currentfile(plan, name, search)))
        image._check(plan.interp, source, image.filename(currentfile), imports)
      except (OSError, ValueError, KeyError, exceptions.CurryError):
        return False
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
    # A program given as a source file has its directory searched first
    # (_findcurry.program_path), for its imports and theirs.
    currypath = _findcurry.program_path(
        arg, self.currypath, is_sourcefile=is_sourcefile
      )
    currentfile = _findcurry.currentfile(
        self.plan, arg, currypath, is_sourcefile=is_sourcefile
      )
    return self._visit(arg, currentfile, currypath), currentfile

  def _visit(self, arg, currentfile, currypath):
    if os.path.isdir(currentfile):
      return None
    curryfile = _filenames.curryfilename(currentfile)
    if curryfile in self._own:
      return self._own[curryfile]
    self._own[curryfile] = None
    self._deps[curryfile] = []
    waits = []
    for name in imports_of(curryfile, self.plan.interp):
      try:
        imported = _findcurry.currentfile(self.plan, name, currypath)
      except (exceptions.ModuleLookupError, exceptions.PrerequisiteError):
        continue
      if os.path.isdir(imported):
        continue
      self._visit(name, imported, currypath)
      waits.extend(self._deps[_filenames.curryfilename(imported)])
    waits = list(dict.fromkeys(waits))
    if is_done(self.plan, currentfile, currypath):
      self._deps[curryfile] = waits
      return None
    job = Job(arg, currentfile, currypath)
    job.imports = waits
    self.jobs.append(job)
    self._own[curryfile] = job
    self._deps[curryfile] = [job]
    return job

def child_command(args, job):
  '''The command that makes the module of ``job`` in a child process.'''
  cmd = [sys.executable, '-m', config.python_package_name() + '.tools.make']
  for flag in [ 'cxx', 'so', 'icy', 'image', 'keep_going', 'quiet', 'tidy' ]:
    if getattr(args, flag):
      cmd.append('--' + flag.replace('_', '-'))
  cmd.append('--child')
  if args.curry2icurry:
    cmd += ['--curry2icurry', args.curry2icurry]
  if args.goal is not None:
    cmd += ['--goal', args.goal]
  cmd.append(_filenames.curryfilename(job.currentfile))
  return cmd

def child_environment():
  '''The environment of a child: this package in front of PYTHONPATH.'''
  from ..backends.cxx import msvc
  env = msvc.environment()
  root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  path = env.get('PYTHONPATH', '')
  env['PYTHONPATH'] = root + (os.pathsep + path if path else '')
  return env

def _make_parallel(program_name, plan, args, kwds, error_handler, jobs, counts=None):
  '''
  Makes the named modules with up to ``jobs`` child processes.  An ICurry
  file is converted in this process.  With -o, the one named module is made
  in this process after its imports, as a serial run makes it.  ``counts``,
  a dict, sums the counts of the product cache the children report.
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
  if graph.jobs:
    _prepare_shared(plan)
  run_jobs(program_name, graph.jobs, jobs, args, error_handler, counts=counts)
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

def run_jobs(
    program_name, jobs, width, args, error_handler, poll_interval=0.05
  , counts=None
  ):
  '''
  Runs the children of ``jobs``, at most ``width`` at once.  A job starts
  when the jobs of its imports have ended well.  A job whose import failed
  is not started, and counts as an error.  After an error no further job
  starts unless -k was given; the running children end by themselves.  The
  output of a child is written when it ends, so the lines of one module stay
  together, less its lines about the product cache and about the
  pre-rewrite pairs, whose counts are summed into ``counts`` (a dict; see
  report_cache and report_rewrites).
  '''
  pending = list(jobs)
  running = []
  finished = set()
  failed = set()
  stop = False
  env = child_environment()
  import json
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
            , stdout=job.stdout, stderr=job.stderr,
              env=dict(env, _SPRITE_LOADER_INPUTS=json.dumps(job.loader_inputs),
                  **({'CURRYPATH': os.pathsep.join(job.currypath)}
                     if job.currypath is not None else {}))
            )
          running.append(job)
      if not running:
        break
      job = _wait_any(running, poll_interval)
      running.remove(job)
      _relay(job, counts)
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
      _relay(job, counts)
    raise

def _wait_any(running, poll_interval):
  '''Waits for the first of the running children to end and returns its job.'''
  while True:
    for job in running:
      if job.proc.poll() is not None:
        return job
    time.sleep(poll_interval)

def _relay(job, counts=None):
  '''
  Writes the output of an ended child to the streams of this process.  The
  lines of the child about the product cache (cache_line) and about the
  pre-rewrite pairs (rewrite_line) are taken out and their counts are added
  to ``counts`` when a dict is given.  A child on Windows ends its lines
  with CRLF, so the match strips both characters.
  '''
  for stream, out in [(job.stdout, sys.stdout), (job.stderr, sys.stderr)]:
    stream.seek(0)
    data = stream.read()
    stream.close()
    text = data.decode('utf-8', errors='replace')
    if out is sys.stdout and counts is not None:
      lines = []
      for line in text.splitlines(keepends=True):
        m = CACHE_LINE.match(line.rstrip('\r\n'))
        if m:
          counts['restored'] += int(m.group('restored'))
          counts['stored'] += int(m.group('stored'))
          continue
        m = REWRITE_LINE.match(line.rstrip('\r\n'))
        if m:
          counts['refreshed'] = counts.get('refreshed', 0) + int(m.group('refreshed'))
          counts['served'] = counts.get('served', 0) + int(m.group('served') or 0)
          continue
        lines.append(line)
      text = ''.join(lines)
    if text:
      out.write(text)
      out.flush()

if __name__ == '__main__':
  main(PROGRAM_NAME, sys.argv[1:])
