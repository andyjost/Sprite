from .compiler import FunctionCompiler
from .... import icurry
from . import misc, statics, synthesis
from .ir import IR
from ....utility import formatDocstring, visitation
import collections, logging, six

logger = logging.getLogger(__name__)
__all__ = ['compile', 'compileEx']

@formatDocstring(__package__[:__package__.find('.')])
def compile(interp, icy, extern=None):
  '''
  Compiles ICurry into IR.

  Parameters:
  -----------
  ``interp``
      The interpreter that owns this function.
  ``icy``
      ICurry for the function to compile.
  ``extern``
      An instance of ``{0}.icurry.IModule`` used to resolve external
      declarations.

  Returns:
  --------
  Python IR for the given function.
  '''
  closure = statics.Closure()
  lines = []
  iobj = compileEx(interp, icy, closure, lines, extern)
  return IR(iobj, closure, lines)

@visitation.dispatch.on('icy')
def compileEx(interp, icy, closure, lines, extern=None):
  '''
  Compiles an ICurry object.

  The output consists of updates to ``closure`` and ``lines`` as well as a new
  ICurry object identical to ``icy`` except that every function body is
  specified as IMaterial.

  Paramters:
  ----------
    ``icy``
      An IPackage, IModule, or IFunction to compile.

    ``closure``
      The closre in which this code resides.  This will be updated if the
      generated code requires external data or symbols.

    ``lines``
      The output lines of Python source.  New code will be appended.

    ``extern``
      An IPackage or IModule containing external definitions.  Use to resolve
      IExternal data.

  Returns:
  --------
  A new ICurry object.
  '''
  raise TypeError('Cannot compile type %r' % type(icy).__name__)

@compileEx.when(icurry.IModule)
def compileEx(interp, imodule, closure, lines, extern=None):
  functions = [
      compileEx(interp, ifun, closure, lines, extern)
          for ifun in six.itervalues(imodule.functions)
    ]
  return imodule.copy(functions=functions)

def withNewEntry(f):
  def decorator(interp, ifun, closure, lines, extern=None):
    entry = closure.intern(ifun.fullname)
    try:
      return f(interp, ifun, closure, lines, extern, entry)
    except:
      closure.delete(entry)
      raise
  return decorator

@compileEx.when(icurry.IFunction)
@withNewEntry
def compileEx(interp, ifun, closure, lines, extern=None, entry=None):
  while True:
    # First, try to synthesize the function.
    new_lines = synthesis.synthesize_function(interp, ifun, closure, entry)
    if new_lines is not None:
      break

    # If that cannot be done, compile it.
    compiler = FunctionCompiler(interp, ifun, closure, entry, extern)
    try:
      compiler.compile()
    except misc.ExternallyDefined as e:
      # The compile routine resolved an external definition.  Start over.
      ifun = e.ifun
    else:
      # Compilation succeeded.  Log the info and return it.
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
      new_lines = compiler.lines
      break

  # Update the lines and return the new IFunction.
  new_ifun = ifun.copy(body=icurry.ILink(entry))
  if lines:
    lines.append('')
  lines.extend(new_lines)
  return new_ifun

