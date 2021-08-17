import cytest # from ./lib; must be first

class TestSetFunctions(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/setf/'
  SKIP = '.*'
  # RUN_ONLY = ''
