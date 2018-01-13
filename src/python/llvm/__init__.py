from _llvm import *
from .types import *

# Modules imported for their side-effects.
from . import _symboltable
from . import _value

def isa(obj, llvmty):
  return obj.isa(llvmty)

