import cytest # from ./lib; must be first
import curry

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/misc/'
  INTENDED_FAILURES = {'error': 'A boom boom happened'}
  TTY = {
                  #  stdin   stdout
      'putChar'   : (None  , 'a'   )
    , 'getChar'   : ('abcd', None  )
    , 'getputChar': ('ZYX' , 'Z'   )
    , 'catch'     : (None  , 'Caught an error\n')
    }
  if curry.flags['backend'] == 'py':
    SKIP = 'catch'
