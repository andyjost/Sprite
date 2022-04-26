from ...toolchain import plans
from ..generic.toolchain import Json2TargetSource

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Py(interp)
  skeleton.append((plans.UNCONDITIONAL, ['.py'], None))

class Json2Py(Json2TargetSource):
  NAME = 'json2py'
  SUFFIX = '.py'

