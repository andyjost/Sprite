from ..backends import IBackend
from . import _curry2icurry, _filenames, _icurry2json
from ..utility import curryname
import collections, itertools

__all__ = ['makeplan', 'Plan', 'Stage']

Stage = collections.namedtuple('Stage', ['suffixes', 'step'])

# Stage flags.
UNCONDITIONAL      = 0x0
MAKE_ICURRY        = 0x1
MAKE_JSON          = 0x2
MAKE_TARGET_SOURCE = 0x4
MAKE_TARGET_OBJECT = 0x8
ZIP_JSON           = 0x1000
MAKE_ALL           = MAKE_ICURRY | MAKE_JSON | MAKE_TARGET_SOURCE | MAKE_TARGET_OBJECT

def makeplan(interp=None, flags=0):
  '''
  Make a ``Plan`` object, which describes the compilation pipeline.

  If ``interp`` is None, then the plan can only go as far as building ICurry-JSON.

  Args:
    interp:
      An optional interpreter used to assist in building objects.  This defines
      the backend and is needed to perform certain build steps, such as the
      conversion from JSON to target code.
    flags:
      Indicates which build stages are enabled.
  '''
  assert not (flags &~ (MAKE_ALL | ZIP_JSON))
  if interp is None:
    flags &= ~MAKE_TARGET_SOURCE
    flags &= ~MAKE_TARGET_OBJECT
  stages = list(_getstages(interp, flags))
  return Plan(interp, flags, stages)

def _getstages(interp, flags):
  json_suffix = '.json.z' if (flags & ZIP_JSON) else '.json'
  skeleton = [
    #  Flag                Suffixes     Step (if enabled)
    #  ------------------  ------------ -----------------------------
      (MAKE_ICURRY       , ['.curry']   , _curry2icurry.curry2icurry)
    , (MAKE_JSON         , ['.icy']     , _icurry2json.icurry2json)
    , (MAKE_TARGET_SOURCE, [json_suffix], None)
    ]
  if interp is not None:
    interp.backend.extend_plan_skeleton(interp, skeleton)

  for flag, suffixes, step_if_enabled in skeleton:
    step = step_if_enabled if (flags & flag) else None
    yield Stage(suffixes, step)
    if step is None:
      return
  yield Stage([interp.backend.target_object_suffix], None)


class Plan(object):
  '''
  A compilation plan.

  Describes the sequence of stages that comprise compilation.  Each stage
  consists of a set of file suffixes and a step function.  The suffixes
  identify files at that stage.  The step function implements the transition to
  the next stage.
  '''
  def __init__(self, interp, flags, stages):
    self.interp = interp
    self.flags = flags
    self.stages = stages

  def __str__(self):
    def lines():
      yield 'Build plan with %r step%s:' % (len(self), '' if len(self) == 1 else 's')
      fmt = '    %-5s %-24s %s'
      yield fmt % ('Stage', 'Suffixes', 'Step')
      yield fmt % ('-----', '-' * 24, '-' * 40)
      for i,st in enumerate(self.stages):
        yield fmt % (
            i
          , repr(st.suffixes)
          , getattr(st.step, '__name__', st.step)
          )
    return '\n'.join(lines())

  def __len__(self):
    '''Gives the number of steps in the plan.'''
    return len(self.stages) - 1

  def filelist(self, curryfile):
    def gen():
      yield curryfile
      icyfile = _filenames.icurryfilename(curryfile)
      assert icyfile.endswith('.icy')
      for suffix in self.suffixes:
        if suffix == '.curry':
          continue
        yield icyfile[:-4] + suffix
    return list(gen())

  def position(self, filename):
    '''Gives the current position in the plan.'''
    for i,(suffixes,_) in enumerate(self.stages):
      if any(filename.endswith(suffix) for suffix in suffixes):
        return i
    raise ValueError('file %r is not recognized' % filename)

  @property
  def suffixes(self):
    '''Returns the sequence of file suffixes in this plan.'''
    def seq():
      for stage in self.stages:
        for suffix in stage.suffixes:
          yield suffix
    return list(seq())
