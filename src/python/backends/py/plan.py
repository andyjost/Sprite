from ...toolchain import plans, _filenames, _loadcurry, _system
import logging

logger = logging.getLogger(__name__)

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Py(interp)
  skeleton.append((plans.UNCONDITIONAL, ['.py'], None))

class Json2Py(object):
  def __init__(self, interp):
    self.interp = interp

  def __repr__(self):
    return 'json2py'

  @_system.updateCheck
  def __call__(self, file_in, currypath, **ignored):
    icurry = _loadcurry.loadjson(file_in)
    module = self.interp.import_(icurry)
    file_out = _filenames.replacesuffix(file_in, '.py')
    _system.makeOutputDir(file_out)
    self.interp.save(module, file_out, module_main=False)
    return file_out

