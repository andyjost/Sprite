import cytest # from ./lib; must be first

class TestExamples(cytest.FunctionalTestCase):
  '''Tests the examples developed for my dissertation.'''
  SOURCE_DIR = 'data/curry/examples/'
  # SKIP = 'ex[1-5]|ex6b'
  # RUNONLY = 'ex6a'
