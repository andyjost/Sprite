'''
Code for converting the intermediate representation to executable code.
'''

from ...common import T_FUNC
from ...exceptions import CompileError
from . import cyrtbindings as cyrt
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
    self.M = handle.getHandle(moduleobj).backend_handle

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
    if info is None or info.tag != T_FUNC:
      # Cannot dynamically build functions in C++.
      assert False
      info = self.M.create_infotable(
          ifun.name
        , ifun.arity
        , T_FUNC
        , ifun.metadata.get('all.flags', 0)
        )
    return info

