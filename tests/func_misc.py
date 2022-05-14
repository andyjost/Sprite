import cytest # from ./lib; must be first

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/misc/'
  INTENDED_FAILURES = {'error': 'A boom boom happened'}
  TTY = {
      'putChar': (None, 'a')
    , 'getChar': ('abcd', None)
    , 'getputChar': ('ZYX', 'Z')
    }
