from ..backends import IBackend
from . import _curry2icurry, _filenames, _icurry2json
from ..utility import curryname
import collections, itertools, os

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

  def prune_stale(self, filelist, currypath=None):
    '''
    Removes from ``filelist``, the files of one module in the order of this
    plan, every file that a step refuses, and every file after it.  A file
    that does not exist is kept, because nothing can be read from it.  See
    ``is_stale``; ``currypath`` is the search path of the imports of the
    module (``_findcurry.imports_path``).
    '''
    for i, filename in enumerate(filelist):
      if os.path.isfile(filename) and self.is_stale(filename, currypath):
        return filelist[:i]
    return filelist

  def is_stale(self, filename, currypath=None):
    '''
    Tells whether a step of this plan refuses ``filename``.  A step refuses a
    file through its ``is_stale`` method, when it has one; see ``Json2Cpp``
    and ``Cpp2So`` of the C++ backend and ``curry2icurry`` of the toolchain.
    The step of the file's stage, which reads the file, is asked, and so is
    the step before it, which made the file.  A step that answers for both
    its input and its output tells them apart by the suffix.  ``currypath``
    is the search path of the imports of the module
    (``_findcurry.imports_path``), for a step that imports them to answer
    (``Cpp2So``).
    '''
    position = self.position(filename)
    steps = [self.stages[position].step]
    if position:
      steps.append(self.stages[position - 1].step)
    for step in steps:
      is_stale = getattr(step, 'is_stale', None)
      if is_stale is not None and is_stale(filename, currypath):
        return True
    return False

  def restore(self, filename, currypath, **kwds):
    '''
    Asks the step that makes the final product of this plan to place a
    cached copy of the products of the module of ``filename`` beside its
    files (the product cache; see ``Cpp2So.restore`` of the C++ backend).
    Returns the file placed, or None when the step has no ``restore``
    method, the cache is off, or the cache holds no entry.  ``Maker.make``
    asks before each step, so a module whose products are cached is neither
    generated nor compiled.  ``kwds`` are the keywords of the plan
    (``is_sourcefile`` among them).
    '''
    if len(self.stages) < 2:
      return None
    restore = getattr(self.stages[-2].step, 'restore', None)
    if restore is None:
      return None
    return restore(filename, currypath, **kwds)

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
