import collections, itertools
from . import _curry2icurry, _icurry2json, _json2tgt
from ..backends import IBackend

Stage = collections.namedtuple('Stage', ['suffixes', 'step'])

class Plan(object):
  '''
  Represents a compilation plan.

  Describes the sequence of steps that must be performed and the functions that
  implement them.
  '''
  def __init__(self, kwds={}):
    self.backend_name = kwds.pop('backend_name', None)
    self.suffix = '' if self.backend_name is None else \
        IBackend(self.backend_name).target_suffix
    self.do_tgt = bool(self.backend_name)
    self.do_json = kwds.pop('json', True) or self.do_tgt
    self.do_icy = kwds.pop('icy', True) or self.do_json
    self.enabled = [self.do_icy, self.do_json, self.do_tgt]
    do_zip = kwds.get('zip', True)
    self.stages = list(self._getstages(do_zip))
    assert len(self.enabled) == len(self.stages) - 1
    self.n_steps = sum(1 for _ in itertools.takewhile(lambda a:a, self.enabled))

  def _getstages(self, zip_json):
    yield Stage(['.curry']   , _curry2icurry.curry2icurry)
    yield Stage(['.icy']     , _icurry2json.icurry2json)

    json2tgt_func = lambda *args, **kwds: \
      _json2tgt.json2tgt(self.backend_name, *args, **kwds)

    if zip_json:
      yield Stage(['.json.z'], json2tgt_func)
    else:
      yield Stage(['.json']  , json2tgt_func)

    yield Stage([self.suffix], None)

  @property
  def suffixes(self):
    '''Returns the sequence of file suffixes in this plan.'''
    def seq():
      for en, stage in zip([True] + self.enabled, self.stages):
        if en:
          for suffix in stage.suffixes:
            yield suffix
        else:
          break
    return list(seq())

  def __len__(self):
    '''Gives the number of steps in the plan.'''
    return self.n_steps

  def position(self, filename):
    '''Gives the current position in the plan.'''
    for i,(suffixes,_) in enumerate(self.stages):
      if any(filename.endswith(suffix) for suffix in suffixes):
        return i
    assert False

