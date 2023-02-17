from .. import config, getInterpreter, interpreter, toolchain, utility
from ..interpreter import flags as _flags
from ..toolchain import plans
from six.moves import cStringIO as StringIO
from .utility import handle_program_errors, unrst
import argparse, os, pydoc, sys

PROGRAM_NAME = 'sprite-make'
__all__ = ['main']

__doc__ = '''\
Executes the toolchain to compile Curry code.

This program uses timestamps and prerequisites to lazily update targets.  Each
positional argument can be a Curry module name or Curry source file.  Modules
are located by searching the CURRYPATH environment variable.

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
goal.

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

Environment Variables
---------------------

    CURRYPATH
        a colon-separated list of paths to search for Curry modules.

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
  parser.add_argument(      '--cxx'    , action='store_true', help='make C++ files')
  parser.add_argument('-g', '--goal'   , default=None, help='specifies the goal in --python mode')
  parser.add_argument('-i', '--icy'    , action='store_true', help='make ICY files')
  parser.add_argument('-j', '--json'   , action='store_true', help='make JSON files')
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

  if len(args.names) > 1 and args.output:
    sys.stderr.write(program_name + ': -o,--output cannot be used with multiple input files.\n')
    sys.exit(1)
  if not any([args.icy, args.json, args.py, args.cxx]):
    sys.stderr.write(
        program_name + ': at least one of (-i,--icy) or (-j,--json) or --cxx or '
                       '(-p,--py,--python) must be supplied.\n'
      )
    sys.exit(1)
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
  interp = getInterpreter() if args.backend_name is None else \
           interpreter.Interpreter(
               flags=_flags.getflags({'backend': args.backend_name})
             )
  for name in args.names:
    kwds['is_sourcefile'] = name.endswith('.curry')
    with error_handler:
      plan = _buildplan(interp, **kwds)
      toolchain.makecurry(plan, name, config.currypath(), **kwds)
  if error_handler.nerrors:
    sys.exit(1)

KEYWORDS = {
    'cxx' : plans.MAKE_TARGET_SOURCE
  , 'icy' : plans.MAKE_ICURRY
  , 'json': plans.MAKE_JSON
  , 'py'  : plans.MAKE_TARGET_SOURCE
  , 'zip' : plans.ZIP_JSON
  }

def _buildplan(interp, **kwds):
  plan_flags = 0
  for kw in KEYWORDS:
    if kwds.get(kw, False):
      plan_flags |= KEYWORDS[kw]
  return plans.makeplan(interp, plan_flags)

if __name__ == '__main__':
  main(PROGRAM_NAME, sys.argv[1:])
