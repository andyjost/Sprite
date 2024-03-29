from ...common import T_CTOR, T_FUNC
from ..generic.compiler import DEFINED, STEP_FUNCTION
from .graph.infotable import DataType, InfoTable
from . import compiler
from ... import config, icurry, objects
from six.moves import StringIO
from ...utility import encoding, filesys, visitation
import six, textwrap

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
    # Compile interactive code right away.  Otherwise, if lazycompile is set,
    # delay compilation until the function is actually used.  See InfoTable in
    # interpreter/runtime.py.
    trampoline = Trampoline(
        lambda: materializeStepfunc(self.interp, ifun)
      )
    lazy = self.interp.flags['lazycompile'] and \
        ifun.modulename != config.interactive_modname()
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
    six.exec_(co, closure)
  else:
    six.exec_(source, closure)
  for symbolname, symbol in target_object.symtab.items():
    if symbol.kind == STEP_FUNCTION and symbol.stat == DEFINED:
      stepfunc = closure[symbolname]
      stepfunc.source = source
      return stepfunc
  assert False

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

