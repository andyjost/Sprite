import collections, itertools
from . import _curry2icurry, _icurry2json, _json2py

Stage = collections.namedtuple('Stage', ['suffixes', 'step'])

class Plan(object):
  '''
  Represents a compilation plan.

  Describes the sequence of steps that must be performed and the functions that
  implement them.
  '''
  def __init__(self, kwds={}):
    self.do_py = kwds.pop('py', False)
    self.do_json = kwds.pop('json', True) or self.do_py
    self.do_icy = kwds.pop('icy', True) or self.do_json
    self.enabled = [self.do_icy, self.do_json, self.do_py]
    do_zip = kwds.get('zip', True)
    self.stages = list(self.get_stages(do_zip))
    assert len(self.enabled) == len(self.stages) - 1
    self.n_steps = sum(1 for _ in itertools.takewhile(lambda a:a, self.enabled))

  @staticmethod
  def get_stages(zip_json):
    yield Stage(['.curry']   , _curry2icurry.curry2icurry)
    yield Stage(['.icy']     , _icurry2json.icurry2json)
    if zip_json:
      yield Stage(['.json.z'], _json2py.json2py)
    else:
      yield Stage(['.json']  , _json2py.json2py)
    yield Stage(['.py']      , None)

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

