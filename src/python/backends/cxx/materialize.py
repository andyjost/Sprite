'''
Code for converting the intermediate representation to executable code.

A module loaded from its compiled object carries its info tables and data
types in its metadata (cxx.material; see loader.py), and the materializer
returns them.  A module imported from its ICurry gets info tables and data
types made at run time (Module::create_infotable, Module::create_type).  Under
the interpreter flag ``interpret`` the functions of such a module are
interpreted: the materializer compiles the body of each function into the
bytecode of the runtime (bytecode.py) and attaches it to the info table
(cyrt/icurry.hpp).  Without the flag a function made at run time has no step,
as before: the C++ backend cannot run it.

The body of a function may name a function of its module that the loader has
not reached yet.  The resolver makes the info table of such a function on
demand; the loader finds it and attaches the body when it reaches it.
'''

from ...common import T_FUNC
from ...exceptions import CompileError
from . import bytecode, cyrtbindings as cyrt
from ... import icurry, objects
from ...objects import handle
from ...utility import visitation
import logging

logger = logging.getLogger(__name__)

def materialize(interp, iobj, moduleobj):
  materializer = Materializer(interp, moduleobj)
  return materializer.materialize(iobj)

class Materializer(object):
  def __init__(self, interp, moduleobj):
    self.interp = interp
    h = handle.getHandle(moduleobj)
    self.M = h.backend_handle
    self.imodule = h.icurry
    self.interpret = interp.flags['interpret'] != 'off'

  def materialize(self, iobj):
    info = iobj.metadata.get('cxx.material')
    if info is not None:
      assert isinstance(info, (cyrt.DataType, cyrt.InfoTable))
      return info
    else:
      return self.materializeEx(iobj)

  @visitation.dispatch.on('iobj')
  def materializeEx(self, iobj):
    assert False

  @materializeEx.when(icurry.IType)
  def materializeEx(self, itype):
    typeobj = self.M.get_builtin_type(itype.name)
    if typeobj is None:
      infos = [
          self.M.create_infotable(
              ictor.name, ictor.arity, tag
            , ictor.metadata.get('all.flags', 0)
            )
            for tag,ictor in enumerate(itype.constructors)
        ]
      typeobj = self.M.create_type(
          itype.name, infos, itype.metadata.get('all.flags', 0)
        )
    return typeobj

  @materializeEx.when(icurry.IFunction)
  def materializeEx(self, ifun):
    info = self.M.get_builtin_symbol(ifun.name)
    if info is not None and info.tag == T_FUNC:
      return info
    info = self.M.get_infotable(ifun.name)
    if info is None:
      info = self.create_function(ifun)
    if self.interpret and not cyrt.icurry_is_interpreted(info):
      self.attach(ifun, info)
    return info

  def create_function(self, ifun):
    '''A function table made at run time, without a step.'''
    return self.M.create_infotable(
        ifun.name, ifun.arity, T_FUNC, ifun.metadata.get('all.flags', 0)
      )

  def attach(self, ifun, info):
    '''Compiles the body of ``ifun`` and attaches it to ``info``.'''
    code = bytecode.compile_function(ifun, self)
    logger.debug(
        'Interpreting %s: %d units, %d constants', ifun.fullname
      , len(code.code), len(code.consts)
      )
    cyrt.icurry_attach(
        info, code.code, code.consts, code.nregs, code.nvars, code.nstack
      )

  # The resolver of the emitter (see bytecode.compile_function).
  def symbol(self, fullname):
    '''
    The info table of a function or constructor.  A function of this module
    not yet materialized gets its table now; the loader attaches its body
    when it reaches it.
    '''
    prefix = self.imodule.fullname + '.'
    if fullname.startswith(prefix):
      name = fullname[len(prefix):]
      info = self.M.get_infotable(name)
      if info is not None:
        return info
      ifun = self.imodule.functions.get(name)
      if ifun is not None:
        return self.create_function(ifun)
    try:
      return self.interp.symbol(fullname).info
    except Exception as exc:
      raise CompileError(
          'cannot resolve symbol %r in module %r: %s'
          % (fullname, self.imodule.fullname, exc)
        )

  def tag(self, fullname):
    return self.symbol(fullname).tag

  def datatype(self, fullname):
    typedef = self.symbol(fullname).typedef
    if typedef is None:
      raise CompileError(
          'symbol %r has no data type in module %r'
          % (fullname, self.imodule.fullname)
        )
    return typedef
