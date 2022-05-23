'''Math test programs.'''
import cytest # from ./lib; must be first
import curry

class TestMath(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/math/'
  CLEAN_KWDS = {
      'floatmath|sort03': {'standardize_floats': True}
    }
  # There seems to be some problem with the way symbols are loaded from Data/List.
  # Running with SPRITE_FORCE_RECOMPILE_CXX=1 the tests pass, but without that there are
  # linker errors.
  if curry.flags['backend'] == 'cxx':
    SKIP = 'sort'
