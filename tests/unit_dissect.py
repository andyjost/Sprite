import cytest # from ./lib; must be first
from cStringIO import StringIO
from curry.utility.visitation import dispatch
from cytest.dissect import dissect
from cytest.clean import clean as cyclean
import collections
import sys

def capture(a, b):
  '''Capture the printed output of a call to dissect.'''
  buf = StringIO()
  stdout = sys.stdout
  sys.stdout = buf
  try:
    dissect(a, b)
  finally:
    sys.stdout = stdout
  return buf.getvalue()

def clean(x):
  '''Remove all whitespace'''
  return cyclean(x).replace('\n', '')

class Dissect(cytest.TestCase):
  def compareMatch(self, a, b, au):
    out = clean(capture(a, b))
    au = clean(au)
    self.assertEqual(out, au)

  @dispatch.on('substr')
  def compareSearch(self, a, b, substr):
    assert False

  @compareSearch.when(str)
  def compareSearch(self, a, b, substr):
    out = capture(a, b)
    self.assertGreater(out.find(substr), -1)

  @compareSearch.when(collections.Sequence, no=(str,))
  def compareSearch(self, a, b, substrs):
    out = capture(a, b)
    for substr in substrs:
      with trap():
        self.assertGreater(out.find(substr), -1)

  def test_dissectSeq(self):
    a = [1,2,3]
    b = [1,2]
    c = [1,2,4]
    self.assertFalse(dissect(a, a, print_results=False))
    self.assertTrue(dissect(a, b, print_results=False))
    self.assertTrue(dissect(a, c, print_results=False))
    self.assertTrue(dissect(b, c, print_results=False))
    self.compareMatch(a, b, '''
                       At <object>, sequence length mismatch
                               a = [1, 2, 3] (<type 'list'>)
                               b = [1, 2] (<type 'list'>)
                       '''
      )
    self.compareMatch(a, c, '''
                       At <object>[2], value mismatch
                               a = 3 (<type 'int'>)
                               b = 4 (<type 'int'>)
                       '''
      )

  def test_dissectMap(self):
    a = {'a':1, 'b':2}
    b = {'a':1}
    c = {'x':1, 'b':2}
    d = {'a':1, 'b':20}
    e = {'x':1, 'b':20}
    self.assertFalse(dissect(a, a, print_results=False))
    self.assertTrue(dissect(a, b, print_results=False))
    self.assertTrue(dissect(a, c, print_results=False))
    self.assertTrue(dissect(a, d, print_results=False))
    self.assertTrue(dissect(a, e, print_results=False))
    self.compareSearch(a, b, "At <object>, only in a: 'b'")
    self.compareSearch(a, c, [ "At <object>, only in a: 'a'"
                             , "At <object>, only in b: 'x'"])
    self.compareMatch(a, d, '''
                            At <object>['b'], value mismatch
                                    a = 2 (<type 'int'>)
                                    b = 20 (<type 'int'>)
                            '''
      )
    self.compareSearch(a, e, [ "At <object>, only in a: 'a'"
                             , "At <object>, only in b: 'x'"
                             , "At <object>['b'], value mismatch"])

  def test_dissectObject(self):
    class Object(object): pass
    a = Object(); a.a = 1; a.b = 2
    b = Object(); b.a = 1
    c = Object(); c.a = 1; c.b = 20
    self.assertFalse(dissect(a, a, print_results=False))
    self.assertTrue(dissect(a, b, print_results=False))
    self.assertTrue(dissect(a, c, print_results=False))
    self.compareSearch(a, b, "At <object>, only in a: 'b'")
    self.compareMatch(a, c, '''
                            At <object>.b, value mismatch
                                    a = 2 (<type 'int'>)
                                    b = 20 (<type 'int'>)
                            '''
      )

  def test_dissectNested(self):
    class Object(object): pass
    o = Object(); o.a = 1; o.b = 2
    p = Object(); p.a = 1; p.b = 20
    a = {'a':[1,2,3], 'b':{'x':o}, 'c':o}
    b = {'a':{}, 'b':{'x':o}, 'c':o}
    c = {'a':[1,2,4], 'b':{'x':p}}
    self.compareSearch(a, b, [ "At <object>['a'], type mismatch"])
    self.compareSearch(a, c, [ "At <object>, only in a: 'c'"
                             , "At <object>['b']['x'].b, value mismatch"])
    self.compareSearch(b, c, [ "At <object>, only in a: 'c'"
                             , "At <object>['a'], type mismatch"])

