import cytest # from ./lib; must be first
import curry

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/misc/'
  INTENDED_FAILURES = {
      'error': 'A boom boom happened'
    , 'writeFile_error': 'i/o error: Is a directory: /'
    }
  TTY = {
                  #  stdin   stdout
      'putChar'   : (None  , 'a'   )
    , 'getChar'   : ('abcd', None  )
    , 'getputChar': ('ZYX' , 'Z'   )
    , 'catch'     : (None  , 'Caught an error\n')
    }
  CREATES_FILE = {
      'writeFile$' : {'data/curry/misc/output.txt': 'the content'}
    }
  if curry.flags['backend'] == 'py':
    SKIP = 'catch'
