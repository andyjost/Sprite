from ..generic.toolchain import Json2TargetSource
from ... import config, exceptions
from ...objects.handle import getHandle
from ...utility import curryname
from ...toolchain import plans, _filenames, _loadcurry, _system
import logging, os, re

logger = logging.getLogger(__name__)

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Cpp(interp)
  skeleton.append((plans.MAKE_TARGET_OBJECT, ['.cpp'], Cpp2So(interp)))
  skeleton.append((plans.UNCONDITIONAL, ['.so'] , None))

class Json2Cpp(Json2TargetSource):
  NAME = 'json2cpp'
  SUFFIX = '.cpp'

class Cpp2So(object):
  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return 'cpp2so'

  IMPORT_PAT = re.compile(r'// IMPORTS: (.*)')
  def _importedModules(self, file_in):
    '''
    Returns a list containing the full names of all modules imported by the
    specified .cpp file.  This information is stored in a comment near the top
    of the file.
    '''
    with open(file_in, 'r') as stream:
      for line in stream:
        m = re.match(self.IMPORT_PAT, line)
        if m:
          return [name for name in m.group(1).split() if name]
      else:
        raise exceptions.PrerequisiteError(
            'Cannot find IMPORTS list in %r' % file_in
          )

  def _sofilename(self, modulename):
    '''
    Gets the name of the .so file implementing the given module.
    '''
    assert modulename in self.interp.modules
    module = self.interp.modules[modulename]
    h = getHandle(module)
    sofilename = h.sofilename
    if sofilename is None:
        raise exceptions.PrerequisiteError(
            'No .so filename for module %r' % h.fullname
          )
    return sofilename

  def _dependencies(self, file_in):
    '''
    Generates the .so files the specified .cpp file depends on.  They are added
    to the link line so that ldd will automaticall load the correct modules.
    '''
    for modulename in self._importedModules(file_in):
      yield self._sofilename(modulename)

  def _compileCommand(self, file_in, file_out):
    yield config.cxx_tool()
    yield '-I%s' % config.installed_path('include')
    yield '-shared'
    yield '-fPIC'
    yield '-std=c++17'
    if self.interp.flags['debug']:
      yield '-O0'
      yield '-g'
    else:
      yield '-O3'
    for flag in os.environ.get('CXXFLAGS', '').split():
      yield flag
    yield file_in
    for sofilename in self._dependencies(file_in):
      yield sofilename
    yield '-L%s' % config.installed_path('lib')
    yield '-lcyrt'
    yield '-o'
    yield file_out

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    file_out = _filenames.replacesuffix(file_in, '.so')
    logger.info('Compiling %r', file_out)
    cmd = list(self._compileCommand(file_in, file_out))
    logger.debug('Command: %s', ' '.join(cmd))
    ignored = _system.popen(cmd)
    return file_out

