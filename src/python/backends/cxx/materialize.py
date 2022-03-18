'''
Code for converting the intermediate representation to executable code.
'''

from ...common import T_FUNC, F_MONADIC
from ...exceptions import CompileError
from . import cyrtbindings as cyrt
from ... import icurry, objects
from ...objects import handle
from ...utility import encoding, filesys
import pprint, six, textwrap

__all__ = [
    'materialize_function'
  , 'materialize_function_info_stub'
  , 'materialize_type'
  ]

def materialize_function(interp, ifun, ir, debug=False):
  '''Materializes a C++ function from the IR.'''
  raise CompileError('JIT compilation is not supported by the %r backend' % 'cxx')

def materialize_type(interp, itype, moduleobj, extern):
  M = handle.getHandle(moduleobj).backend_handle
  typeobj = M.get_builtin_type(itype.name)
  if typeobj is None:
    infos = [
        M.create_infotable(
            ictor.name, ictor.arity, tag
          , ictor.metadata.get('all.flags', 0)
          )
          for tag,ictor in enumerate(itype.constructors)
      ]
    typeobj = M.create_type(itype.name, infos)
  infos = [
      objects.CurryNodeInfo(info, icurry=ictor)
          for ictor, info in zip(itype.constructors, typeobj.constructors)
    ]
  typedef = objects.CurryDataType(itype, infos, moduleobj)
  for info in infos:
    info.typedef = typedef
  return typedef

def materialize_function_info_stub(interp, ifun, moduleobj, extern):
  M = handle.getHandle(moduleobj).backend_handle
  info = M.get_builtin_symbol(ifun.name)
  if info is None or info.tag != T_FUNC:
    info = M.create_infotable(
        ifun.name
      , ifun.arity
      , T_FUNC
      , F_MONADIC if ifun.metadata.get('all.monadic') else 0
      )
  return objects.CurryNodeInfo(info, icurry=ifun)

