from .compiler import FunctionCompiler
from . import misc, synthesis
from ....utility import formatDocstring
import logging

logger = logging.getLogger(__name__)

__all__ = ['compile']

@formatDocstring(__package__[:__package__.find('.')])
def compile(interp, ifun, extern=None):
  '''
  Compiles an ICurry function into an instance of IR.

  Parameters:
  -----------
  ``interp``
      The interpreter that owns this function.
  ``ifunc``
      ICurry for the function to compile.
  ``extern``
      An instance of ``{0}.icurry.IModule`` used to resolve external
      declarations.

  Returns:
  --------
  A Python function object.
  '''
  while True:
    try:
      ir = synthesis.synthesize_function(interp, ifun)
      if ir is not None:
        return ir
      compiler = FunctionCompiler(interp, ifun, extern)
      compiler.compile()
    except misc.ExternallyDefined as e:
      ifun = e.ifun
    else:
      break

  if logger.isEnabledFor(logging.DEBUG):
    title = 'Compiling %r:' % ifun.fullname
    logger.debug('')
    logger.debug(title)
    logger.debug('=' * len(title))
    logger.debug('    ICurry:')
    logger.debug('    -------')
    [logger.debug('    ' + line if line else '')
        for line in str(ifun).split('\n')
      ]
    logger.debug('')
    [logger.debug('    ' + line if line else '')
        for line in str(compiler).split('\n')
      ]
  return compiler.ir()

