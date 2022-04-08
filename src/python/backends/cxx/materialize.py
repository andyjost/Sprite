'''
Code for converting the intermediate representation to executable code.
'''

from ...common import T_FUNC
from ...exceptions import CompileError
# from . import cyrtbindings as cyrt
from ... import icurry, objects
from ...objects import handle
# from ...utility import encoding, filesys
# import pprint, six, textwrap
from ...utility import visitation

def materialize(interp, iobj, moduleobj):
  materializer = Materializer(interp, moduleobj)
  return materializer.materialize(iobj)

class Materializer(object):
  def __init__(self, interp, moduleobj):
    self.interp = interp
    self.M = handle.getHandle(moduleobj).backend_handle

  def materialize(self, iobj):
    info = iobj.metadata.get('cxx.material')
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
    typeobj = self.M.get_builtin_type(itype.name)
    if typeobj is None:
      infos = [
          self.M.create_infotable(
              ictor.name, ictor.arity, tag
            , ictor.metadata.get('all.flags', 0)
            )
            for tag,ictor in enumerate(itype.constructors)
        ]
      typeobj = self.M.create_type(itype.name, infos)
    return typeobj

  @materializeEx.when(icurry.IFunction)
  def materializeEx(self, ifun):
    info = self.M.get_builtin_symbol(ifun.name)
    if info is None or info.tag != T_FUNC:
      info = self.M.create_infotable(
          ifun.name
        , ifun.arity
        , T_FUNC
        , ifun.metadata.get('all.flags', 0)
        )
    return info


# def materialize_function(interp, ifun, ir, debug=False):
#   '''Materializes a C++ function from the IR.'''
#   raise CompileError('JIT compilation is not supported by the %r backend' % 'cxx')
# 
# def materialize_type(interp, itype, moduleobj, extern):
#   M = handle.getHandle(moduleobj).backend_handle
#   typeobj = M.get_builtin_type(itype.name)
#   if typeobj is None:
#     infos = [
#         M.create_infotable(
#             ictor.name, ictor.arity, tag
#           , ictor.metadata.get('all.flags', 0)
#           )
#           for tag,ictor in enumerate(itype.constructors)
#       ]
#     typeobj = M.create_type(itype.name, infos)
#   infos = [
#       objects.CurryNodeInfo(info, icurry=ictor)
#           for ictor, info in zip(itype.constructors, typeobj.constructors)
#     ]
#   typedef = objects.CurryDataType(itype, infos, moduleobj)
#   for info in infos:
#     info.typedef = typedef
#   return typedef
# 
# def materialize_function_info_stub(interp, ifun, moduleobj, extern):
#   M = handle.getHandle(moduleobj).backend_handle
#   info = M.get_builtin_symbol(ifun.name)
#   if info is None or info.tag != T_FUNC:
#     info = M.create_infotable(
#         ifun.name
#       , ifun.arity
#       , T_FUNC
#       , ifun.metadata.get('all.flags', 0)
#       )
#   return objects.CurryNodeInfo(info, icurry=ifun)

