'''
The route from Curry to ICurry through the Curry front end.

The front end translates a module and its imports to FlatCurry.  For a
module ``M`` it writes ``M.fcy``, the interface ``M.fint``, and ``M.icurry``
under ``.curry/<subdir>/`` beside the source, where ``<subdir>`` names the
front end (see :func:`config.frontend_subdir`).  The same run writes the
interfaces of the imports beside their sources.  Then
:mod:`curry.toolchain.flat2icurry` translates the FlatCurry to ICurry.  The
``icurry`` program runs the same front end, so its run leaves the same files
(see :func:`interfacefile`).

The command runs in the directory of the module and names the module by its
file name, as ``icurry`` does, so the output lands in the same places.

The translation runs with ``bindingopt=True``: the binding optimization of
:mod:`curry.toolchain.flat2icurry.bindingopt` turns the Boolean equalities
of the conditions into equational constraints, as the preprocessing of
PAKCS does before it compiles a FlatCurry file.  A program that binds free
variables through ``==`` in a guard then runs as it runs under PAKCS.  The
``icurry`` route does not apply it; its ICurry is the program as written.

The translation runs with ``icurry_compat=False``.  ``icurry`` 3.1.0 loses
the bindings of a let or free declaration under a type annotation at the
root of a rule, and the program then fails at run time.  The port looks
through the annotation here.  Only the oracle tests keep the defect.  Two
probe modules of the oracle hold the construct, and their output differs
from the files ``icurry`` wrote: TypedRoot, and Externals, where
``failed :: Int`` becomes ``IExempt`` instead of a call of ``failed``.  No
other file of the oracle changes.
'''

from .. import config
from . import _system, flat2icurry
from ..exceptions import CompileError
from ..utility import curryname
import logging, os, shlex

__all__ = [
    'QUIET_FLAGS', 'command', 'curry2flat', 'curry2icurry', 'flat2icy'
  , 'flatcurryfile', 'interfacefile', 'searchdirs'
  ]
logger = logging.getLogger(__name__)

# The options that silence the front end.  They are the ones icurry passes in
# quiet mode.
QUIET_FLAGS = ['--no-verb', '--no-warn', '--no-overlap-warn']

def searchdirs(file_in, currypath):
  '''
  The directories in which the front end and the translation look for
  modules: the directory of ``file_in``, the Curry path, and the system
  library, without repeats.
  '''
  moduledir = os.path.dirname(os.path.abspath(file_in))
  dirs = [moduledir] + curryname.makeCurryPath(currypath)
  dirs.append(config.system_curry_path())
  seen = set()
  unique = []
  for dirname in dirs:
    if dirname not in seen:
      seen.add(dirname)
      unique.append(dirname)
  return unique

def flatcurryfile(file_in):
  '''The FlatCurry file that the front end writes for ``file_in``.'''
  path, name = os.path.split(os.path.abspath(file_in))
  assert name.endswith('.curry')
  return os.path.join(
      path, '.curry', config.frontend_subdir(), name[:-len('.curry')] + '.fcy'
    )

def interfacefile(file_in, suffix):
  '''
  The interface file with ``suffix`` (``.fint`` or ``.icurry``; see
  ``cache.INTERFACE_SUFFIXES``) that the front end writes for ``file_in``,
  beside its FlatCurry file.
  '''
  fcyfile = flatcurryfile(file_in)
  return fcyfile[:-len('.fcy')] + suffix

def command(file_in, currypath, quiet=False):
  '''
  The front-end command line for the Curry file ``file_in``.  The output
  directory is relative, so it is resolved against the directory of each
  module the front end compiles.  A front end that is not configured raises
  ``CompileError``.
  '''
  if config.curry_frontend() is None:
    raise CompileError(
        'the Curry front end is not configured; rerun configure, or set '
        'SPRITE_CURRY2ICURRY=icurry to use icurry'
      )
  name = os.path.basename(file_in)
  assert name.endswith('.curry')
  cmd = [
      config.curry_frontend(), '--flat'
    , '-o', os.path.join('.curry', config.frontend_subdir())
    ]
  if quiet:
    cmd.extend(QUIET_FLAGS)
  cmd.extend(shlex.split(config.frontend_flags()))
  for dirname in searchdirs(file_in, currypath):
    cmd.extend(['-i', dirname])
  cmd.append(name[:-len('.curry')])
  return cmd

def curry2flat(file_in, currypath, quiet=False):
  '''
  Runs the front end on ``file_in``.  Returns the name of the FlatCurry file.
  A failure of the front end raises ``CompileError`` with its messages.
  '''
  cmd = command(file_in, currypath, quiet)
  logger.debug('Command: %s', ' '.join(cmd))
  moduledir = os.path.dirname(os.path.abspath(file_in))
  stdout = _system.pexec(cmd, cwd=moduledir)
  if stdout:
    logger.debug('Front end output:\n%s', stdout)
  fcyfile = flatcurryfile(file_in)
  if not os.path.isfile(fcyfile):
    raise CompileError('the front end did not write %s' % fcyfile)
  return fcyfile

def flat2icy(fcyfile, file_out, searchdirs):
  '''
  Translates the FlatCurry file ``fcyfile`` to ICurry and writes ``file_out``.
  The interfaces of the imports are searched under ``searchdirs``.
  '''
  finder = flat2icurry.InterfaceFinder(searchdirs, [config.frontend_subdir()])
  iprog = flat2icurry.translate_file(
      fcyfile, finder, icurry_compat=False, bindingopt=True
    )
  flat2icurry.write_icurry(iprog, file_out)

def curry2icurry(file_in, file_out, currypath, quiet=False):
  '''
  Converts the Curry file ``file_in`` to the ICurry file ``file_out``.
  '''
  fcyfile = curry2flat(file_in, currypath, quiet)
  flat2icy(fcyfile, file_out, searchdirs(file_in, currypath))
