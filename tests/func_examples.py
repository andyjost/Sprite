import cytest # from ./lib; must be first

class TestExamples(cytest.FunctionalTestCase):
  '''Tests the examples developed for my dissertation.'''
  SOURCE_DIR = 'data/curry/examples/'
  SKIP = 'ex8|ex10'
  # RUNONLY = 'ex3b'