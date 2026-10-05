from ...common import T_CTOR, T_FUNC
from ..generic.compiler import DEFINED, STEP_FUNCTION
from .graph.infotable import DataType, InfoTable
from . import compiler
from ... import icurry, objects
from io import StringIO
from ...utility import encoding, filesys, visitation
import inspect, textwrap

def materialize(interp, iobj, moduleobj):
  materializer = Materializer(interp)
  return materializer.materialize(iobj)

class Materializer(object):
  def __init__(self, interp):
    self.interp = interp

  def materialize(self, iobj):
    info = iobj.metadata.get('py.material')
    if info is not None:
      assert isinstance(info, (DataType, InfoTable))
      return info
    else:
      return self.materializeEx(iobj)

  @visitation.dispatch.on('iobj')
  def materializeEx(self, iobj):
    assert False

  @materializeEx.when(icurry.IType)
  def materializeEx(self, itype):
    datatype = DataType(
        itype.name
      , [self.materialize(ictor) for ictor in itype.constructors]
      )
    for ctorinfo in datatype.constructors:
      ctorinfo.typedef = datatype
    return datatype

  @materializeEx.when(icurry.IConstructor)
  def materializeEx(self, ictor):
    builtin = 'all.tag' in ictor.metadata
    return InfoTable(
        ictor.name
      , ictor.arity
      , T_CTOR + ictor.index if not builtin else ictor.metadata['all.tag']
      , getattr(ictor.metadata, 'all.flags', 0)
      , None
      , getattr(ictor.metadata, 'py.format', None)
      )

  @materializeEx.when(icurry.IFunction)
  def materializeEx(self, ifun):
    # If lazycompile is set, delay compilation until the function is actually
    # used.  The step function resolves the symbols it refers to by name, so
    # a function compiled while its module loads must not refer to a function
    # of the module loaded after it: a lambda lifted from the text of an
    # expression, or a method derived for a data type of the module.  An
    # expression module, which leaves the registry of the interpreter after
    # its compilation, is compiled right after its load (compile_pending).
    trampoline = Trampoline(
        lambda: materializeStepfunc(self.interp, ifun)
      )
    lazy = self.interp.flags['lazycompile']
    info = InfoTable(
        ifun.name
      , ifun.arity
      , T_FUNC
      , ifun.metadata.get('all.flags', 0)
      , trampoline if lazy else trampoline.materialize()
      , getattr(ifun.metadata, 'py.format', None)
      )
    if lazy:
      trampoline.slot = info, 'step'
    return info

def compile_pending(moduleobj):
  '''
  Compiles every step function of ``moduleobj`` that was left to its first
  call.  Every symbol of the module is registered, so a function may refer to
  any function of the module.
  '''
  for symbol in getattr(moduleobj, '.symbols').values():
    step = symbol.info.step
    if isinstance(step, Trampoline):
      step.materialize()

def materializeStepfunc(interp, ifun):
  '''JIT-compiles a Python step function.'''
  target_object = compiler.compile(interp, ifun)
  stream = StringIO()
  compiler.write_module(target_object, stream, module_main=False, section_headers=False)
  source = stream.getvalue()
  closure = {'interp': interp}
  if interp.flags['debug']:
    # If debugging, write a source file so that PDB can step into this
    # function.
    assert ifun is not None
    srcdir = filesys.getDebugSourceDir()
    name = encoding.symbolToFilename(ifun.fullname) + '.py'
    srcfile = filesys.makeNewfile(srcdir, name)
    with open(srcfile, 'w') as out:
      out.write(source)
      out.write('\n')
      comment = (
          'This file was created by Sprite because %r was compiled in debug '
          'mode.  It exists to help PDB show the compiled code.'
        ) % ifun.fullname
      out.write('\n'.join('# ' + line for line in textwrap.wrap(comment)))
      out.write('\n\n# ICurry:\n# -------\n')
      out.write('\n'.join('# ' + line for line in str(ifun).split('\n')))
    co = compile(source, srcfile, 'exec')
    exec(co, closure)
  else:
    exec(source, closure)
  for symbolname, symbol in target_object.symtab.items():
    if symbol.kind == STEP_FUNCTION and symbol.stat == DEFINED:
      stepfunc = closure[symbolname]
      stepfunc.source = source
      return stepfunc
  assert False

def getimpl(symbol):
  '''
  The source of the step function of ``symbol``: the text of a step compiled
  in this process, or the source of the function in the generated module or
  in the library of built-ins.  A step left to its first call is compiled
  now.  Raises ValueError when there is no step or no source.
  '''
  step = symbol.info.step
  if isinstance(step, Trampoline):
    step = step.materialize()
  if step is not None:
    source = getattr(step, 'source', None)
    if source is not None:
      return source
    try:
      return inspect.getsource(step)
    except (OSError, TypeError):
      pass
  raise ValueError(
      'no implementation code available for %r' % symbol.fullname
    )

class Trampoline(object):
  def __init__(self, callback, slot=None):
    self.callback = callback
    self.slot = None

  def materialize(self):
    value = self.callback()
    if self.slot:
      obj, attr = self.slot
      setattr(obj, attr, value)
    return value

  def __call__(self, *args, **kwds):
    f = self.materialize()
    return f(*args, **kwds)

