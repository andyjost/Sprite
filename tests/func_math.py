'''Math test programs.'''
import cytest # from ./lib; must be first
import curry

class TestMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  # RUN_ONLY = []
  if curry.flags['backend'] == 'cxx':
    SKIP = ['floatmath|intmath05[89]|intmath0[67][0-9]']
