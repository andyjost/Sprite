'''Python bindings for libsprite.so.'''
from . import __sprite
from . import fingerprint

from .__sprite import (
    ChoiceState
  , Fingerprint
  , InfoTable
  , InterpreterState
  , LEFT
  , Node
  , RIGHT
  , Type
  , UNDETERMINED
  )

# class InfoTable(_c.InfoTable):
#   def create(moduleobj, name, arity, tag, step, format, typecheck, flags):
#     M = _c.get_module_handle(moduleobj)
#     return _c.create_info(M, name, arity, tag, flags)
#
#   @property
#   def typedef(self):
#     return self._typedef
#
#   @typedef.setter
#   def typedef(self, value):
#     breakpoint()


# def InfoTable_create(
#     moduleobj, name, arity, tag, step, format, typecheck, flags
#   ):
#   M = __sprite.get_module_handle(moduleobj)
#   return __sprite.create_info(M, name, arity, tag, flags)

# InfoTable.create = InfoTable_create
