import cytest # from ./lib; must be first

class TestExamples(cytest.FunctionalTestCase):
  '''Tests the examples developed for my dissertation.'''
  SOURCE_DIR = 'data/curry/examples/'
  # RUN_ONLY = 'ex[8][a-z]?$'
