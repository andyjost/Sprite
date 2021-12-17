from ..exceptions import ModuleLookupError, PrerequisiteError
from .. import config
from . import _filenames
from ..tools.utility import make_exception
from ..utility import curryname, filesys, formatDocstring
import logging, os

__all__ = ['currentfile']
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

@formatDocstring(config.python_package_name())
def currentfile(
    name, currypath, is_sourcefile=False, plan=None, **ignored
  ):
  '''
  Finds the newest prerequisite along the Curry build pipeline.

  The file returned is the newest among the Curry source file (suffix: .curry),
  the ICurry file (suffix: .icy), and the JSON file (suffix: .json or .json.z).

  Args:
    name:
        The module, source file, or package name.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').
    is_sourcefile:
        Indicates whether to interpret the name as a source file.  If True, the
        name should end with extension .curry.  Otherwise the name is
        interpreted as a module or package name.
    plan:
        The compilation :class:`plan <{0}.toolchain.plan.Plan>`  This indicates
        which files to consider as prerequisites.  If None, a default plan

  Raises:
    ModuleLookupError: the module was not found.

  Returns:
    The name of an ICurry-JSON file (suffix: .json), Curry source file (suffix:
    .curry), Python file (suffix: .py), or directory.  The JSON name may have
    an additional .z suffix.  The JSON file is returned if it is up-to-date,
    otherwise, the Curry file is returned if it exists.  If neither of those
    applies, the package directory name is returned, if it exists.
  '''
  if plan is None:
    from .plans import Plan
    plan = Plan()
  if not is_sourcefile:
    # If name is a module name, then search CURRYPATH for the source file or
    # (possibly zipped) JSON and set it as the name.  source file and
    # is_sourcefile=True.  It is acceptable to use a JSON file that has no
    # corresponding source file.  This means a library could be installed as
    # JSON only, without needing to install its source.
    curryname.validateModulename(name)
    # Search for the JSON file first, then ICurry, then .curry.
    parts = name.split('.')
    package_path, name = os.sep.join(parts[:-1]), parts[-1]
    search_names = [
        os.path.join(package_path, '.curry', SUBDIR, name + suffix)
            for suffix in reversed(plan.suffixes[1:])
            #             [.json[.z], .icy]
      ]
    search_names += [os.path.join(package_path, name + '.curry')]
    search_names += [os.path.join(package_path, name, '')]
    files = filesys.findfiles(currypath, search_names)
    try:
      name = next(files)
    except StopIteration:
      raise make_exception(
          ModuleLookupError
        , 'Curry module %r not found.' % name
        , hint=lambda:_fileNotFoundHint(name)
        )
    if os.path.isdir(name):
      return name
    else:
      name = _filenames.curryfilename(name)

  # Find the newest prerequisite.
  curryfile = name
  if not curryfile.endswith('.curry'):
    raise ModuleLookupError('expected .curry extension in %r' % curryfile)
  curryfile = os.path.abspath(curryfile)
  filelist = [curryfile]
  if plan.do_icy:
    icyfile = _filenames.icurryfilename(curryfile)
    filelist += [icyfile]
  if plan.do_json:
    filelist += _filenames.jsonfilenames(curryfile, set(plan.suffixes))
  prereq = os.path.abspath(filesys.newest(filelist))
  if not os.path.exists(prereq):
    # If there is no prerequisite, then there is no Curry file or any of its
    # derivatives (it could be OK to ship Curry files with no source).  Report
    # this as there being no source file.
    assert not os.path.exists(curryfile)
    raise PrerequisiteError('Curry file does not exist: %r' % curryfile)
  if not (os.access(prereq, os.R_OK) and os.path.isfile(prereq)):
    raise PrerequisiteError(
        'prerequisite is the wrong type or is unreadable: %r' % prereq
      )
  logger.debug('Prerequisite for compilation of %r is %r', name, prereq)
  return prereq

# Keyword defaults.
def _fileNotFoundHint(name, **kwds):
  if os.path.exists(name + '.curry'):
    return 'Perhaps you meant "%s.curry"?' % name

