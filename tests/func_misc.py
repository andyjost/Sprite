import cytest # from ./lib; must be first
import curry
from cytest.tty import CLOSE

class TestExamples(cytest.FunctionalTestCase):
  SOURCE_DIR = 'data/curry/misc/'
  INTENDED_FAILURES = {
      'appendFile_error': 'i/o error: Is a directory: /'
    , 'error'           : 'A boom boom happened'
    , 'getChar_error'   : 'i/o error: EOF'
    , 'putChar_error'   : 'i/o error: EOF'
    , 'writeFile_error' : 'i/o error: Is a directory: /'
    }
  TTY = {             #  stdin   stdout
      'putChar$'      : (None  , 'a'   )
    , 'putChar_error' : (None  , CLOSE )
    , 'putChar_catch' : (None  , CLOSE )
    , 'getChar$'      : ('abcd', None  )
    , 'getChar_error$': (''    , None  )
    , 'getChar_catch$': (''    , None  )
    , 'getChar_error2': (CLOSE , None  )
    , 'getChar_catch2': (CLOSE , None  )
    , 'getputChar'    : ('ZYX' , 'Z'   )
    , 'catch'         : (None  , 'Caught an error\n')
    }
  CREATES_FILE = {
      'appendFile$'   : {'data/curry/misc/appendFile.out': 'Hello, World!'}
    , 'putChar_catch' : {'data/curry/misc/putChar_catch.out': 'yes'}
    , 'writeFile$'    : {'data/curry/misc/output.txt': 'the content'}
    }
  if curry.flags['backend'] == 'py':
    SKIP = 'catch'
