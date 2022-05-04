import cytest # from ./lib; must be first

class TestExamples(cytest.FunctionalTestCase):
  '''Tests the examples developed for my dissertation.'''
  SOURCE_DIR = 'data/curry/examples/'
  SKIP = 'ex10'
  # RUN_ONLY = 'ex[8][a-z]?$'
  RUN_ONLY = 'ex5'
