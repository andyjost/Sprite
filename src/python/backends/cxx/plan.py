from ...toolchain import plans

def extend_plan_skeleton(interp, skeleton):
  assert interp is not None
  flag, suffixes, _ = skeleton[-1]
  skeleton[-1] = flag, suffixes, Json2Cpp(interp)
  skeleton.append((plans.MAKE_TARGET_OBJECT, ['.cpp'], Cpp2So(interp)))
  skeleton.append((plans.UNCONDITIONAL, ['.so'] , None))

class Json2Cpp(object):
  def __init__(self, interp):
    self.interp = interp
  def __repr__(self):
    return 'json2cpp'
  def __call__(self, *args, **kwds):
    # TODO
    pass

class Cpp2So(object):
  def __init__(self, interp):
    self.interp = interp
  def __repr__(self):
    return 'cpp2so'
  def __call__(self, *args, **kwds):
    # TODO
    pass
