'''
Code for converting the intermediate representation to executable code.
'''

from ....common import T_FUNC, F_MONADIC
from ....exceptions import CompileError
from .. import cyrtbindings as cyrt
from .... import icurry, objects
from . import save
from ....utility import encoding, filesys
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
  M = moduleobj._cxx
  if M.is_builtin_type(itype.name):
    typeobj = M.get_type(itype.name)
  else:
    flags = lambda ictor: \
        icurry.metadata.getmd(ictor, extern, itype=itype).get('all.flags', 0)
    infos = [
        M.create_infotable(ictor.name, ictor.arity, tag, flags(ictor))
          for tag,ictor in enumerate(itype.constructors)
      ]
    typeobj = M.create_type(itype.name, infos)
  infos = [
      objects.CurryNodeInfo(ictor, info)
          for ictor, info in zip(itype.constructors, typeobj.constructors)
    ]
  typedef = objects.CurryDataType(itype, infos, moduleobj)
  for info in infos:
    info.typedef = typedef
  return typedef

def materialize_function_info_stub(interp, ifun, moduleobj, extern):
  M = moduleobj._cxx
  if M.is_builtin_function(ifun.name):
    info = M.get_infotable(ifun.name)
  else:
    metadata = icurry.metadata.getmd(ifun, extern)
    info = M.create_infotable(
        ifun.name
      , ifun.arity
      , T_FUNC
      , F_MONADIC if metadata.get('all.monadic') else 0
      )
  return objects.CurryNodeInfo(ifun, info)

