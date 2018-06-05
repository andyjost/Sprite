'''
Compares stuctured data recursively and reports on differences.
'''
from curry.visitation import dispatch
import collections
import functools

class Difference(Exception):
  '''Indicates a found difference.'''

def dissectmethod(wrapped):
  '''
  Decorator that implements standard processing for one level of a dissection.

  If an index is provided, the ``self.path`` variable is updated while in the
  inner frames.

  If a ``Difference`` is raised (to abort the inner frame) it is captured and
  dissection continues, if configured to do so.
  '''

  def handleDiff(self, a, b, **kwds):
    try:
      if type(a) != type(b):
        raise Difference('type mismatch')
      return wrapped(self, a, b, **kwds)
    except Difference as diff:
      self.report(diff, a, b)
      # msg = 'At <object>%s, %s' % (''.join(self.path), str(diff))
      # self.diffs.append((msg, a, b))
      # if len(self.diffs) < self.limit:
      #   pass
      # else:
      #   raise StopIteration()

  @functools.wraps(wrapped)
  def processFrame(self, a, b, **kwds):
    index = kwds.pop('index', None)
    if index:
      self.path.append(index)
      try:
        handleDiff(self, a, b, **kwds)
      finally:
        self.path.pop()
    else:
      handleDiff(self, a, b, **kwds)

  return processFrame

class Dissector(object):
  '''
  Compares stuctured data recursively and reports on differences.
  '''
  def __init__(self, limit=0):
    self.limit = limit if limit > 0 else float('inf')
    self.path = []
    self.diffs = []

  def report(self, diff, a, b):
    msg = 'At <object>%s, %s' % (''.join(self.path), str(diff))
    self.diffs.append((msg, a, b))
    if len(self.diffs) >= self.limit:
      raise StopIteration()

  def check(self, a, b, what):
    if a != b:
      raise Difference('%s mismatch' % (what,))

  @dissectmethod
  @dispatch.on('a')
  def __call__(self, a, b, **kwds):
    if hasattr(a, '__dict__'):
      self(a.__dict__, b.__dict__, format='.{}'.format)
    else:
      self.check(a, b, 'value')

  @dissectmethod
  @__call__.when(collections.Sequence, no=(str,))
  def __call__(self, a, b, **kwds):
    self.check(len(a), len(b), 'sequence length')
    for i,(a_,b_) in enumerate(zip(a,b)):
      self(a_, b_, index='[%s]' % i)

  @dissectmethod
  @__call__.when(collections.Mapping)
  def __call__(self, a, b, **kwds):
    ka = set(a.keys())
    kb = set(b.keys())
    ka_b = ka - kb
    for k in ka-kb:
      self.report('only in a: {!r}'.format(k), a, b)
    for k in kb-ka:
      self.report('only in b: {!r}'.format(k), a, b)
    #self.check(len(ka), len(kb), 'key #')
    #self.check(ka, kb, 'key')
    format_ = kwds.pop('format', '[{!r}]'.format)
    for k in ka.intersection(kb):
      self(a[k], b[k], index=format_(k))

def dissect(a, b, limit=0, print_results=True):
  '''
  Dissects and compares the internals of two objects.  If they are not equal,
  reports details about where they differ.  This can be used to find
  differences between complex, nested objects such as instances of
  ``icurry.IModule``.
  '''
  dissector = Dissector(limit)
  try:
    dissector(a, b)
  except StopIteration:
    pass
  if print_results:
    for msg, a, b in dissector.diffs:
      print msg
      print '        a =', a, '(%s)' % type(a)
      print '        b =', b, '(%s)' % type(b)
  else:
    return dissector.diffs

