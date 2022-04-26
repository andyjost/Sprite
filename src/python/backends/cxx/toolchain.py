from ..generic.toolchain import Json2TargetSource
from ... import config
from ...toolchain import plans, _filenames, _system
import logging, os

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
  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    file_out = _filenames.replacesuffix(file_in, '.so')
    logger.info('Compiling %r', file_out)
    def compile_command():
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
      yield '-L%s' % config.installed_path('lib')
      yield '-lcyrt'
      for flag in os.environ.get('CXXFLAGS', '').split():
        yield flag
      yield file_in
      yield '-o'
      yield file_out
    cmd = list(compile_command())
    logger.debug('Command: %s', ' '.join(cmd))
    ignored = _system.popen(cmd)
    return file_out
