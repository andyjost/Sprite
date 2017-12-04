from _llvm import *
from .types import *

def isa(obj, llvmty):
  return obj.isa(llvmty)

